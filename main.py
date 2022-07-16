import fastf1 as ff
from fastf1 import plotting 
import pandas as pd
from matplotlib import pyplot
from matplotlib.pyplot import figure
from matplotlib import cm
import numpy as np
import sys 
import os 
from datetime import datetime as dt
import argparse


def get_latest_race_name(schedule):
    """
    Given a schedule, return the name of the latest race that has already happened.
    :param schedule: the schedule dataframe
    :return: The latest race name.
    """
    today_date = dt.now()
    latest = None
    for _, event in schedule.iterrows():
        if event['EventDate'] < today_date:
            latest = event
        else:
            return latest['EventName']


# enabling the ff1 cache
done = False
while not done:
    try:
        ff.Cache.enable_cache('.cache/')
        done = True
    except NotADirectoryError:
        os.mkdir

# avoid pandas error
pd.options.mode.chained_assignment = None

# argparse settings 
description = """
f1-laptimes is a tool for visualizing lap-by-lap pace and average pace over a Formula 1 session.
"""

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=description)
parser.add_argument("-y", "--year", metavar="YEAR", type=int, help="The year of the session to analyze.")
parser.add_argument("-t", "--track", metavar="TRACK", type=str, default=get_latest_race_name(ff.get_event_schedule(2022)), help="The track of the session to analyze. If not specified, the latest F1 weekend's track will be used.")
parser.add_argument("-df", "--drivers-file", metavar="DRIVERS_FILE", type=str, help="Path to a file containing a comma separated list of drivers to display.")

args = vars(parser.parse_args())

print(args['year'])
# retrieving the session specificities from cli args : year and track
# YEAR = 2022
# if '-y' in sys.argv or '--year' in sys.argv :
#     arg = '-y' if '-y' in sys.argv else '--year'
#     YEAR = int(sys.argv[sys.argv.index(arg) + 1])

# GP = None
# if '-t' in sys.argv or '--track' in sys.argv:
#     arg_track = '-t' if '-t' in sys.argv else '--track'
#     GP = sys.argv[sys.argv.index(arg_track) + 1]
# else:
#     GP = get_latest_race_name(ff.get_event_schedule(YEAR))

# load session data / convert laptimes to seconds  
race = ff.get_session(YEAR, GP, 'Q')
laps = race.load_laps()
laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds() 

# exclude pit stop laps 
laps = laps.loc[(laps['PitOutTime'].isnull() & laps['PitInTime'].isnull())]

# using IQR to remove outliers 
# quantiles
q75, q25 = laps['LapTimeSeconds'].quantile(0.75), laps['LapTimeSeconds'].quantile(0.25)
inter = q75 - q25
laptime_max = q75 + (1.5 * inter) 
laptime_min = q25 - (1.5 * inter)

laps.loc[laps['LapTimeSeconds'] < laptime_min, 'LapTimeSeconds'] = np.nan
laps.loc[laps['LapTimeSeconds'] > laptime_max, 'LapTimeSeconds'] = np.nan

# drivers to display
DRIVERS = []
if '-df' in sys.argv or '--drivers-file' in sys.argv:
    arg = '-df' if '-df' in sys.argv else '--drivers-file'
    filename = sys.argv[sys.argv.index(arg) + 1]
    with open(filename, mode='r') as drivers_file:
        for line in drivers_file.readlines():
            DRIVERS.append(line.strip().upper())
elif '-d' in sys.argv or '--drivers' in sys.argv:
    arg = '-d' if '-d' in sys.argv else '--drivers'
    DRIVERS = [txt.upper() for txt in sys.argv[sys.argv.index(arg) + 1].split(",")]
else:
    DRIVERS = [driver['Abbreviation'] for _, driver in race.results.iterrows()]

# plotting 
drivers = [driver for driver in DRIVERS]
teams = []

# plot size configuration 
pyplot.rcParams['figure.figsize'] = [10, 10]

# subplots (average pace, lap-by-lap pace)
fig, ax = pyplot.subplots(2)

# average racepace
laptimes = [laps.pick_driver(x)['LapTimeSeconds'].dropna() for x in drivers]
ax[0].boxplot(laptimes, labels=drivers)
ax[0].set_title('Average pace')
ax[0].set(ylabel = 'Laptime (seconds)')

# laptimes (lap-by-lap)
for driver in drivers:
    driver_laps = laps.pick_driver(driver)[['LapNumber', 'LapTimeSeconds', 'Team']]
    driver_laps = driver_laps.dropna()
    team = pd.unique(driver_laps['Team'])[0]
    x = driver_laps['LapNumber']
    poly = np.polyfit(driver_laps['LapNumber'], driver_laps['LapTimeSeconds'], 5)
    y_poly = np.poly1d(poly)(driver_laps['LapNumber'])

    linestyle = '.'
    # labels and headers
    ax[1].plot(x, y_poly, label=driver, color=ff.plotting.team_color(team), linestyle=linestyle)
    ax[1].set(ylabel='Laptime (seconds)')
    ax[1].set(xlabel='Lap')

    ax[1].legend()
    if team not in teams:
        teams.append(team)

if 'Haas F1 Team' in teams:
    ax[1].set_facecolor("grey")
    
fig.suptitle(f"{race.event['EventName']}")

# save the plot in an image if the user says so 
if '-s' or '--save' in sys.argv:
    # if the -n or --name option is given, sets the filename to it, 
    # default filename is country-sessiontype-year.png (e.g. austria-race-2022.png)
    filename = ""
    if '-n' in sys.argv or '--name' in sys.argv:
        arg = '-n' if '-n' in sys.argv else '--name'
        filename = f"{sys.argv[sys.argv.index(arg) + 1]}.png"
    else:
        filename = f"{str(race.event['EventDate'])[:4]}-{race.event['Country']}-{race.name}.png"
        
    pyplot.savefig(filename, dpi=300)
    
    
# Checking if the user wants to see the plot or not.
if not '-no' in sys.argv and not '--no-output' in sys.argv:
    pyplot.show()

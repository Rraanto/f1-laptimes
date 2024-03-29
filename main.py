import fastf1 as ff
from fastf1 import plotting
import pandas as pd
from matplotlib import pyplot
from matplotlib.pyplot import figure
from matplotlib import cm
import numpy as np
import os
from datetime import datetime as dt
import argparse

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
LATEST_SEASON = 2022  # have to update manually


# enabling the ff1 cache
done = False
while not done:
    try:
        ff.Cache.enable_cache(
            '/Users/rantonyainarakotondrajoa/f1-laptimes/.cache')
        done = True
    except NotADirectoryError:
        os.mkdir(os.path.join(CURRENT_PATH, ".cache/"))

# avoid pandas error
pd.options.mode.chained_assignment = None


def get_latest_race_name(schedule):
    """
    Given a schedule, return the name of the latest race that has already happened. 
    :param schedule: the schedule dataframe
    :return: The latest race name.
    """
    today_date = dt.now()
    latest = None
    for _, event in schedule.iterrows():
        if event['EventDate'] < today_date or dt.now().year > LATEST_SEASON:
            latest = event
        else:
            return latest['EventName']
    print(f"Latest race is : {latest['EventName']}")
    return latest['EventName']


# argparse settings
description = """
f1-laptimes is a tool for visualizing lap-by-lap pace and average pace over a Formula 1 session.
"""

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter, description=description)

parser.add_argument("-y", "--year", metavar="YEAR", type=int, default=LATEST_SEASON,
                    help="The year of the session to analyze, default is the current year.")

parser.add_argument("-t", "--track", metavar="TRACK", default=get_latest_race_name(ff.get_event_schedule(LATEST_SEASON)),
                    help="The track of the session to analyse, default is the latest available session in the year.")

parser.add_argument("-d", "--drivers", metavar="DRIVERS", type=str,
                    nargs='+', help="The drivers to analyze, default is all drivers.")

parser.add_argument("-df", "--drivers-file", metavar="DRIVERS_FILE", type=str,
                    help="Path to a file containing a comma separated list of drivers to display. If both a file and a list of drivers are given as arguments, the file will be ignored")

parser.add_argument("-s", "--save", action='store_true',
                    help="Save the figure in a file.")

parser.add_argument("-b", "--backup", action='store_true',
                    help="Backup the image in the remote github repository.")

parser.add_argument("-no", "--no-output", action='store_true',
                    help="Don't display the figure.")

parser.add_argument("--session", metavar="SESSION", type=str, default="R",
                    help="The session of the weekend to analyze : R (race), Q (qualifying), FP1, FP2, FP3, S (sprint). Race is set by default")

parser.add_argument("--message", type=str, default="",
                    help="Add custom message to the commit of a backup")

parser.add_argument("--clear-cache", action='store_true',
                    help="clear the cache (before executing, the cache of the latest execution will be stored)")

args = vars(parser.parse_args())
YEAR = args['year']
schedule = ff.get_event_schedule(YEAR)

GP = None
race = None
session = args['session']

try:
    GP = int(args['track'])
    race = schedule.get_event_by_round(GP)
except ValueError:
    GP = args['track']
    race = schedule.get_event_by_name(GP)
race = race.get_session(session)

laps = race.load_laps()
laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

# exclude pit stop laps
laps = laps.loc[(laps['PitOutTime'].isnull() & laps['PitInTime'].isnull())]

# using IQR to remove outliers
# quantiles
q75, q25 = laps['LapTimeSeconds'].quantile(
    0.75), laps['LapTimeSeconds'].quantile(0.25)
inter = q75 - q25
laptime_max = q75 + (1.5 * inter)
laptime_min = q25 - (1.5 * inter)

laps.loc[laps['LapTimeSeconds'] < laptime_min, 'LapTimeSeconds'] = np.nan
laps.loc[laps['LapTimeSeconds'] > laptime_max, 'LapTimeSeconds'] = np.nan

# plotting
if args['drivers']:
    drivers = [driver.upper() for driver in args['drivers']]
else:
    drivers = [driver[1][2] for driver in race.results.iterrows()]
teams = []

# plot size configuration
pyplot.rcParams['figure.figsize'] = [10, 10]
# subplots (average pace, lap-by-lap pace)
fig, ax = pyplot.subplots(2)

# average racepace
laptimes = [laps.pick_driver(x)['LapTimeSeconds'].dropna() for x in drivers]
ax[0].boxplot(laptimes, labels=drivers)
ax[0].set_title('Average pace')
ax[0].set(ylabel='Laptime (seconds)')

# laptimes (lap-by-lap)
for driver in drivers:
    try:
        driver_laps = laps.pick_driver(
            driver)[['LapNumber', 'LapTimeSeconds', 'Team']]
        driver_laps = driver_laps.dropna()
        team = pd.unique(driver_laps['Team'])[0]
        x = driver_laps['LapNumber']
        poly = np.polyfit(driver_laps['LapNumber'],
                          driver_laps['LapTimeSeconds'], 5)
        y_poly = np.poly1d(poly)(driver_laps['LapNumber'])

        linestyle = '-' if team not in teams else ':'
        # labels and headers
        ax[1].plot(x, y_poly, label=driver,
                   color=ff.plotting.team_color(team), linestyle=linestyle)
        ax[1].set(ylabel='Laptime (seconds)')
        ax[1].set(xlabel='Lap')

        ax[1].legend()
        if team not in teams:
            teams.append(team)
    except IndexError:
        pass

if 'Haas F1 Team' in teams:
    ax[1].set_facecolor("grey")

fig.suptitle(f"{race.event['EventName']}")

# save the figure
if args['save']:
    filename = f"{str(race.event['EventDate'])[:4]}-{race.event['Country']}-{race.name}.png"
    pyplot.savefig(f"outputs/{filename}" if os.path.isdir(
        os.path.join(CURRENT_PATH, 'outputs')) else filename, dpi=300)

    # add the file to the repository and commit change
    os.system(f'git add outputs/{filename}')

    # if backup option is enabled, create a backup of the file on the github remote repository
    if args['backup']:
        message = f"Plotted {str(race.event['EventDate'])[:4]} {race.event['Country']} Grand Prix {race.name} data" if args['message'] == "" else args['message']
        os.system(f"""git commit -a -m "{message}" """)
        with open('outputs/.history', mode='w') as history_file:
            history_file.write(f"On {dt.now()} - backed up {filename}\n")
        os.system("git push")

# display the figure
if not args['no_output']:
    pyplot.show()

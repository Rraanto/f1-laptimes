import fastf1 as ff
from fastf1 import plotting 
import pandas as pd
from matplotlib import pyplot
from matplotlib.pyplot import figure
from matplotlib import cm
import numpy as np
import sys 

# storing the session specificities 
YEAR = 2022
if '-y' or '--year' in sys.argv :
    arg = '-y' if '-y' in sys.argv else '--year'
    YEAR = int(sys.argv[sys.argv.index(arg) + 1])

arg_track = '-t' if '-t' in sys.argv else '--track'
GP = sys.argv[sys.argv.index(arg_track) + 1]

DRIVERS = None
if '-d' in sys.argv or '--drivers' in sys.argv:
    arg = '-d' if '-d' in sys.argv else '--drivers'
    DRIVERS = [txt.upper() for txt in sys.argv[sys.argv.index(arg) + 1].split(",")] 
else:
    DRIVERS = ['HAM', 'RUS', 'VER', 'PER', 'LEC', 'SAI', 'OCO', 'ALO', 'NOR', 'RIC', 'MSC', 'MAG', 'ALB', 'LAT', 'VET', 'STR']

# enabling the cache 
ff.Cache.enable_cache('.cache/')

# avoid pandas error 
pd.options.mode.chained_assignment = None 

# load session data / convert laptimes to seconds  
race = ff.get_session(YEAR, GP, 'R')
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

    linestyle = '-' if team not in teams else ':'
    # labels and headers
    ax[1].plot(x, y_poly, label=driver, color=ff.plotting.team_color(team), linestyle=linestyle)
    ax[1].set(ylabel='Laptime (seconds)')
    ax[1].set(xlabel='Lap')

    ax[1].legend()
    if team not in teams:
        teams.append(team)

if '-s' or '--save' in sys.argv:
    pyplot.savefig(f"{GP}-{YEAR}-racepace.png", dpi=300)       

if 'Haas F1 Team' in teams:
    ax[1].set_facecolor("grey")
pyplot.show()
# Camber Extravaganza

App for Assetto Corsa to show wheel camber angles in real time, helpful for tuning suspension.

Shows instantaneous and peak camber, and has an optional short-term history graph with some settings to play with.

Calculates optimal camber from config files - per car, per tire compound.  Turns blue when camber is too negative, green when near optimal camber, and red when too positive.

## Installation

1. Extract the **apps** and **content** folders to steamapps\\common\\assettocorsa\\
2. Enable the app in Options > General
3. Enable the app in-game

## Screenshots and Video

![screenshot](https://i.imgur.com/mMGKESZ.jpg)
![screenshot](https://thumbs.gfycat.com/CourteousSlimyCanvasback-size_restricted.gif)
[![youtube](https://i.imgur.com/CjyzZ9t.png)](https://www.youtube.com/watch?v=IMbU8Rjkklg)]

## How to Use

Adjust camber to try to keep as many wheels green as possible through turns, giving preference to the outside wheels.  If the outside wheels are mostly blue, add more positive camber.  If the outside wheels are mostly red, add more negative camber.

Once everything is mostly green, add some positive camber to the fronts or rears to tweak balance if necessary.

#### Mod cars

If your target camber is showing 999°, the app can't find data for your car.  You can add it to any custom file ending in `.json` that won't be overwritten by updates.

For example, adding [garyjpaterson's Dallara FX17](http://www.racedepartment.com/downloads/dallara-fx-17.13928/) with semislicks (short name "SM") would look like this:

```
{
	"dallara_fx17": { 
        	"FRONT": {
			"SM": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.81}
		},
        	"REAR": {
			"SM": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.81}
		}
	},
}
```

Adding any more cars follows the same pattern as tyres-data.json, for example a fictional Abarth 500 Stage 2 with Soft, Medium, and Hard slicks:

```
{
	"dallara_fx17": {
        	"FRONT": {
			"SM": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.81}
		},
        	"REAR": {
			"SM": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.81}
		}
	},
	"abarth500_s2": {
        	"FRONT": {
			"S": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.8071},
			"M": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.8071},
			"H": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.8071}
		},
        	"REAR": {
			"S": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.8071},
			"M": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.8071},
			"H": {"DCAMBER_0": 1.2, "DCAMBER_1": -13.0, "LS_EXPY": 0.8071}
		}
	},
}
```

More examples can be found in the included `tyres_data\*.json` files.

## Calculation Details

Grip in Assetto Corsa is multiplied by a factor determined by camber.

![screenshot](https://i.imgur.com/TRScBxn.png)

Where x is camber measured in radians. Converted to degrees and plotted on a graph, it looks like this for the Ferrari 458 GT2:

![screenshot](https://i.imgur.com/U1J02EN.png)

Peak grip for a single wheel (blue) is acheived at roughly -3.3°, but the total axle grip is the important value.  As the inside wheel during a turn effectively has inverse camber, it must also be calculated (red) and added to the outside wheel, weighted by the tire's load sensitivity factor.  This gives total grip for the axle (yellow), peaking somewhere below the single-wheel target.

#### More Math

DY_LS_FL is front-left load sensitivity, TIRE_LOAD_FL is the vertical force on the tire in Newtons, and the rest of the variables are found in the car's tyres.ini. 

![screeshot](https://i.imgur.com/HNeTLnQ.png)



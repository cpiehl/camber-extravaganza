# Camber Extravaganza

App for Assetto Corsa to show wheel camber angles in real time, helpful for tuning suspension.

Shows instantaneous and peak camber, and has an optional short-term history graph with some settings to play with.

Calculates optimal camber from config files - per car, per tire compound.  Turns blue when camber is too negative, green when near optimal camber, and red when too positive.

## Screenshots and Video

![screenshot](https://i.imgur.com/mMGKESZ.jpg)
![screenshot](https://thumbs.gfycat.com/CourteousSlimyCanvasback-size_restricted.gif)
[![youtube](https://i.imgur.com/CjyzZ9t.png)](https://www.youtube.com/watch?v=IMbU8Rjkklg)]

## How to Use

Adjust camber to try to keep as many wheels green as possible through turns, giving preference to the outside wheels.  If the outside wheels are mostly blue, add more positive camber.  If the outside wheels are mostly red, add more negative camber.

Once everything is mostly green, add some positive camber to the fronts or rears to tweak balance if necessary.

#### Mod cars

If your target camber is showing 999°, the app can't find data for your car.  You can add it to a custom file `tyre-data-custom.json` that won't be overwritten by updates.

For example, adding [garyjpaterson's Dallara FX17](http://www.racedepartment.com/downloads/dallara-fx-17.13928/) with semislicks (short name "SM") would look like this:

```
{
	"dallara_fx17": { 
		"SM": {"dcamber0": 1.2, "dcamber1": -13.0, "radius": 0.3106}
	},
}
```

More examples can be found in the full `tyres-data.json` file.

## Calculation Details

Grip in Assetto Corsa is multiplied by a factor determined by camber.

![screenshot](https://i.imgur.com/CTAz7dG.png)

Where x is camber measured in radians. Converted to degrees and plotted on a graph, it looks like this for the Ferrari 458 GT2:

![screenshot](https://i.imgur.com/NphyF5V.png)

Peak grip is acheived at roughly -3.3°, but given its quadratic nature not much grip is lost even at ±1° from peak.  This is why we get it close to start and use any remaining adjustment for front/rear balance.

## Installation

1. Save camber-extravaganza.py and tyres-data.json in steamapps\common\assettocorsa\apps\python\camber-extravaganza\
2. Enable the app in Options > General
3. Enable the app in-game

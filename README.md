# Extended window status
Extend window status custom integration for Home Assistant

## What can it do for you?
Show not only a open/close status like most window/door sensors but also the tilted opening which you find typically on european style windows.
You will get a nice human readable status ("Open/Closed/Tilted") to show in your dashboards.

## Use with Shelly BLU Door/Window
The Shelly BLU Door/Window sensor has beside a binary open/close entity a rotation entity that can be used to determine a "tilt open".
To configure, use mode "Rotary value" and select the binary open/close entity as primary, the rotation as secondary entity

## Use with two window sensors on one window
Place one sensor on the upper side, the other on the lower side of the window. The lower sensor will only open when fully opened, the upper will also open when tilted.
To configure, choose mode "Another window sensor" and select the upper sensor as the second entity




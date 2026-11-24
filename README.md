<p align="center">
  <img src="freecad/kle2freecad/resources/icons/kle2sketch.svg" width="96" height="96" />
</p>

# KLE Plate Generator for FreeCAD

Convert your Keyboard-Layout-Editor.com (KLE) layout to a FreeCAD sketch.

## Key Notes

- This add-on is under development and works in a basic way. Several features can be added, but I have no time for them now. Helpers are welcome.

## How to Install

Clone this repo into the `Mod` folder of your FreeCAD user folder. FreeCAD 1.1 has a user folder for each version, for example `v1-1`.

- On Linux it is usually `/home/username/.local/share/FreeCAD/v1-1/Mod/`
- On Windows it is `%APPDATA%\FreeCAD\v1-1\Mod\`, which is usually `C:\Users\your_user_name\AppData\Roaming\FreeCAD\v1-1\Mod\`
- On macOS it is usually `/Users/username/Library/Application Support/FreeCAD/v1-1/Mod/`
- *(To find the user folder, type `App.getUserAppDataDir()` in the Python console. If the `Mod` folder does not exist, make it.)*

In the `Mod` folder, type:

```sh
git clone https://github.com/k33b0/kle2freecad
```

## How to Use

*(I will expand this section later.)*

- Restart FreeCAD, then select the **KLE Plate Generator** workbench.
- The workbench has two buttons: **Plate cutouts** and **Import plate DXF or SVG**.
- **Plate cutouts** opens the generator dialog, which asks for your KLE "raw" data.
- **Import plate DXF or SVG** opens a file dialog. Select a DXF or SVG file from a plate generator.
- Both buttons make a sketch of the plate cutouts.

## Current Limits

### KLE to sketch

- Only generates simple Cherry MX Basic key footprints.
- Only generates simple Cherry MX Basic stab cutouts (PCB mount).

### DXF and SVG import

- Tested only with files from the [ai03 Plate Generator](https://kbplate.ai03.com) (Cherry MX and EC cutouts). Files from other generators have not been tested.
- The import uses the outer frame of the plate to center the cutouts. Without a frame, it centers on the cutouts.
- DXF files are tested only with lines, arcs, and circles.
- SVG files can use only `<path>` (commands M, L, H, V, A, Z) and `<circle>`. Transforms, curves, and elliptical arcs are not supported.
- The inside corners of merged cutouts get a fixed radius of 0.5 mm.
- Kerf comes from the generator. The import does not add kerf.

## Next?

- Further develop the generator to make other key and stab footprints.
- Further develop the generator with features such as key rotation.

> When? I have no time for now, so it depends on help from others.

## Support

- None
- ... but if you are good at coding *(or **really good** at driving AI)*, start with a PR.

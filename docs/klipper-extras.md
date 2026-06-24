# Experimental Klipper CNC Extras

This repository includes optional Klipper modules:

- `work_coordinate_systems.py` adds persistent G54-G59 work coordinates,
  G53 machine mode, and G10 L2/L20.
- `touch_probe.py` adds guarded XY stylus probing for edges, centers, and
  bores, plus reference Z surface probing.
- `tool_setter.py` uses a fixed machine-mounted tool setter to re-touch Z after
  manual tool changes.

The WCS and XY probe modules were originally developed by **Shadowphyre from
the E3CNC Discord community** and shared for beta testing. Klipper Screen CNC
hardens and extends them for this fork. The cutting-tool Z workflow is a
separate module derived from the same endstop-probing approach.

!!! warning

    These modules can move a CNC machine outside ordinary G-code execution.
    Test every direction with the spindle off, low speeds, generous clearance,
    and immediate access to an emergency stop.

## Install

Copy the modules into the active Klipper source tree:

```sh
cp klipper-extras/work_coordinate_systems.py ~/klipper/klippy/extras/
cp klipper-extras/touch_probe.py ~/klipper/klippy/extras/
cp klipper-extras/tool_setter.py ~/klipper/klippy/extras/
```

On installations where Klipper lives elsewhere, copy them into that
installation's `klippy/extras/` directory. Restart Klipper after adding or
updating either file.

## Work Coordinate Systems

Add:

```ini
[work_coordinate_systems]
persist_file: ~/printer_data/config/wcs_offsets.json
```

The module intentionally waits until XYZ are homed before applying the saved
WCS. This prevents stale offsets from altering the unhomed coordinate state
after a restart. Selecting G54-G59 is persisted automatically, even before
homing; the selected WCS is applied after the next full XYZ home.

Available commands:

```gcode
G54
G55
G53
G10 L2 P1 X10 Y20 Z30
G10 L20 P1 X0 Y0 Z0
WCS_STATUS
SAVE_WCS
```

`G53` remains modal in this experimental implementation. Select G54-G59 again
after machine-coordinate work. The bundled cancel/end macros already restore
the active WCS after parking.

## XY Stylus Probe

This probe is mounted in the ER11 collet and locates workpiece geometry.
Replacing it with a cutting tool does not invalidate XY because both tools
share the spindle centerline. Its Z result is a reference surface for setup
and tool-setter calibration; use the fixed tool setter after changing to a
cutting bit.

Example configuration:

```ini
[touch_probe]
pin: ^!PC5
fast_speed: 10
slow_speed: 0.5
max_distance: 50
retract_distance: 2
tip_diameter: 4.97
trigger_offset: 0
z_hop: 10
z_hop_speed: 10
overshoot: 10
samples: 1
spindle_object: output_pin spindle
```

The plugin rejects probing while a virtual-SD job is printing or paused, while
the configured spindle output is nonzero, when required axes are unhomed, or
when the probe is already triggered. A hop-over command also aborts if the full
requested Z clearance is unavailable within machine limits.

Raw and diagnostic commands:

```gcode
QUERY_TOUCH_PROBE
PROBE_X_POS
PROBE_X_NEG
PROBE_Y_POS
PROBE_Y_NEG
PROBE_Z_NEG
```

Workpiece commands:

```gcode
FIND_EDGE_X_POS
FIND_EDGE_X_NEG
FIND_EDGE_Y_POS
FIND_EDGE_Y_NEG
FIND_SURFACE_Z
FIND_CENTER_X DISTANCE=40
FIND_CENTER_Y DISTANCE=30
FIND_CENTER_XY DISTANCE_X=40 DISTANCE_Y=30
PROBE_BORE
```

Add `SET_ZERO=1` to a workpiece command to update the currently selected
G54-G59 coordinate directly:

```gcode
FIND_EDGE_X_NEG SET_ZERO=1
FIND_SURFACE_Z SET_ZERO=1
FIND_CENTER_XY DISTANCE_X=40 DISTANCE_Y=30 SET_ZERO=1
```

This does not use `G92`. The probe result is captured in machine coordinates,
then converted into a persistent WCS offset even though the tool has already
retracted from the contact surface.

## Calibration

`trigger_offset` is the empirical XY overtravel correction used together
with half the probe-tip diameter. It must be zero or positive.

Probe parameters such as `FAST_SPEED`, `SLOW_SPEED`, `MAX_DISTANCE`,
`RETRACT_DISTANCE`, `SAMPLES`, `Z_HOP`, `Z_HOP_SPEED`, and `OVERSHOOT` may be
overridden per command.

## Fixed Tool Setter

Configure this module when a switch or touch plate is permanently mounted on
the machine bed:

```ini
[tool_setter]
pin: ^!PC6
persist_file: ~/printer_data/config/tool_setter.json
setter_x: 186.5
setter_y: 246.5
safe_z: 60
travel_speed: 30
z_speed: 10
fast_speed: 5
slow_speed: 0.5
max_distance: 25
retract_distance: 2
final_retract: 5
trigger_offset: 0
samples: 1
spindle_object: output_pin spindle
```

The fixed setter can use a different input pin from the XY touch probe. It is
intended for manual setup and UI buttons, not automatic mid-job tool changes.

Typical setup:

1. Home XYZ, select the intended G54-G59 WCS, and use the XY/Z probing workflow
   to set the stock work zero.
2. With the same reference probe still installed, run:

   ```gcode
   CALIBRATE_TOOL_SETTER
   ```

   This moves to the configured `setter_x`/`setter_y`, probes down, and stores
   the fixed setter's Z height in the active WCS.

3. Replace the probe with the cutting bit.
4. Probe the bit against the fixed setter:

   ```gcode
   TOUCH_OFF_TOOL
   ```

   By default this only reports the calculated WCS Z adjustment.

5. Apply the adjustment after verifying the result:

   ```gcode
   TOUCH_OFF_TOOL APPLY=1
   ```

   `SET_ZERO=1` is accepted as an alias for UI consistency.

Available commands:

```gcode
QUERY_TOOL_SETTER
CALIBRATE_TOOL_SETTER
TOUCH_OFF_TOOL
```

Useful command overrides:

```gcode
CALIBRATE_TOOL_SETTER X=186.5 Y=246.5 SAFE_Z=60
TOUCH_OFF_TOOL SAMPLES=3 APPLY=1
```

The module requires homed XYZ, a selected G54-G59 WCS, spindle off, no active
print, and an open setter input before probing. It travels in machine
coordinates, lifts to `SAFE_Z`, moves to the fixed setter XY, probes downward,
and leaves Z retracted.

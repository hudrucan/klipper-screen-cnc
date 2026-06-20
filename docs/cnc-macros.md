# Example CNC Macros

The repository includes optional Klipper configuration examples:

- [`cnc_pause_resume.cfg`](https://github.com/hudrucan/klipper-screen-cnc/blob/master/config/examples/cnc_pause_resume.cfg)
- [`cnc_homing_override.cfg`](https://github.com/hudrucan/klipper-screen-cnc/blob/master/config/examples/cnc_homing_override.cfg)

Copy the required files into `~/printer_data/config/`, review every machine-specific
value, then include them from `printer.cfg`:

```ini
[include cnc_pause_resume.cfg]
[include cnc_homing_override.cfg]
```

Run `RESTART` after validating the configuration.

## Pause, Resume, and Cancel

Remove the complete Mainsail include from `printer.cfg`:

```ini
# Remove this:
[include mainsail.cfg]
```

The CNC pause example replaces the required job-control sections itself:

- `[virtual_sdcard]`
- `[pause_resume]`
- `[display_status]`
- `PAUSE`
- `RESUME`
- `CANCEL_PRINT`

- Pause stops file motion, lifts Z while the spindle is still running, then stops it.
- Resume is rejected while the spindle output is off.
- The operator starts the spindle manually and waits for it to stabilize before Resume.
- Cancel stops file motion, retracts Z while the spindle is running, stops the spindle,
  parks XY in machine coordinates, then restores the previously active WCS.
- `on_error_gcode: CANCEL_PRINT` ensures a virtual SD error also stops the spindle.

The example expects `[work_coordinate_systems]`, `[output_pin spindle]`, `M3`, and `M5`
to exist. Adjust the pause lift, cancel clearance, park coordinates, and movement speeds
for the machine.

Do not include `mainsail.cfg` at the same time. Duplicate base sections and command
overrides will prevent Klipper from loading.

## Homing Override

The homing example reads the axes passed to `G28`, allowing the touchscreen's Home X,
Home Y, Home Z, Home XY, and Home All actions to remain distinct.

The supplied example assumes Z and Y home at their upper limits while X homes at its
lower limit. Home All homes Z first, homes and releases X, then homes and releases Y.
Individual Home X and Home Y actions remain selectable, but first home Z when its
position is unknown or below the configured safe height.

Adjust `clearance_from_top`, `x_clearance`, `y_clearance`, and `clearance_speed` in the
example for the machine. With a Z maximum of 65 mm and `clearance_from_top: 10`, X/Y
homing requires Z to be at least 55 mm high. Test each axis with the spindle stopped and
enough physical clearance to reach an emergency stop.

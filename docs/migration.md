# Migration Notes

This fork intentionally breaks some upstream names to better match the CNC target.

## Remove Upstream KlipperScreen

Klipper Screen CNC replaces upstream KlipperScreen. Leaving the old service enabled can
start two GTK/X11 clients and make it appear that updates, restarts, or configuration
changes are being ignored.

Stop the old service and preserve the old checkout, environment, and config:

```sh
sudo systemctl disable --now KlipperScreen.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/KlipperScreen.service
sudo systemctl daemon-reload

mv ~/KlipperScreen ~/KlipperScreen.backup 2>/dev/null || true
mv ~/.KlipperScreen-env ~/.KlipperScreen-env.backup 2>/dev/null || true
mv ~/.config/KlipperScreen ~/.config/KlipperScreen.backup 2>/dev/null || true
mv ~/printer_data/config/KlipperScreen.conf \
  ~/printer_data/config/KlipperScreen.conf.backup 2>/dev/null || true
rm -f ~/.local/share/applications/KlipperScreen.desktop
```

Use `systemctl list-unit-files | grep -Ei 'klipper.?screen'` to find installations that
used a different service spelling. Disable any unit that launches the old
`~/KlipperScreen/screen.py`.

## Runtime Names

- `KlipperScreen.conf` is no longer searched automatically. Use `klipper_screen.conf`.
- `~/.config/KlipperScreen` was replaced by `~/.config/klipper_screen`.
- `~/.KlipperScreen-env` was replaced by `~/.klipper-screen-env`.
- `KlipperScreen.service` was replaced by `klipper-screen.service`.
- The expected checkout path in scripts and docs is `~/klipper-screen-cnc`.

Copy only the settings still needed from the backup config. Do not copy the old config
directory wholesale because upstream printer-specific menu entries may reference panels
removed by this fork.

## Sonic Pad Debian

The SonicPad-Debian `display-sleep.service` is separate from Klipper Screen CNC. Its
original script may switch the physical backlight off when X11 is temporarily
unavailable. Disable or patch that service if the display becomes black after restarting
the UI.

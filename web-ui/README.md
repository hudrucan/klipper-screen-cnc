# Web UI

This directory contains the in-progress web UI app derived from the upstream
E3CNC frontend.

Current goals:

- keep the CNC dashboard, file browser, metadata cards, and gcode viewer
- depend only on standard Moonraker runtime plus this repo's CNC metadata and
  `/server/cnc/*` compatibility layer
- remove product-ops, release-management, and other non-CNC features

Current debloat status:

- moved out of `vendor/` so it can be developed as a first-class app
- upstream E3CNC update/rollback hooks were removed earlier
- `HostBashPanel` was dropped because it depended on a missing host-shell API
  and is not part of the CNC runtime core

This app is not yet the primary shipped UI for this repository.

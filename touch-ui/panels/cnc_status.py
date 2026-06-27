import os

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    metrics = (
        ("file", "ACTIVE FILE"),
        ("feed_override", "FEED OVERRIDE"),
        ("requested_feed", "REQUESTED FEED"),
        ("max_velocity", "MAX VELOCITY"),
        ("host_load", "HOST LOAD"),
        ("free_ram", "FREE RAM"),
    )

    def __init__(self, screen, title):
        super().__init__(screen, title or "CNC Status")

        self.labels["state"] = self._status_label("READY")
        self.labels["mode"] = self._status_label("Absolute G90")
        self.labels["homed"] = self._status_label("Homed: none")

        chips = Gtk.Grid(column_homogeneous=True)
        chips.set_column_spacing(8)
        chips.attach(self.labels["state"], 0, 0, 1, 1)
        chips.attach(self.labels["mode"], 1, 0, 1, 1)
        chips.attach(self.labels["homed"], 2, 0, 1, 1)

        grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        columns = 2 if self._screen.vertical_mode else 3
        for index, (name, heading) in enumerate(self.metrics):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.set_hexpand(True)
            card.set_vexpand(True)
            card.get_style_context().add_class("cnc-status-card")

            label = Gtk.Label(label=heading, xalign=0)
            label.get_style_context().add_class("cnc-status-heading")
            card.pack_start(label, False, False, 0)

            self.labels[name] = Gtk.Label(label="--", xalign=0)
            self.labels[name].set_ellipsize(3)
            self.labels[name].get_style_context().add_class("cnc-status-value")
            card.pack_start(self.labels[name], True, True, 0)
            if name == "feed_override":
                event_box = Gtk.EventBox()
                event_box.set_visible_window(False)
                event_box.add(card)
                event_box.connect("button-press-event", self.open_feed_override)
                self.labels["metric_feed_override"] = event_box
                card = event_box
            grid.attach(card, index % columns, index // columns, 1, 1)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.pack_start(chips, False, False, 0)
        content.pack_start(grid, True, True, 0)
        self.content.add(content)

    @staticmethod
    def _status_label(text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("cnc-status")
        return label

    def process_update(self, action, data):
        if action != "notify_status_update":
            return

        state = self._printer.state or "unknown"
        absolute = self._printer.get_stat("gcode_move", "absolute_coordinates")
        homed_axes = self._printer.get_stat("toolhead", "homed_axes") or ""
        filename = self._printer.get_stat("print_stats", "filename") or ""
        speed_factor = float(self._printer.get_stat("gcode_move", "speed_factor") or 1)
        requested_speed = (
            float(self._printer.get_stat("gcode_move", "speed") or 0)
            * speed_factor
            / 60
        )
        max_velocity = float(self._printer.get_stat("toolhead", "max_velocity") or 0)
        system_stats = self._printer.get_stat("system_stats") or {}
        sysload = float(system_stats.get("sysload", 0))
        free_ram = float(system_stats.get("memavail", 0)) / 1024

        self.labels["state"].set_label(state.upper())
        self.labels["mode"].set_label("Absolute G90" if absolute else "Relative G91")
        self.labels["homed"].set_label(f"Homed: {homed_axes.upper() or 'none'}")
        self.labels["file"].set_label(os.path.basename(filename) if filename else "No active file")
        self.labels["feed_override"].set_label(f"{speed_factor * 100:.0f}%")
        self.labels["requested_feed"].set_label(f"{requested_speed:.1f} mm/s")
        self.labels["max_velocity"].set_label(f"{max_velocity:.1f} mm/s")
        self.labels["host_load"].set_label(f"{sysload:.2f}")
        self.labels["free_ram"].set_label(f"{free_ram:.0f} MB")

    def open_feed_override(self, widget=None, event=None):
        self._screen.show_panel("feed_override")
        return True

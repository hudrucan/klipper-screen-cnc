import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    minimum = 10
    maximum = 150

    def __init__(self, screen, title):
        super().__init__(screen, title or "Motion Override")
        self.value = 100
        self.buttons = {}

        self.labels["value"] = Gtk.Label(label="100%")
        self.labels["value"].get_style_context().add_class("cnc-override-value")

        self.labels["note"] = Gtk.Label(
            label="Applies to all Klipper G0 and G1 motion through M220",
            wrap=True,
        )
        self.labels["note"].get_style_context().add_class("cnc-override-note")

        adjust = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        adjust.set_column_spacing(8)
        for index, delta in enumerate((-10, -5, 5, 10)):
            name = f"adjust_{delta}"
            icon = "decrease" if delta < 0 else "increase"
            self.buttons[name] = self._gtk.Button(icon, f"{delta:+d}%", f"color{index % 4 + 1}")
            self.buttons[name].connect("clicked", self.adjust, delta)
            adjust.attach(self.buttons[name], index, 0, 1, 1)

        self.buttons["reset"] = self._gtk.Button("refresh", "Reset 100%", "color3")
        self.buttons["reset"].connect("clicked", self.set_override, 100)

        presets = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        presets.set_column_spacing(8)
        presets.set_row_spacing(8)
        for index, value in enumerate((25, 50, 75, 100, 125, 150)):
            name = f"preset_{value}"
            self.buttons[name] = self._gtk.Button(None, f"{value}%", f"color{index % 4 + 1}")
            self.buttons[name].connect("clicked", self.set_override, value)
            presets.attach(self.buttons[name], index % 3, index // 3, 1, 1)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_halign(Gtk.Align.FILL)
        content.set_valign(Gtk.Align.FILL)
        content.pack_start(self.labels["value"], True, True, 0)
        content.pack_start(adjust, False, False, 0)
        content.pack_start(self.buttons["reset"], False, False, 0)
        content.pack_start(presets, False, False, 0)
        content.pack_start(self.labels["note"], False, False, 0)
        self.content.add(content)

    def activate(self):
        self.update_value()

    def process_update(self, action, data):
        if action == "notify_status_update" and "gcode_move" in data:
            self.update_value()

    def update_value(self):
        factor = float(self._printer.get_stat("gcode_move", "speed_factor") or 1)
        self.value = round(factor * 100)
        self.labels["value"].set_label(f"{self.value}%")
        self.update_buttons()

    def update_buttons(self):
        usable = self._printer.state in {"ready", "printing", "paused"}
        for name, button in self.buttons.items():
            button.set_sensitive(usable)
            if name.startswith("adjust_"):
                delta = int(name.split("_", 1)[1])
                button.set_sensitive(
                    usable and self.minimum <= self.value + delta <= self.maximum
                )

    def adjust(self, widget, delta):
        self.apply_override(self.value + delta)

    def set_override(self, widget, value):
        self.apply_override(value)

    def apply_override(self, value):
        value = min(max(round(value), self.minimum), self.maximum)
        self.value = value
        self.labels["value"].set_label(f"{value}%")
        self.update_buttons()
        self._screen._ws.api.gcode_script(f"M220 S{value}")

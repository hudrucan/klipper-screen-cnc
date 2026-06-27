import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    pin = "output_pin spindle"

    def __init__(self, screen, title):
        super().__init__(screen, title or "Spindle")
        self.buttons = {}

        self.labels["state"] = Gtk.Label(label="OFF")
        self.labels["state"].get_style_context().add_class("cnc-spindle-state")
        commands = "M3 / M4 / M5" if "M4" in self._printer.available_commands else "M3 / M5"
        self.labels["source"] = Gtk.Label(label=commands)
        self.labels["source"].get_style_context().add_class("cnc-spindle-source")

        state_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        state_box.set_valign(Gtk.Align.CENTER)
        state_box.set_vexpand(True)
        state_box.pack_start(self.labels["state"], True, True, 0)
        state_box.pack_start(self.labels["source"], False, False, 0)

        controls = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        controls.set_column_spacing(10)
        self.buttons["on"] = self._gtk.Button("cw", "ON", "color4")
        self.buttons["on"].connect("clicked", self.spindle_on)
        controls.attach(self.buttons["on"], 0, 0, 1, 1)

        column = 1
        if "M4" in self._printer.available_commands:
            self.buttons["ccw"] = self._gtk.Button("ccw", "CCW", "color3")
            self.buttons["ccw"].connect("clicked", self.spindle_ccw)
            controls.attach(self.buttons["ccw"], column, 0, 1, 1)
            column += 1

        self.buttons["off"] = self._gtk.Button("stop", "OFF", "color2")
        self.buttons["off"].connect("clicked", self.spindle_off)
        controls.attach(self.buttons["off"], column, 0, 1, 1)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.pack_start(state_box, True, True, 0)
        content.pack_end(controls, False, False, 0)
        self.content.add(content)

    def process_update(self, action, data):
        if action != "notify_status_update":
            return
        value = float(self._printer.get_stat(self.pin, "value") or 0)
        running = value > 0
        self.labels["state"].set_label("ON" if running else "OFF")
        context = self.labels["state"].get_style_context()
        if running:
            context.add_class("cnc-spindle-running")
        else:
            context.remove_class("cnc-spindle-running")
        self.buttons["on"].set_sensitive(not running)
        if "ccw" in self.buttons:
            self.buttons["ccw"].set_sensitive(not running)
        self.buttons["off"].set_sensitive(running)

    def spindle_on(self, widget):
        self._screen._confirm_send_action(
            widget,
            "Start spindle clockwise with <b>M3</b>?",
            "printer.gcode.script",
            {"script": "M3"},
        )

    def spindle_ccw(self, widget):
        self._screen._confirm_send_action(
            widget,
            "Start spindle counter-clockwise with <b>M4</b>?",
            "printer.gcode.script",
            {"script": "M4"},
        )

    def spindle_off(self, widget):
        self._screen._send_action(
            widget,
            "printer.gcode.script",
            {"script": "M5"},
        )

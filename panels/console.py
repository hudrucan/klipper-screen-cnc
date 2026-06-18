import re
import time

import gi

gi.require_version("Gtk", "3.0")
from datetime import datetime

from gi.repository import Gtk

from ks_includes.screen_panel import ScreenPanel

COLORS = {
    "command": "#bad8ff",
    "error": "#ff6975",
    "response": "#b8b8b8",
    "time": "grey",
    "warning": "#c9c9c9",
}


class Panel(ScreenPanel):
    def __init__(self, screen, title):
        title = title or "MDI"
        super().__init__(screen, title)
        self.autoscroll = True
        self.command_history = []
        self.history_position = 0

        self.labels["state"] = self._status_label("OFFLINE")
        self.labels["mode"] = self._status_label("G54 · G90 · G21")
        self.labels["homed"] = self._status_label("Homed: none")

        status = Gtk.Grid(column_homogeneous=True)
        status.set_column_spacing(8)
        status.attach(self.labels["state"], 0, 0, 1, 1)
        status.attach(self.labels["mode"], 1, 0, 1, 1)
        status.attach(self.labels["homed"], 2, 0, 1, 1)

        o1_button = self._gtk.Button(
            "arrow-down", _("Auto-scroll") + " ", None, self.bts, Gtk.PositionType.RIGHT, 1
        )
        o1_button.get_style_context().add_class("button_active")
        o1_button.get_style_context().add_class("buttons_slim")
        o1_button.connect("clicked", self.set_autoscroll)

        o2_button = self._gtk.Button(
            "refresh", _("Clear") + " ", None, self.bts, Gtk.PositionType.RIGHT, 1
        )
        o2_button.get_style_context().add_class("buttons_slim")
        o2_button.connect("clicked", self.clear)

        options = Gtk.Grid(vexpand=False)
        options.attach(o1_button, 0, 0, 1, 1)
        options.attach(o2_button, 1, 0, 1, 1)

        sw = Gtk.ScrolledWindow(hexpand=True, vexpand=True)

        tb = Gtk.TextBuffer()
        tv = Gtk.TextView(buffer=tb, editable=False, cursor_visible=False)
        tv.connect("size-allocate", self._autoscroll)
        tv.connect("touch-event", self._screen.remove_keyboard)
        tv.connect("button-press-event", self._screen.remove_keyboard)

        sw.add(tv)

        ebox = Gtk.Box(hexpand=True, vexpand=False)

        entry = Gtk.Entry(hexpand=True, vexpand=False)
        entry.connect("button-press-event", self._screen.show_keyboard)
        entry.connect("touch-event", self._screen.show_keyboard)
        entry.connect("activate", self._send_command)
        entry.set_placeholder_text("Enter one MDI command")
        entry.grab_focus_without_selecting()

        previous = self._gtk.Button("arrow-up", scale=0.55)
        previous.get_style_context().add_class("buttons_slim")
        previous.set_hexpand(False)
        previous.set_tooltip_text("Previous MDI command")
        previous.connect("clicked", self.history_previous)

        next_command = self._gtk.Button("arrow-down", scale=0.55)
        next_command.get_style_context().add_class("buttons_slim")
        next_command.set_hexpand(False)
        next_command.set_tooltip_text("Next MDI command")
        next_command.connect("clicked", self.history_next)

        send = self._gtk.Button(
            "resume", " " + _("Send") + " ", None, 0.66, Gtk.PositionType.RIGHT, 1
        )
        send.get_style_context().add_class("buttons_slim")

        send.set_hexpand(False)
        send.connect("clicked", self._send_command)

        ebox.add(previous)
        ebox.add(next_command)
        ebox.add(entry)
        ebox.add(send)

        self.labels.update(
            {
                "entry": entry,
                "send": send,
                "sw": sw,
                "tb": tb,
                "tv": tv,
            }
        )

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content_box.pack_start(status, False, False, 0)
        content_box.pack_start(options, False, False, 5)
        content_box.add(sw)
        content_box.pack_end(ebox, False, False, 0)
        self.content.add(content_box)

    @staticmethod
    def _status_label(text):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class("cnc-status")
        return label

    def clear(self, widget=None):
        self.labels["tb"].set_text("")

    def add_gcode(self, msgtype, msgtime, message):
        if msgtype == "command":
            color = COLORS["command"]
        elif message.startswith("!!"):
            color = COLORS["error"]
            message = message.replace("!! ", "")
        elif message.startswith("//"):
            color = COLORS["warning"]
            message = message.replace("// ", "")
        elif re.match("^(?:ok\\s+)?(B|C|T\\d*):", message):
            return
        else:
            color = COLORS["response"]

        message = f'<span color="{color}"><b>{message}</b></span>'

        message = message.replace("\n", "\n         ")

        self.labels["tb"].insert_markup(
            self.labels["tb"].get_end_iter(),
            f'\n<span color="{COLORS["time"]}">'
            f"{datetime.fromtimestamp(msgtime).strftime('%H:%M:%S')}</span> {message}",
            -1,
        )
        # Limit the length
        if self.labels["tb"].get_line_count() > 999:
            self.labels["tb"].delete(
                self.labels["tb"].get_iter_at_line(0), self.labels["tb"].get_iter_at_line(1)
            )

    def gcode_response(self, result, method, params):
        if method != "server.gcode_store":
            return

        for resp in result["result"]["gcode_store"]:
            self.add_gcode(resp["type"], resp["time"], resp["message"])

    def process_update(self, action, data):
        if action == "notify_gcode_response":
            self.add_gcode("response", time.time(), data)
        elif action == "notify_status_update":
            self.update_machine_state()

    def set_autoscroll(self, widget):
        self.autoscroll ^= True
        self.toggle_active_class(widget, self.autoscroll)

    @staticmethod
    def toggle_active_class(widget, cond):
        if cond:
            widget.get_style_context().add_class("button_active")
        else:
            widget.get_style_context().remove_class("button_active")

    def _autoscroll(self, *args):
        if self.autoscroll:
            adj = self.labels["sw"].get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())

    def _send_command(self, *args):
        cmd = self.labels["entry"].get_text().strip()
        if not cmd:
            return
        if not self.mdi_available():
            self._screen.show_popup_message("MDI is unavailable in the current machine state", 2)
            return

        self.labels["entry"].set_text("")
        self._screen.remove_keyboard()

        self.remember_command(cmd)
        self.history_position = len(self.command_history)
        self.add_gcode("command", time.time(), cmd)
        self._screen._ws.api.gcode_script(cmd)

    def activate(self):
        self.clear()
        self.update_machine_state()
        self._screen._ws.send_method("server.gcode_store", {"count": 100}, self.gcode_response)

    def remember_command(self, command):
        command = command.strip()
        if not command:
            return
        if not self.command_history or self.command_history[-1] != command:
            self.command_history.append(command)
        self.command_history = self.command_history[-50:]

    def history_previous(self, widget=None):
        if not self.command_history:
            return
        self.history_position = max(0, self.history_position - 1)
        self.labels["entry"].set_text(self.command_history[self.history_position])
        self.labels["entry"].set_position(-1)

    def history_next(self, widget=None):
        if not self.command_history:
            return
        self.history_position = min(len(self.command_history), self.history_position + 1)
        command = (
            self.command_history[self.history_position]
            if self.history_position < len(self.command_history)
            else ""
        )
        self.labels["entry"].set_text(command)
        self.labels["entry"].set_position(-1)

    def mdi_available(self):
        return self._printer.state in {"ready", "paused"}

    def update_machine_state(self):
        state = self._printer.state or "offline"
        absolute = self._printer.get_stat("gcode_move", "absolute_coordinates")
        homed_axes = self._printer.get_stat("toolhead", "homed_axes") or ""
        wcs = self._printer.get_stat("work_coordinate_systems") or {}
        active_wcs = "G53" if wcs.get("machine_mode") else wcs.get("active_wcs", "G54")

        self.labels["state"].set_label(state.upper())
        self.labels["mode"].set_label(
            f"{active_wcs} · {'G90' if absolute else 'G91'} · G21"
        )
        self.labels["homed"].set_label(f"Homed: {homed_axes.upper() or 'none'}")

        available = self.mdi_available()
        self.labels["entry"].set_sensitive(available)
        self.labels["send"].set_sensitive(available)

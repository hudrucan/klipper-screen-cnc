import logging
import os
from math import pi, trunc

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango

from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    axes = ("X", "Y", "Z")

    def __init__(self, screen, title):
        super().__init__(screen, title or "CNC Run")
        self.filename = ""
        self.file_metadata = {}
        self.state = "standby"
        self.progress = 0.0
        self.can_close = False
        self.thumb_dialog = None

        self.labels["progress_text"] = Gtk.Label(label="0%")
        self.labels["progress_text"].get_style_context().add_class("cnc-run-progress-text")
        self.labels["progress_ring"] = Gtk.DrawingArea()
        self.labels["progress_ring"].set_size_request(
            self._gtk.font_size * 6, self._gtk.font_size * 6
        )
        self.labels["progress_ring"].connect("draw", self.on_draw)

        progress = Gtk.Overlay()
        progress.add(self.labels["progress_ring"])
        progress.add_overlay(self.labels["progress_text"])

        self.labels["file"] = Gtk.Label(label="No active file", xalign=0)
        self.labels["file"].set_ellipsize(Pango.EllipsizeMode.END)
        self.labels["file"].get_style_context().add_class("cnc-run-filename")
        self.labels["state"] = self._chip("STANDBY")
        self.labels["message"] = Gtk.Label(xalign=0, no_show_all=True)
        self.labels["message"].set_ellipsize(Pango.EllipsizeMode.END)
        self.labels["message"].get_style_context().add_class("cnc-run-message")

        file_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        file_box.set_valign(Gtk.Align.CENTER)
        file_box.pack_start(self.labels["file"], False, False, 0)
        file_box.pack_start(self.labels["state"], False, False, 0)
        file_box.pack_start(self.labels["message"], False, False, 0)

        hero = Gtk.Grid()
        hero.set_column_spacing(16)
        hero.get_style_context().add_class("cnc-run-hero")
        hero.attach(progress, 0, 0, 1, 1)
        hero.attach(file_box, 1, 0, 1, 1)

        positions = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        positions.set_column_spacing(8)
        positions.set_row_spacing(8)
        for index, axis in enumerate(self.axes):
            positions.attach(self._position_card(axis), index, 0, 1, 1)

        metrics = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        metrics.set_column_spacing(8)
        metrics.set_row_spacing(8)
        metric_items = (
            ("coordinate", "COORDINATE", "--"),
            ("feed", "FEED", "0.0 / 0.0 mm/s"),
            ("override", "FEED OVERRIDE", "100%"),
            ("spindle", "SPINDLE", "OFF"),
            ("elapsed", "ELAPSED", "0s"),
            ("remaining", "REMAINING", "--"),
        )
        for index, (name, heading, value) in enumerate(metric_items):
            card = self._metric_card(name, heading, value)
            metrics.attach(card, index % 2, index // 2, 1, 1)

        if self.has_spindle():
            self.labels["metric_spindle"].connect(
                "button-press-event", self.open_spindle
            )
        self.labels["metric_override"].connect(
            "button-press-event", self.open_feed_override
        )

        body = Gtk.Grid(column_homogeneous=True, row_homogeneous=True)
        body.set_column_spacing(10)
        body.set_row_spacing(10)
        if self._screen.vertical_mode:
            body.attach(positions, 0, 0, 1, 1)
            body.attach(metrics, 0, 1, 1, 2)
        else:
            body.attach(positions, 0, 0, 3, 1)
            body.attach(metrics, 3, 0, 2, 1)

        self.create_buttons()
        self.buttons["button_grid"] = Gtk.Grid(
            column_homogeneous=True, row_homogeneous=True
        )
        self.buttons["button_grid"].set_column_spacing(8)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.pack_start(hero, False, False, 0)
        content.pack_start(body, True, True, 0)
        content.pack_end(self.buttons["button_grid"], False, False, 0)
        self.content.add(content)
        self.show_buttons_for_state()

    def _chip(self, text):
        label = Gtk.Label(label=text, xalign=0)
        label.get_style_context().add_class("cnc-status")
        return label

    def _position_card(self, axis):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        card.set_hexpand(True)
        card.set_vexpand(True)
        card.get_style_context().add_class("cnc-run-position-card")
        card.get_style_context().add_class(f"cnc-dro-card-{axis.lower()}")

        header = Gtk.Box()
        axis_label = Gtk.Label(label=axis, xalign=0)
        axis_label.get_style_context().add_class("cnc-run-axis")
        self.labels[f"homed_{axis}"] = Gtk.Label(label="OPEN", xalign=1)
        self.labels[f"homed_{axis}"].get_style_context().add_class("cnc-dro-homed")
        header.pack_start(axis_label, True, True, 0)
        header.pack_end(self.labels[f"homed_{axis}"], False, False, 0)
        card.pack_start(header, False, False, 0)

        machine_heading = Gtk.Label(label="MACHINE", xalign=0)
        machine_heading.get_style_context().add_class("cnc-status-heading")
        card.pack_start(machine_heading, False, False, 0)
        self.labels[f"machine_{axis}"] = Gtk.Label(label="--", xalign=0)
        self.labels[f"machine_{axis}"].get_style_context().add_class(
            "cnc-run-position-value"
        )
        card.pack_start(self.labels[f"machine_{axis}"], True, True, 0)

        work_heading = Gtk.Label(label="WORK", xalign=0)
        work_heading.get_style_context().add_class("cnc-status-heading")
        card.pack_start(work_heading, False, False, 0)
        self.labels[f"work_{axis}"] = Gtk.Label(label="--", xalign=0)
        self.labels[f"work_{axis}"].get_style_context().add_class(
            "cnc-run-work-value"
        )
        card.pack_start(self.labels[f"work_{axis}"], True, True, 0)
        return card

    def _metric_card(self, name, heading, value):
        event_box = Gtk.EventBox()
        event_box.set_visible_window(False)
        event_box.set_hexpand(True)
        event_box.set_vexpand(True)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        card.get_style_context().add_class("cnc-run-metric-card")
        label = Gtk.Label(label=heading, xalign=0)
        label.get_style_context().add_class("cnc-status-heading")
        card.pack_start(label, False, False, 0)
        self.labels[name] = Gtk.Label(label=value, xalign=0)
        self.labels[name].set_ellipsize(Pango.EllipsizeMode.END)
        self.labels[name].get_style_context().add_class("cnc-run-metric-value")
        card.pack_start(self.labels[name], True, True, 0)
        event_box.add(card)
        self.labels[f"metric_{name}"] = event_box
        return event_box

    def create_buttons(self):
        self.buttons = {
            "cancel": self._gtk.Button("stop", _("Cancel"), "color2"),
            "control": self._gtk.Button("settings", _("Settings"), "color3"),
            "menu": self._gtk.Button("complete", _("Main Menu"), "color4"),
            "pause": self._gtk.Button("pause", _("Pause"), "color1"),
            "restart": self._gtk.Button("refresh", _("Restart"), "color3"),
            "resume": self._gtk.Button("resume", _("Resume"), "color1"),
        }
        self.buttons["cancel"].connect("clicked", self.cancel)
        self.buttons["control"].connect("clicked", self._screen._go_to_submenu, "")
        self.buttons["menu"].connect("clicked", self.close_panel)
        self.buttons["pause"].connect("clicked", self.pause)
        self.buttons["restart"].connect("clicked", self.restart)
        self.buttons["resume"].connect("clicked", self.resume)

    def has_spindle(self):
        return (
            "M3" in self._printer.available_commands
            and "M5" in self._printer.available_commands
            and "output_pin spindle" in self._printer.get_output_pins()
        )

    def open_spindle(self, widget=None, event=None):
        if self.has_spindle():
            self._screen.show_panel("spindle")
        return True

    def open_feed_override(self, widget=None, event=None):
        self._screen.show_panel("feed_override")
        return True

    def activate(self):
        self.update_filename(self._printer.get_stat("print_stats", "filename") or "")
        self.set_state(self._printer.get_stat("print_stats", "state") or "standby")
        self.update_machine_values()
        self.update_time_and_progress()

    def process_update(self, action, data):
        if action == "notify_gcode_response":
            if "action:cancel" in data:
                self.set_state("cancelled")
            elif "action:paused" in data:
                self.set_state("paused")
            elif "action:resumed" in data:
                self.set_state("printing")
            return
        if action == "notify_metadata_update" and data["filename"] == self.filename:
            self.get_file_metadata(response=True)
            return
        if action != "notify_status_update":
            return

        if "display_status" in data and "message" in data["display_status"]:
            message = data["display_status"]["message"] or ""
            self.labels["message"].set_label(message)
            self.labels["message"].set_visible(bool(message))

        if "print_stats" in data:
            print_stats = data["print_stats"]
            if "state" in print_stats:
                self.set_state(print_stats["state"], print_stats.get("message", ""))
            if "filename" in print_stats:
                self.update_filename(print_stats["filename"])

        self.update_machine_values()
        if (
            "print_stats" in data
            or "virtual_sdcard" in data
            or "gcode_move" in data
        ):
            self.update_time_and_progress()

    def update_machine_values(self):
        machine = self._printer.get_stat("motion_report", "live_position") or ()
        work = self._printer.get_stat("gcode_move", "gcode_position") or ()
        homed_axes = self._printer.get_stat("toolhead", "homed_axes") or ""

        for index, axis in enumerate(self.axes):
            digits = 3 if axis == "Z" else 2
            machine_value = float(machine[index]) if len(machine) > index else 0
            work_value = float(work[index]) if len(work) > index else 0
            self.labels[f"machine_{axis}"].set_label(f"{machine_value:.{digits}f}")
            self.labels[f"work_{axis}"].set_label(f"{work_value:.{digits}f}")
            homed = axis.lower() in homed_axes
            self.labels[f"homed_{axis}"].set_label("HOMED" if homed else "OPEN")
            context = self.labels[f"homed_{axis}"].get_style_context()
            if homed:
                context.add_class("cnc-dro-homed-active")
            else:
                context.remove_class("cnc-dro-homed-active")

        wcs = self._printer.get_stat("work_coordinate_systems") or {}
        active_wcs = "G53" if wcs.get("machine_mode") else wcs.get("active_wcs", "G54")
        absolute = self._printer.get_stat("gcode_move", "absolute_coordinates")
        mode = "G90" if absolute else "G91"
        self.labels["coordinate"].set_label(f"{active_wcs}  ·  {mode}")

        speed_factor = float(self._printer.get_stat("gcode_move", "speed_factor") or 1)
        requested = (
            float(self._printer.get_stat("gcode_move", "speed") or 0)
            * speed_factor
            / 60
        )
        live = abs(float(self._printer.get_stat("motion_report", "live_velocity") or 0))
        self.labels["feed"].set_label(f"{live:.1f} / {requested:.1f} mm/s")
        self.labels["override"].set_label(f"{speed_factor * 100:.0f}%")

        spindle_on = (
            self.has_spindle()
            and float(self._printer.get_stat("output_pin spindle", "value") or 0) > 0
        )
        self.labels["spindle"].set_label("ON" if spindle_on else "OFF")
        spindle_context = self.labels["spindle"].get_style_context()
        if spindle_on:
            spindle_context.add_class("cnc-spindle-running")
        else:
            spindle_context.remove_class("cnc-spindle-running")

    def update_time_and_progress(self):
        progress = float(self._printer.get_stat("virtual_sdcard", "progress") or 0)
        gcode_start = self.file_metadata.get("gcode_start_byte")
        gcode_end = self.file_metadata.get("gcode_end_byte")
        if gcode_start is not None and gcode_end is not None and gcode_end > gcode_start:
            file_position = float(
                self._printer.get_stat("virtual_sdcard", "file_position") or 0
            )
            progress = max(file_position - gcode_start, 0) / (gcode_end - gcode_start)
        progress = min(max(progress, 0), 1)

        elapsed = float(self._printer.get_stat("print_stats", "print_duration") or 0)
        if elapsed < 1:
            elapsed = float(self._printer.get_stat("print_stats", "total_duration") or 0)

        estimate = 0
        if progress > 0.01 and elapsed > 0:
            estimate = elapsed / progress
        elif self.file_metadata.get("last_time"):
            estimate = float(self.file_metadata["last_time"])
        elif self.file_metadata.get("estimated_time"):
            estimate = float(self.file_metadata["estimated_time"])

        self.labels["elapsed"].set_label(self.format_time(elapsed))
        self.labels["remaining"].set_label(
            self.format_time(max(estimate - elapsed, 0)) if estimate > elapsed else "--"
        )
        self.update_progress(progress)

    def update_progress(self, progress):
        self.progress = min(max(float(progress), 0), 1)
        self.labels["progress_text"].set_label(f"{trunc(self.progress * 100)}%")
        self.labels["progress_ring"].queue_draw()

    def on_draw(self, drawing_area, context):
        width = drawing_area.get_allocated_width()
        height = drawing_area.get_allocated_height()
        radius = min(width, height) * 0.37
        context.translate(width / 2, height / 2)
        context.set_line_width(max(self._gtk.font_size * 0.55, 5))
        context.set_source_rgba(1, 1, 1, 0.12)
        context.arc(0, 0, radius, 0, 2 * pi)
        context.stroke()
        context.set_source_rgb(0.18, 0.66, 0.86)
        context.arc(0, 0, radius, -pi / 2, -pi / 2 + self.progress * 2 * pi)
        context.stroke()
        return False

    def set_state(self, state, msg=""):
        if state == "standby" and self.state == "cancelled":
            state = "cancelled"
        changed = self.state != state
        titles = {
            "printing": _("Working"),
            "paused": _("Paused"),
            "complete": _("Complete"),
            "error": _("Error"),
            "cancelling": _("Cancelling"),
            "cancelled": _("Cancelled"),
            "standby": _("Standby"),
        }
        self._screen.set_panel_title(titles.get(state, state.title()))
        self.labels["state"].set_label(state.upper())
        state_context = self.labels["state"].get_style_context()
        if state == "printing":
            state_context.add_class("cnc-run-state-active")
        else:
            state_context.remove_class("cnc-run-state-active")
        if changed and state in {"error", "cancelled"} and msg:
            self._screen.show_popup_message(msg)
        if state == "complete":
            self.update_progress(1)
        if changed:
            if state == "complete":
                timeout = self._config.get_main_config().getint("job_complete_timeout", 0)
                self._add_timeout(timeout)
            elif state == "error":
                timeout = self._config.get_main_config().getint("job_error_timeout", 0)
                self._add_timeout(timeout)
            elif state == "cancelled":
                timeout = self._config.get_main_config().getint("job_cancelled_timeout", 0)
                self._add_timeout(timeout)
            logging.debug("Changing CNC run state from '%s' to '%s'", self.state, state)
            self.state = state
        self.show_buttons_for_state()

    def show_buttons_for_state(self):
        for child in self.buttons["button_grid"].get_children():
            self.buttons["button_grid"].remove(child)

        if self.state == "printing":
            items = ("pause", "cancel", "control")
            self.can_close = False
        elif self.state == "paused":
            items = ("resume", "cancel", "control")
            self.can_close = False
        elif self.state == "cancelling":
            items = ("cancel", "control")
            self.can_close = False
        else:
            items = ("restart", "menu") if self.filename else ("menu",)
            self.can_close = True

        for index, name in enumerate(items):
            self.buttons["button_grid"].attach(self.buttons[name], index, 0, 1, 1)
        self.buttons["button_grid"].show_all()

    def new_print(self):
        self._screen.screensaver.close()
        self.update_progress(0)
        self.set_state("printing")

    def pause(self, widget):
        self._screen._send_action(widget, "printer.print.pause", {})

    def resume(self, widget):
        self._screen._send_action(widget, "printer.print.resume", {})

    def cancel(self, widget):
        buttons = [
            {"name": _("Cancel Job"), "response": Gtk.ResponseType.OK, "style": "dialog-error"},
            {"name": _("Go Back"), "response": Gtk.ResponseType.CANCEL, "style": "dialog-info"},
        ]
        label = Gtk.Label(hexpand=True, vexpand=True, wrap=True)
        label.set_markup(_("Cancel the active CNC job?"))
        self._gtk.Dialog(_("Cancel"), buttons, label, self.cancel_confirm)

    def cancel_confirm(self, dialog, response_id):
        self._gtk.remove_dialog(dialog)
        if response_id != Gtk.ResponseType.OK:
            return
        self.set_state("cancelling")
        self._screen._ws.api.print_cancel()

    def restart(self, widget):
        buttons = [
            {"name": _("Restart Job"), "response": Gtk.ResponseType.OK, "style": "dialog-default"},
            {"name": _("Go Back"), "response": Gtk.ResponseType.CANCEL, "style": "dialog-info"},
        ]
        label = Gtk.Label(hexpand=True, vexpand=True, wrap=True)
        label.set_markup(_("Restart this CNC job from the beginning?"))
        self._gtk.Dialog(_("Restart"), buttons, label, self.restart_confirm)

    def restart_confirm(self, dialog, response_id):
        self._gtk.remove_dialog(dialog)
        if response_id == Gtk.ResponseType.OK and self.filename:
            self._screen._ws.api.print_start(self.filename)
            self.new_print()

    def close_panel(self, widget=None):
        if self.can_close:
            self._screen.state_ready(wait=False)

    def _add_timeout(self, timeout):
        self._screen.screensaver.close()
        if timeout:
            GLib.timeout_add_seconds(timeout, self.close_panel)

    def update_filename(self, filename):
        if not filename or filename == self.filename:
            return
        self.filename = filename
        self.labels["file"].set_label(os.path.splitext(os.path.basename(filename))[0])
        self.get_file_metadata()

    def get_file_metadata(self, response=False):
        if self._files.file_metadata_exists(self.filename):
            self.file_metadata = self._files.get_file_info(self.filename)
            job_id = self.file_metadata.get("job_id")
            if job_id:
                self._screen._ws.api.get_single_job_history(job_id, self.set_last_time)
            self.update_time_and_progress()
        elif not response:
            self._files.request_metadata(self.filename)

    def set_last_time(self, data, method, params):
        if "error" in data or "result" not in data:
            return
        job = data["result"].get("job")
        if job and job.get("status") == "completed" and job.get("print_duration"):
            self.file_metadata["last_time"] = job["print_duration"]
            self.update_time_and_progress()

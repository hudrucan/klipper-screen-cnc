import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    def __init__(self, screen, title):
        super().__init__(screen, title or "Probe Result History")
        self.grid = Gtk.Grid(column_homogeneous=True)
        self.grid.set_column_spacing(10)
        self.grid.set_row_spacing(10)

        self.empty = Gtk.Label(
            label="No probe results yet",
            xalign=0.5,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
        )
        self.empty.get_style_context().add_class("cnc-probe-detail")

        self.scroll = self._gtk.ScrolledWindow()
        self.scroll.get_style_context().add_class("gcode-list-scroll")
        self.scroll.add(self.grid)
        self.content.add(self.scroll)

    def activate(self):
        self.update_status()

    def process_update(self, action, data):
        if action == "notify_status_update" and (
            "touch_probe" in data or "tool_setter" in data
        ):
            self.update_status()

    def update_status(self):
        self._clear_grid()
        entries = self._history_entries()
        if not entries:
            self.grid.attach(self.empty, 0, 0, 2, 1)
            self.grid.show_all()
            return

        columns = 1 if self._screen.vertical_mode else 2
        for index, entry in enumerate(entries):
            self.grid.attach(self._history_card(entry), index % columns, index // columns, 1, 1)
        self.grid.show_all()

    def _clear_grid(self):
        for child in self.grid.get_children():
            self.grid.remove(child)

    def _history_entries(self):
        touch = self._printer.get_stat("touch_probe") or {}
        setter = self._printer.get_stat("tool_setter") or {}
        wcs = self._printer.get_stat("work_coordinate_systems") or {}
        active_wcs = "G53" if wcs.get("machine_mode") else wcs.get("active_wcs", "G54")
        entries = []

        for raw in self._status_history(touch) + self._status_history(setter):
            entry = self._entry_from_raw(raw, active_wcs)
            if entry:
                entries.append(entry)

        surface = touch.get("surface_result")
        if surface:
            entries.append(self._surface_entry(surface))

        touch_result = touch.get("last_result")
        if touch_result:
            entries.append(self._touch_entry(touch, touch_result, active_wcs))

        setter_result = setter.get("last_result")
        if setter_result:
            entries.append(self._setter_entry(setter_result, active_wcs))

        calibration = setter.get("calibration")
        if calibration:
            entries.append(self._calibration_entry(calibration))

        return entries[:12]

    @staticmethod
    def _status_history(status):
        for key in ("history", "results"):
            value = status.get(key)
            if isinstance(value, list):
                return list(reversed(value))
        return []

    def _entry_from_raw(self, raw, active_wcs):
        if not isinstance(raw, dict):
            return None
        if raw.get("surface_result"):
            return self._surface_entry(raw["surface_result"])
        if raw.get("kind") == "surface" or raw.get("type") == "tilt":
            return self._surface_entry(raw)
        title = raw.get("title") or raw.get("command") or raw.get("name") or "Probe Result"
        return {
            "title": self._title(title),
            "meta": self._meta(raw.get("time") or raw.get("timestamp"), raw.get("wcs") or active_wcs),
            "result": raw.get("result") or raw.get("summary") or "Result stored",
            "highlight": raw.get("highlight") or raw.get("detail") or "Review result",
            "detail": raw.get("command") or raw.get("type") or "History entry",
            "kind": raw.get("kind", "touch"),
        }

    def _surface_entry(self, result):
        summary = result.get("summary") or {}
        coord = str(result.get("coord", "--")).upper()
        pattern = str(result.get("pattern", "--")).upper()
        high = summary.get("high_point", "--")
        low = summary.get("low_point", "--")
        return {
            "title": "Surface Measure",
            "meta": self._meta(result.get("time") or result.get("timestamp"), coord),
            "result": "Range %s mm" % self._fmt(summary.get("range"), 3),
            "highlight": "High %s · Low %s" % (high, low),
            "detail": pattern.replace("_", " "),
            "kind": "surface",
        }

    def _touch_entry(self, status, result, active_wcs):
        direction = result.get("direction") or status.get("last_command") or "Touch Probe"
        position = result.get("position")
        samples = result.get("samples") or []
        return {
            "title": self._touch_title(status.get("last_command"), direction),
            "meta": self._meta(result.get("time") or result.get("timestamp"), active_wcs),
            "result": self._position_result(position),
            "highlight": "Direction %s" % direction,
            "detail": "%d sample%s" % (len(samples), "" if len(samples) == 1 else "s") if samples else "Latest touch result",
            "kind": "touch",
        }

    def _setter_entry(self, result, active_wcs):
        if "delta" in result:
            title = "Apply Bit Z"
            value = "Delta Z %+.3f" % float(result.get("delta", 0))
            highlight = "Offset %s" % self._fmt(result.get("new_wcs_z_offset"), 3)
        else:
            title = "Tool Setter"
            value = "Contact Z %s" % self._fmt(result.get("contact_z"), 3)
            highlight = "Setter touched"
        samples = result.get("samples") or []
        detail = "Setter %s" % self._fmt(result.get("setter_work_z"), 3) if result.get("setter_work_z") is not None else "Latest setter result"
        if samples:
            detail += " · %d sample%s" % (len(samples), "" if len(samples) == 1 else "s")
        return {
            "title": title,
            "meta": self._meta(result.get("time") or result.get("timestamp"), active_wcs),
            "result": value,
            "highlight": highlight,
            "detail": detail,
            "kind": "setter",
        }

    def _calibration_entry(self, calibration):
        active_wcs = calibration.get("active_wcs", "--")
        return {
            "title": "Setter Calibration",
            "meta": self._meta(calibration.get("time") or calibration.get("timestamp"), active_wcs),
            "result": "Setter Z %s" % self._fmt(calibration.get("setter_work_z"), 3),
            "highlight": "Reference stored",
            "detail": "Contact %s" % self._fmt(calibration.get("reference_contact_z"), 3),
            "kind": "setter",
        }

    def _history_card(self, entry):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        card.set_hexpand(True)
        card.set_size_request(-1, 148)
        card.get_style_context().add_class("cnc-history-card")
        card.get_style_context().add_class(f"cnc-history-{entry['kind']}")

        accent = Gtk.Box()
        accent.set_size_request(-1, 4)
        accent.get_style_context().add_class("cnc-history-accent")
        accent.get_style_context().add_class(f"cnc-history-accent-{entry['kind']}")
        card.pack_start(accent, False, False, 0)

        title = self._label(entry["title"], "cnc-history-title")
        meta = self._label(entry["meta"], "cnc-history-meta")
        result = self._label(entry["result"], "cnc-history-result")
        highlight = self._label(entry["highlight"], "cnc-history-highlight")
        detail = self._label(entry["detail"], "cnc-history-detail")

        for label in (title, meta, result, highlight, detail):
            card.pack_start(label, False, False, 0)
        return card

    @staticmethod
    def _label(text, style_class):
        label = Gtk.Label(label=str(text), xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.get_style_context().add_class(style_class)
        return label

    @staticmethod
    def _meta(timestamp, mode):
        when = str(timestamp).strip() if timestamp else "Latest"
        return "%s · %s" % (when, str(mode).upper())

    @staticmethod
    def _title(value):
        return str(value).replace("_", " ").title()

    def _touch_title(self, command, direction):
        command = str(command or "").upper()
        if command.startswith("FIND_EDGE"):
            return command.replace("FIND_EDGE_", "Edge ").replace("_", " ")
        if command.startswith("FIND_SURFACE") or direction == "Z-":
            return "Stock Z0"
        if command.startswith("FIND_CENTER"):
            return command.replace("FIND_", "").replace("_", " ").title()
        if command.startswith("PROBE_BORE"):
            return "Bore XY"
        return self._title(command or direction or "Touch Probe")

    def _position_result(self, position):
        if not position:
            return "Position --"
        return "X%s Y%s Z%s" % (
            self._fmt_index(position, 0),
            self._fmt_index(position, 1),
            self._fmt_index(position, 2),
        )

    @staticmethod
    def _fmt(value, decimals):
        try:
            return f"{float(value):.{decimals}f}"
        except (TypeError, ValueError):
            return "--"

    def _fmt_index(self, values, index):
        try:
            return self._fmt(values[index], 3)
        except (TypeError, IndexError):
            return "--"

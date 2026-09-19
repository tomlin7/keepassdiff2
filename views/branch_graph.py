from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
import flet as ft
import flet.canvas as cv


class BranchGraph(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        diff_results: list,
        resolved_uuids: set,
        resolutions: dict,
        on_select_diff: Callable[[any], None],
        resolution_timestamps: Optional[dict] = None,
    ):
        super().__init__()
        self.page_ref = page
        self.diff_results = diff_results
        self.resolved_uuids = resolved_uuids
        self.resolutions = resolutions
        self.resolution_timestamps = resolution_timestamps or {}
        self.on_select_diff = on_select_diff

        self.is_collapsed: bool = False
        self.is_tall: bool = False
        self.sort_mode: str = "chrono"  # "chrono" (mtime latest first) or "status"
        self.fullscreen_dlg: Optional[ft.AlertDialog] = None
        self.filter_text: str = ""

        self.padding = ft.Padding.symmetric(horizontal=10, vertical=6)
        self.border_radius = 8
        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        self.border = ft.Border.all(1, ft.Colors.GREY_800)

        self.content = self._build_ui()

    def update_data(
        self,
        diff_results: list,
        resolved_uuids: set,
        resolutions: dict,
        resolution_timestamps: Optional[dict] = None,
    ):
        self.diff_results = diff_results
        self.resolved_uuids = resolved_uuids
        self.resolutions = resolutions
        if resolution_timestamps:
            self.resolution_timestamps.update(resolution_timestamps)
        self.content = self._build_ui()
        try:
            self.update()
        except RuntimeError:
            pass

    def _toggle_collapse(self, e):
        self.is_collapsed = not self.is_collapsed
        self.content = self._build_ui()
        try:
            self.update()
        except RuntimeError:
            pass

    def _toggle_tall(self, e):
        self.is_tall = not self.is_tall
        self.content = self._build_ui()
        try:
            self.update()
        except RuntimeError:
            pass

    def _toggle_sort(self, e):
        self.sort_mode = "status" if self.sort_mode == "chrono" else "chrono"
        self.content = self._build_ui()
        try:
            self.update()
        except RuntimeError:
            pass

    def _handle_row_click(self, diff, close_dialog: bool = False):
        if close_dialog and self.fullscreen_dlg:
            self.close_fullscreen(None)
        self.on_select_diff(diff)

    def _extract_timestamp_info(self, diff) -> dict:
        ea = getattr(diff, "entry_a", None)
        eb = getattr(diff, "entry_b", None)

        mtime_a = getattr(ea, "mtime", None) if ea else None
        mtime_b = getattr(eb, "mtime", None) if eb else None
        ctime_a = getattr(ea, "ctime", None) if ea else None
        ctime_b = getattr(eb, "ctime", None) if eb else None
        atime_a = getattr(ea, "atime", None) if ea else None
        atime_b = getattr(eb, "atime", None) if eb else None

        # Effective event timestamp for chronological sorting
        timestamps = [t for t in (mtime_b, mtime_a, ctime_b, ctime_a) if t is not None]
        default_min = datetime.min.replace(tzinfo=timezone.utc)
        event_time = max(timestamps) if timestamps else default_min

        # Ahead time delta calculation
        delta_str = ""
        delta_badge_color = "#f59e0b"  # amber
        if mtime_a and mtime_b:
            diff_sec = (mtime_b - mtime_a).total_seconds()
            abs_sec = abs(int(diff_sec))
            if abs_sec < 60:
                d_time = f"{abs_sec}s"
            elif abs_sec < 3600:
                d_time = f"{abs_sec // 60}m"
            elif abs_sec < 86400:
                d_time = f"{abs_sec // 3600}h"
            else:
                d_time = f"{abs_sec // 86400}d"

            if diff_sec > 0:
                delta_str = f"B newer (+{d_time})"
                delta_badge_color = "#f59e0b"
            elif diff_sec < 0:
                delta_str = f"A newer (+{d_time})"
                delta_badge_color = "#3b82f6"
            else:
                delta_str = "Same mtime"
                delta_badge_color = "#f59e0b"
        elif mtime_b:
            delta_str = "Only in B"
            delta_badge_color = "#14b8a6"
        elif mtime_a:
            delta_str = "Only in A"
            delta_badge_color = "#3b82f6"

        atime = atime_b or atime_a
        atime_str = atime.strftime("%H:%M:%S") if atime else "—"
        time_display = (
            event_time.strftime("%b %d, %H:%M:%S")
            if event_time != default_min
            else "Unknown"
        )

        tooltip = (
            f"Entry: {diff.title}\n"
            f"Base (A) mtime: {mtime_a or '—'}\n"
            f"Compare (B) mtime: {mtime_b or '—'}\n"
            f"Base ctime: {ctime_a or '—'}\n"
            f"Compare ctime: {ctime_b or '—'}\n"
            f"Last Accessed (atime): {atime_str}\n"
            f"Delta: {delta_str or '—'}"
        )

        return {
            "event_time": event_time,
            "time_display": time_display,
            "delta_str": delta_str,
            "delta_badge_color": delta_badge_color,
            "atime_str": atime_str,
            "mtime_a": mtime_a,
            "mtime_b": mtime_b,
            "ctime_a": ctime_a,
            "ctime_b": ctime_b,
            "tooltip": tooltip,
        }

    def _get_sorted_diffs(self, diff_list: list) -> list:
        if self.sort_mode == "chrono":
            # Sort by event_time descending (most recent change at top)
            return sorted(
                diff_list,
                key=lambda d: self._extract_timestamp_info(d)["event_time"],
                reverse=True,
            )
        else:
            # Sort: Unresolved first, then by state, then title
            def sort_key(d):
                is_res = 1 if d.uuid in self.resolved_uuids else 0
                state_prio = {"MODIFIED": 0, "ONLY_IN_B": 1, "ONLY_IN_A": 2}.get(
                    d.state, 3
                )
                return (is_res, state_prio, d.title or "")

            return sorted(diff_list, key=sort_key)

    def _build_ui(self) -> ft.Control:
        total_diffs = len(self.diff_results)
        resolved_count = len(
            [d for d in self.diff_results if d.uuid in self.resolved_uuids]
        )

        collapse_icon = (
            ft.Icons.KEYBOARD_ARROW_RIGHT
            if self.is_collapsed
            else ft.Icons.KEYBOARD_ARROW_DOWN
        )

        header_left = ft.Row(
            [
                ft.IconButton(
                    icon=collapse_icon,
                    icon_size=18,
                    tooltip="Collapse / Expand Graph",
                    on_click=self._toggle_collapse,
                    visual_density=ft.VisualDensity.COMPACT,
                ),
                ft.Icon(ft.Icons.AUTO_GRAPH, color=ft.Colors.INDIGO_300, size=18),
                ft.Text("Commit & Merge Graph", weight=ft.FontWeight.BOLD, size=14),
                ft.Container(
                    content=ft.Text(
                        f"{total_diffs} changes • {resolved_count} resolved",
                        size=11,
                        color=ft.Colors.GREY_300,
                    ),
                    bgcolor=ft.Colors.WHITE10,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    border_radius=10,
                ),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        legend = ft.Row(
            [
                self._legend_chip("Base (A)", "#3b82f6"),
                self._legend_chip("Compare (B)", "#14b8a6"),
                self._legend_chip("Modified", "#f59e0b"),
                self._legend_chip("Merged", "#10b981", is_ring=True),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        sort_btn = ft.TextButton(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.SCHEDULE
                        if self.sort_mode == "chrono"
                        else ft.Icons.SORT_BY_ALPHA,
                        size=14,
                        color=ft.Colors.INDIGO_200,
                    ),
                    ft.Text(
                        "Chrono (mtime)"
                        if self.sort_mode == "chrono"
                        else "Status",
                        size=11,
                        color=ft.Colors.INDIGO_200,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
            tooltip="Toggle sorting: Chronological by mtime vs Status",
            on_click=self._toggle_sort,
            style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=6, vertical=2)),
        )

        header_actions = ft.Row(
            [
                sort_btn,
                legend,
                ft.IconButton(
                    icon=(
                        ft.Icons.UNFOLD_MORE
                        if not self.is_tall
                        else ft.Icons.UNFOLD_LESS
                    ),
                    icon_size=18,
                    tooltip="Toggle Height (Compact / Tall)",
                    on_click=self._toggle_tall,
                    visible=not self.is_collapsed,
                    visual_density=ft.VisualDensity.COMPACT,
                ),
                ft.IconButton(
                    icon=ft.Icons.FULLSCREEN,
                    icon_size=18,
                    tooltip="Expand to Fullscreen",
                    on_click=self.open_fullscreen,
                    visual_density=ft.VisualDensity.COMPACT,
                ),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        header = ft.Row(
            [header_left, header_actions],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if self.is_collapsed:
            return header

        if not self.diff_results:
            body = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=20),
                        ft.Text(
                            "Branches are fully merged and in sync — no divergence.",
                            size=13,
                            color=ft.Colors.GREEN,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=12,
            )
            return ft.Column([header, body], spacing=4)

        list_height = 360 if self.is_tall else 220
        sorted_diffs = self._get_sorted_diffs(self.diff_results)
        body = self._build_graph_body(
            sorted_diffs, height=list_height, close_dialog=False
        )

        return ft.Column(
            [
                header,
                ft.Divider(height=1, color=ft.Colors.GREY_800),
                body,
            ],
            spacing=4,
        )

    def _legend_chip(self, label: str, color_hex: str, is_ring: bool = False) -> ft.Control:
        if is_ring:
            marker = ft.Container(
                width=10,
                height=10,
                border_radius=5,
                border=ft.Border.all(2, color_hex),
                alignment=ft.Alignment(0, 0),
                content=ft.Container(
                    width=4, height=4, border_radius=2, bgcolor=color_hex
                ),
            )
        else:
            marker = ft.Container(width=8, height=8, border_radius=4, bgcolor=color_hex)

        return ft.Row(
            [
                marker,
                ft.Text(label, size=11, color=ft.Colors.GREY_300),
            ],
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _generate_track_canvas(self, diff_list: list, H: int, total_h: int) -> ft.Control:
        N = len(diff_list)
        x0 = 18  # Lane 0: Base DB A (Trunk)
        x1 = 38  # Lane 1: Compare DB B (Branch)

        p_trunk = ft.Paint(
            color=ft.Colors.BLUE_400,
            stroke_width=2.5,
            stroke_cap=ft.StrokeCap.ROUND,
            style=ft.PaintingStyle.STROKE,
        )
        p_branch = ft.Paint(
            color=ft.Colors.TEAL_400,
            stroke_width=2,
            stroke_cap=ft.StrokeCap.ROUND,
            style=ft.PaintingStyle.STROKE,
        )
        p_merge = ft.Paint(
            color=ft.Colors.GREEN_400,
            stroke_width=2,
            stroke_cap=ft.StrokeCap.ROUND,
            style=ft.PaintingStyle.STROKE,
        )
        p_green_ring = ft.Paint(
            color=ft.Colors.GREEN_400,
            stroke_width=2,
            style=ft.PaintingStyle.STROKE,
        )
        p_dot_amber = ft.Paint(color=ft.Colors.AMBER_400, style=ft.PaintingStyle.FILL)
        p_dot_teal = ft.Paint(color=ft.Colors.TEAL_400, style=ft.PaintingStyle.FILL)
        p_dot_blue = ft.Paint(color=ft.Colors.BLUE_400, style=ft.PaintingStyle.FILL)
        p_dot_green = ft.Paint(color=ft.Colors.GREEN_400, style=ft.PaintingStyle.FILL)
        p_dot_bg = ft.Paint(color="#18181b", style=ft.PaintingStyle.FILL)

        shapes = []

        has_branch = any(
            d.state in ("MODIFIED", "ONLY_IN_B") for d in diff_list
        )
        branch_indices = [
            i
            for i, d in enumerate(diff_list)
            if d.state in ("MODIFIED", "ONLY_IN_B")
        ]

        # 1. Base Trunk (Lane 0) - Continuous vertical line
        if N > 1:
            shapes.append(cv.Line(x0, 16, x0, total_h - 16, paint=p_trunk))
        else:
            shapes.append(cv.Line(x0, 8, x0, 24, paint=p_trunk))

        # 2. Compare Branch (Lane 1) - Continuous vertical line branching off at top
        if has_branch:
            first_branch_i = branch_indices[0]
            last_branch_i = branch_indices[-1]
            y_fork_start = max(8, first_branch_i * H)
            y_branch_end = last_branch_i * H + 16

            shapes.append(
                cv.Path(
                    elements=[
                        cv.Path.MoveTo(x0, y_fork_start),
                        cv.Path.CubicTo(
                            x0 + 8,
                            y_fork_start + 4,
                            x1,
                            y_fork_start + 10,
                            x1,
                            y_fork_start + 16,
                        ),
                        cv.Path.LineTo(x1, y_branch_end),
                    ],
                    paint=p_branch,
                )
            )

        # 3. Commit Nodes & Merges per row
        for i, diff in enumerate(diff_list):
            cy = i * H + 16
            is_resolved = diff.uuid in self.resolved_uuids

            if is_resolved:
                # Merge arc from Lane 1 into Lane 0
                shapes.append(
                    cv.Path(
                        elements=[
                            cv.Path.MoveTo(x1, max(8, cy - 14)),
                            cv.Path.CubicTo(x1 - 6, cy - 4, x0 + 8, cy, x0, cy),
                        ],
                        paint=p_merge,
                    )
                )
                shapes.append(cv.Circle(x0, cy, 6, paint=p_dot_bg))
                shapes.append(cv.Circle(x0, cy, 6, paint=p_green_ring))
                shapes.append(cv.Circle(x0, cy, 2.5, paint=p_dot_green))
            elif diff.state == "MODIFIED":
                # Node on Lane 1 for Compare version
                shapes.append(cv.Circle(x1, cy, 5.5, paint=p_dot_bg))
                shapes.append(cv.Circle(x1, cy, 4, paint=p_dot_amber))
            elif diff.state == "ONLY_IN_B":
                # Node on Lane 1 for Compare addition
                shapes.append(cv.Circle(x1, cy, 5.5, paint=p_dot_bg))
                shapes.append(cv.Circle(x1, cy, 4, paint=p_dot_teal))
            else:  # ONLY_IN_A
                # Node on Lane 0 for Base-only
                shapes.append(cv.Circle(x0, cy, 5.5, paint=p_dot_bg))
                shapes.append(cv.Circle(x0, cy, 4, paint=p_dot_blue))

        return cv.Canvas(shapes=shapes, width=50, height=total_h)

    def _build_commit_row(
        self, diff: any, H: int, close_dialog: bool = False
    ) -> ft.Control:
        is_resolved = diff.uuid in self.resolved_uuids
        title = diff.title or "Untitled"
        group_path = getattr(diff, "group_path", None) or "Root"
        ts_info = self._extract_timestamp_info(diff)

        # 1. Commit text
        if is_resolved:
            action = self.resolutions.get(diff.uuid, "Resolved")
            badge = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK, color="#34d399", size=11),
                        ft.Text(
                            f"Merged ({action})",
                            size=10,
                            weight=ft.FontWeight.W_600,
                            color="#34d399",
                        ),
                    ],
                    spacing=3,
                    tight=True,
                ),
                bgcolor="#064e3b",
                border_radius=4,
                padding=ft.Padding.symmetric(horizontal=6, vertical=1.5),
                border=ft.Border.all(1, "#059669"),
            )
            commit_text = f"Merge '{title}' into Base"
        elif diff.state == "MODIFIED":
            fields_label = ", ".join(diff.diffs[:2])
            delta_label = ts_info["delta_str"]
            badge = ft.Container(
                content=ft.Text(
                    f"{delta_label}: {fields_label}",
                    size=10,
                    weight=ft.FontWeight.W_600,
                    color="#fbbf24",
                ),
                bgcolor="#3d2003",
                border_radius=4,
                padding=ft.Padding.symmetric(horizontal=6, vertical=1.5),
                border=ft.Border.all(1, "#92400e"),
            )
            commit_text = f"Update '{title}'"
        elif diff.state == "ONLY_IN_B":
            badge = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.ARROW_DOWNWARD, color="#2dd4bf", size=11),
                        ft.Text(
                            f"Incoming (B) • {ts_info['delta_str']}",
                            size=10,
                            weight=ft.FontWeight.W_600,
                            color="#2dd4bf",
                        ),
                    ],
                    spacing=3,
                    tight=True,
                ),
                bgcolor="#042f2e",
                border_radius=4,
                padding=ft.Padding.symmetric(horizontal=6, vertical=1.5),
                border=ft.Border.all(1, "#0d9488"),
            )
            commit_text = f"Add '{title}' from Compare"
        else:  # ONLY_IN_A
            badge = ft.Container(
                content=ft.Text(
                    f"Base Only (A) • {ts_info['delta_str']}",
                    size=10,
                    weight=ft.FontWeight.W_600,
                    color="#93c5fd",
                ),
                bgcolor="#0f172a",
                border_radius=4,
                padding=ft.Padding.symmetric(horizontal=6, vertical=1.5),
                border=ft.Border.all(1, "#2563eb"),
            )
            commit_text = f"Retain '{title}' in Base"

        diff_count_info = (
            f"{len(diff.diffs)} field(s)"
            if getattr(diff, "diffs", None)
            else ""
        )

        timestamp_widget = ft.Container(
            content=ft.Text(
                ts_info["time_display"],
                size=11,
                color="#94a3b8",
                font_family="monospace",
            ),
            width=135,
        )

        return ft.Container(
            content=ft.Row(
                [
                    timestamp_widget,
                    ft.Text(
                        commit_text,
                        weight=ft.FontWeight.W_600,
                        size=12,
                        color="#f1f5f9" if not is_resolved else "#94a3b8",
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                    ),
                    badge,
                    ft.Text(
                        f"• {group_path} {diff_count_info} • atime: {ts_info['atime_str']}".strip(),
                        size=11,
                        color="#64748b",
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=H,
            border_radius=4,
            padding=ft.Padding.symmetric(horizontal=6),
            ink=True,
            on_click=lambda _, d=diff: self._handle_row_click(d, close_dialog),
            tooltip=ts_info["tooltip"],
        )

    def _build_graph_body(
        self,
        diff_list: list,
        height: Optional[int] = None,
        close_dialog: bool = False,
    ) -> ft.Control:
        H = 32
        N = len(diff_list)
        total_h = N * H

        track_canvas = self._generate_track_canvas(diff_list, H, total_h)

        row_controls = [
            self._build_commit_row(diff, H, close_dialog)
            for diff in diff_list
        ]

        graph_row = ft.Row(
            [
                track_canvas,
                ft.Column(
                    row_controls,
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        scroll_col = ft.Column(
            [graph_row],
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            expand=True if height is None else False,
        )

        if height is not None:
            return ft.Container(content=scroll_col, height=height)
        return ft.Container(content=scroll_col, expand=True)

    # 3. Fullscreen Expansion View
    def open_fullscreen(self, e):
        dlg_content = self._build_fullscreen_content()
        self.fullscreen_dlg = ft.AlertDialog(
            modal=True,
            content=dlg_content,
            actions_padding=0,
            content_padding=15,
        )

        if hasattr(self.page_ref, "show_dialog"):
            self.page_ref.show_dialog(self.fullscreen_dlg)
        else:
            self.page_ref.dialog = self.fullscreen_dlg
            self.fullscreen_dlg.open = True
            self.page_ref.update()

    def close_fullscreen(self, e):
        if hasattr(self.page_ref, "pop_dialog"):
            self.page_ref.pop_dialog()
        elif self.page_ref.dialog:
            self.page_ref.dialog.open = False
            self.page_ref.update()
        self.fullscreen_dlg = None

    def _build_fullscreen_content(self) -> ft.Control:
        search_field = ft.TextField(
            hint_text="Search changes by title, group, or status...",
            prefix_icon=ft.Icons.SEARCH,
            height=38,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            border_radius=6,
            expand=True,
            on_change=self._on_search_change,
        )

        header = ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.AUTO_GRAPH, color=ft.Colors.INDIGO_300, size=22
                        ),
                        ft.Text(
                            "Commit & Merge Graph (Fullscreen View)",
                            weight=ft.FontWeight.BOLD,
                            size=16,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                ft.Row(
                    [
                        self._legend_chip("Base (A)", "#3b82f6"),
                        self._legend_chip("Compare (B)", "#14b8a6"),
                        self._legend_chip("Modified", "#f59e0b"),
                        self._legend_chip(
                            "Merged", "#10b981", is_ring=True
                        ),
                        ft.IconButton(
                            icon=ft.Icons.FULLSCREEN_EXIT,
                            tooltip="Exit Fullscreen",
                            on_click=self.close_fullscreen,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.fullscreen_container = ft.Container(expand=True)
        self._populate_fullscreen_list()

        return ft.Container(
            content=ft.Column(
                [
                    header,
                    ft.Divider(height=1, color=ft.Colors.GREY_800),
                    ft.Row([search_field]),
                    self.fullscreen_container,
                ],
                spacing=8,
                expand=True,
            ),
            width=960,
            height=620,
            padding=10,
        )

    def _on_search_change(self, e):
        self.filter_text = e.control.value.lower()
        self._populate_fullscreen_list()
        try:
            self.fullscreen_container.update()
        except RuntimeError:
            pass

    def _populate_fullscreen_list(self):
        filtered = []
        for diff in self.diff_results:
            title = (diff.title or "").lower()
            group = (getattr(diff, "group_path", None) or "").lower()
            if (
                not self.filter_text
                or self.filter_text in title
                or self.filter_text in group
            ):
                filtered.append(diff)

        if not filtered:
            self.fullscreen_container.content = ft.Container(
                content=ft.Text("No matching changes found.", color=ft.Colors.GREY_400),
                alignment=ft.Alignment(0, 0),
                padding=20,
            )
        else:
            sorted_filtered = self._get_sorted_diffs(filtered)
            self.fullscreen_container.content = self._build_graph_body(
                sorted_filtered, height=None, close_dialog=True
            )

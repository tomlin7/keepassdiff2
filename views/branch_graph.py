from typing import Callable, List, Optional
import urllib.parse
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
    ):
        super().__init__()
        self.page_ref = page
        self.diff_results = diff_results
        self.resolved_uuids = resolved_uuids
        self.resolutions = resolutions
        self.on_select_diff = on_select_diff

        self.is_collapsed: bool = False
        self.is_tall: bool = False
        self.fullscreen_dlg: Optional[ft.AlertDialog] = None
        self.filter_text: str = ""

        self.padding = ft.Padding.symmetric(horizontal=10, vertical=6)
        self.border_radius = 8
        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        self.border = ft.Border.all(1, ft.Colors.GREY_800)

        self.content = self._build_ui()

    def update_data(self, diff_results: list, resolved_uuids: set, resolutions: dict):
        self.diff_results = diff_results
        self.resolved_uuids = resolved_uuids
        self.resolutions = resolutions
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

    def _handle_row_click(self, diff, close_dialog: bool = False):
        if close_dialog and self.fullscreen_dlg:
            self.close_fullscreen(None)
        self.on_select_diff(diff)

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
                ft.Text("Graph", weight=ft.FontWeight.BOLD, size=14),
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
                self._legend_chip("Resolved", "#10b981", is_ring=True),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        header_actions = ft.Row(
            [
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

        list_height = 360 if self.is_tall else 210
        body = self._build_graph_body(
            self.diff_results, height=list_height, close_dialog=False
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
        x0 = 20
        x1 = 46

        p_trunk = ft.Paint(
            color=ft.Colors.BLUE_400,
            stroke_width=2.5,
            stroke_cap=ft.StrokeCap.ROUND,
            style=ft.PaintingStyle.STROKE,
        )
        p_branch = ft.Paint(
            color=ft.Colors.AMBER_400,
            stroke_width=2,
            stroke_cap=ft.StrokeCap.ROUND,
            style=ft.PaintingStyle.STROKE,
        )
        p_teal = ft.Paint(
            color=ft.Colors.TEAL_400,
            stroke_width=2,
            stroke_cap=ft.StrokeCap.ROUND,
            style=ft.PaintingStyle.STROKE,
        )
        p_green_stroke = ft.Paint(
            color=ft.Colors.GREEN_400,
            stroke_width=2,
            stroke_cap=ft.StrokeCap.ROUND,
            style=ft.PaintingStyle.STROKE,
        )
        p_green_ring = ft.Paint(
            color=ft.Colors.GREEN_400,
            stroke_width=2.5,
            style=ft.PaintingStyle.STROKE,
        )
        p_dot_amber = ft.Paint(color=ft.Colors.AMBER_400, style=ft.PaintingStyle.FILL)
        p_dot_teal = ft.Paint(color=ft.Colors.TEAL_400, style=ft.PaintingStyle.FILL)
        p_dot_blue = ft.Paint(color=ft.Colors.BLUE_400, style=ft.PaintingStyle.FILL)
        p_dot_green = ft.Paint(color=ft.Colors.GREEN_400, style=ft.PaintingStyle.FILL)
        p_dot_bg = ft.Paint(color="#18181b", style=ft.PaintingStyle.FILL)

        shapes = []

        # 1. Main Continuous Base Trunk Line
        if N > 1:
            shapes.append(cv.Line(x0, 19, x0, total_h - 19, paint=p_trunk))
        else:
            shapes.append(cv.Line(x0, 10, x0, 28, paint=p_trunk))

        # 2. Branch Curves and Commit Nodes
        for i, diff in enumerate(diff_list):
            cy = i * H + 19
            is_resolved = diff.uuid in self.resolved_uuids

            if is_resolved:
                # Merge arc from branch lane into trunk
                y_from = max(0, cy - 20)
                shapes.append(
                    cv.Path(
                        elements=[
                            cv.Path.MoveTo(x1, y_from),
                            cv.Path.CubicTo(x1, cy - 8, x0 + 10, cy, x0, cy),
                        ],
                        paint=p_green_stroke,
                    )
                )
                # Double-ring merge commit at (x0, cy)
                shapes.append(cv.Circle(x0, cy, 6.5, paint=p_dot_bg))
                shapes.append(cv.Circle(x0, cy, 6.5, paint=p_green_ring))
                shapes.append(cv.Circle(x0, cy, 3.0, paint=p_dot_green))
            elif diff.state == "MODIFIED":
                # Smooth bezier fork curve from trunk to branch lane
                y_fork = max(0, cy - 20)
                shapes.append(
                    cv.Path(
                        elements=[
                            cv.Path.MoveTo(x0, y_fork),
                            cv.Path.CubicTo(x0, cy - 8, x1 - 10, cy, x1, cy),
                        ],
                        paint=p_branch,
                    )
                )
                shapes.append(cv.Circle(x1, cy, 5.5, paint=p_dot_bg))
                shapes.append(cv.Circle(x1, cy, 4.5, paint=p_dot_amber))
            elif diff.state == "ONLY_IN_B":
                # Incoming branch line down to (x1, cy)
                y_from = max(0, cy - 20)
                shapes.append(cv.Line(x1, y_from, x1, cy, paint=p_teal))
                shapes.append(cv.Circle(x1, cy, 5.5, paint=p_dot_bg))
                shapes.append(cv.Circle(x1, cy, 4.5, paint=p_dot_teal))
            else:  # ONLY_IN_A
                shapes.append(cv.Circle(x0, cy, 5.5, paint=p_dot_bg))
                shapes.append(cv.Circle(x0, cy, 4.5, paint=p_dot_blue))

        return cv.Canvas(shapes=shapes, width=66, height=total_h)

    def _build_commit_row(self, diff: any, H: int, close_dialog: bool = False) -> ft.Control:
        is_resolved = diff.uuid in self.resolved_uuids
        title = diff.title or "Untitled"
        group_path = getattr(diff, "group_path", None) or "Root"

        # GitLens-style sleek badge and text
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
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, "#059669"),
            )
            commit_text = f"Merge '{title}' into Base"
        elif diff.state == "MODIFIED":
            ahead_label = (
                "B newer"
                if diff.ahead == "B"
                else ("A newer" if diff.ahead == "A" else "Diverged")
            )
            fields_label = ", ".join(diff.diffs[:2])
            badge = ft.Container(
                content=ft.Text(
                    f"{ahead_label}: {fields_label}",
                    size=10,
                    weight=ft.FontWeight.W_600,
                    color="#fbbf24",
                ),
                bgcolor="#451a03",
                border_radius=4,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, "#b45309"),
            )
            commit_text = f"Update '{title}'"
        elif diff.state == "ONLY_IN_B":
            badge = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.ARROW_DOWNWARD, color="#2dd4bf", size=11),
                        ft.Text(
                            "Incoming (B)",
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
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, "#0f766e"),
            )
            commit_text = f"Add '{title}' from Compare"
        else:  # ONLY_IN_A
            badge = ft.Container(
                content=ft.Text(
                    "Base Only (A)",
                    size=10,
                    weight=ft.FontWeight.W_600,
                    color="#93c5fd",
                ),
                bgcolor="#172554",
                border_radius=4,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, "#1d4ed8"),
            )
            commit_text = f"Retain '{title}' in Base"

        diff_count_info = f"{len(diff.diffs)} field(s)" if getattr(diff, "diffs", None) else ""

        return ft.Container(
            content=ft.Row(
                [
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
                        f"• {group_path} {diff_count_info}".strip(),
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
            tooltip=f"Click to inspect '{title}' ({diff.state})",
        )

    def _build_graph_body(self, diff_list: list, height: Optional[int] = None, close_dialog: bool = False) -> ft.Control:
        H = 38
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
            hint_text="Search changes by title or group...",
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
                            "Commit & Branch Graph (Fullscreen View)",
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
                            "Resolved", "#10b981", is_ring=True
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
            width=920,
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
            self.fullscreen_container.content = self._build_graph_body(
                filtered, height=None, close_dialog=True
            )

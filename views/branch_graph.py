from typing import Callable, List, Optional
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

        # 1. Header Row
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

        # Legend Chips
        legend = ft.Row(
            [
                self._legend_chip("Base (A)", ft.Colors.BLUE_400),
                self._legend_chip("Compare (B)", ft.Colors.TEAL_400),
                self._legend_chip("Modified", ft.Colors.AMBER_400),
                self._legend_chip("Resolved", ft.Colors.GREEN_400, is_ring=True),
            ],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Header Action Buttons
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

        # 2. Commit Rows List
        rows = []
        for i, diff in enumerate(self.diff_results):
            rows.append(
                self._build_commit_row(
                    diff,
                    is_first=(i == 0),
                    is_last=(i == len(self.diff_results) - 1),
                )
            )

        list_height = 360 if self.is_tall else 210
        body = ft.Container(
            content=ft.ListView(
                controls=rows,
                spacing=2,
                padding=ft.Padding.only(top=4, bottom=4),
            ),
            height=list_height,
        )

        return ft.Column(
            [
                header,
                ft.Divider(height=1, color=ft.Colors.GREY_800),
                body,
            ],
            spacing=4,
        )

    def _legend_chip(self, label: str, color: str, is_ring: bool = False) -> ft.Control:
        if is_ring:
            marker = ft.Container(
                width=10,
                height=10,
                border_radius=5,
                border=ft.Border.all(2, color),
                alignment=ft.Alignment(0, 0),
                content=ft.Container(
                    width=4, height=4, border_radius=2, bgcolor=color
                ),
            )
        else:
            marker = ft.Container(width=8, height=8, border_radius=4, bgcolor=color)

        return ft.Row(
            [
                marker,
                ft.Text(label, size=11, color=ft.Colors.GREY_300),
            ],
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_commit_row(
        self,
        diff: any,
        is_first: bool,
        is_last: bool,
        close_dialog: bool = False,
    ) -> ft.Control:
        is_resolved = diff.uuid in self.resolved_uuids
        title = diff.title or "Untitled"
        group_path = getattr(diff, "group_path", None) or "Root"

        # GitLens Canvas Drawing (Left Track)
        canvas = self._draw_graph_track(diff, is_resolved, is_first, is_last)

        # Pill Tag / Badge (e.g. dev, incoming, modified)
        if is_resolved:
            action = self.resolutions.get(diff.uuid, "Resolved")
            badge = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=12
                        ),
                        ft.Text(
                            f"Resolved ({action})",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREEN_300,
                        ),
                    ],
                    spacing=3,
                    tight=True,
                ),
                bgcolor=ft.Colors.GREEN_900,
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, ft.Colors.GREEN_700),
            )
            commit_text = f"Merge '{title}' into Base (A)"
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
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.AMBER_300,
                ),
                bgcolor=ft.Colors.AMBER_900,
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, ft.Colors.AMBER_700),
            )
            commit_text = f"Update '{title}'"
        elif diff.state == "ONLY_IN_B":
            badge = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CALL_RECEIVED, color=ft.Colors.TEAL_300, size=12
                        ),
                        ft.Text(
                            "Incoming (B)",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.TEAL_200,
                        ),
                    ],
                    spacing=3,
                    tight=True,
                ),
                bgcolor=ft.Colors.TEAL_900,
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, ft.Colors.TEAL_700),
            )
            commit_text = f"Add '{title}' from Compare (B)"
        else:  # ONLY_IN_A
            badge = ft.Container(
                content=ft.Text(
                    "Base Only (A)",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_200,
                ),
                bgcolor=ft.Colors.BLUE_900,
                border_radius=8,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, ft.Colors.BLUE_700),
            )
            commit_text = f"Retain '{title}' in Base (A)"

        # Text & Metadata
        info_row = ft.Row(
            [
                ft.Text(
                    commit_text,
                    weight=ft.FontWeight.BOLD,
                    size=12,
                    color=ft.Colors.WHITE if not is_resolved else ft.Colors.GREY_400,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                ),
                badge,
                ft.Text(
                    f"in {group_path}",
                    size=11,
                    color=ft.Colors.GREY_500,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=8,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=ft.Row(
                [
                    canvas,
                    info_row,
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=38,
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=4, vertical=1),
            ink=True,
            on_click=lambda _, d=diff: self._handle_row_click(d, close_dialog),
            tooltip=f"Click to inspect '{title}' ({diff.state})",
        )

    def _draw_graph_track(
        self,
        diff: any,
        is_resolved: bool,
        is_first: bool,
        is_last: bool,
    ) -> cv.Canvas:
        h = 38
        ym = 19
        x0 = 18  # Trunk (Base A)
        x1 = 44  # Branch (Compare B / Feature)

        p_trunk = ft.Paint(
            color=ft.Colors.BLUE_500,
            stroke_width=2,
            style=ft.PaintingStyle.STROKE,
        )
        p_branch_stroke = ft.Paint(
            color=ft.Colors.AMBER_400,
            stroke_width=2,
            style=ft.PaintingStyle.STROKE,
        )
        p_branch_fill = ft.Paint(
            color=ft.Colors.AMBER_400,
            style=ft.PaintingStyle.FILL,
        )
        p_teal_stroke = ft.Paint(
            color=ft.Colors.TEAL_400,
            stroke_width=2,
            style=ft.PaintingStyle.STROKE,
        )
        p_teal_fill = ft.Paint(
            color=ft.Colors.TEAL_400,
            style=ft.PaintingStyle.FILL,
        )
        p_blue_fill = ft.Paint(
            color=ft.Colors.BLUE_400,
            style=ft.PaintingStyle.FILL,
        )
        p_green_stroke = ft.Paint(
            color=ft.Colors.GREEN_400,
            stroke_width=2,
            style=ft.PaintingStyle.STROKE,
        )
        p_green_fill = ft.Paint(
            color=ft.Colors.GREEN_400,
            style=ft.PaintingStyle.FILL,
        )

        shapes = []

        # 1. Base Trunk Vertical Line (runs through Lane 0)
        y_start = ym if is_first else 0
        y_end = ym if is_last else h
        shapes.append(cv.Line(x0, y_start, x0, y_end, paint=p_trunk))

        # 2. Branch / Merge / Commit Node logic
        if is_resolved:
            # Curved merge line from Lane 1 into Lane 0
            shapes.append(
                cv.Path(
                    [
                        cv.Path.MoveTo(x1, 0),
                        cv.Path.CubicTo(x1, ym - 4, x0 + 10, ym, x0, ym),
                    ],
                    paint=p_green_stroke,
                )
            )
            # Double-ring merge node on Lane 0 (GitLens merge commit icon)
            shapes.append(cv.Circle(x0, ym, 6.5, paint=p_green_stroke))
            shapes.append(cv.Circle(x0, ym, 3.0, paint=p_green_fill))
        elif diff.state == "MODIFIED":
            # Smooth branch curve forking out from Lane 0 to Lane 1
            shapes.append(
                cv.Path(
                    [
                        cv.Path.MoveTo(x0, ym),
                        cv.Path.CubicTo(x0 + 12, ym, x1 - 12, ym, x1, ym),
                    ],
                    paint=p_branch_stroke,
                )
            )
            # Commit dot on Lane 1
            shapes.append(cv.Circle(x1, ym, 4.5, paint=p_branch_fill))
        elif diff.state == "ONLY_IN_B":
            # Incoming branch track on Lane 1
            shapes.append(cv.Line(x1, 0, x1, ym, paint=p_teal_stroke))
            # Commit dot on Lane 1
            shapes.append(cv.Circle(x1, ym, 4.5, paint=p_teal_fill))
        else:  # ONLY_IN_A
            # Commit dot directly on Lane 0
            shapes.append(cv.Circle(x0, ym, 4.5, paint=p_blue_fill))

        return cv.Canvas(shapes=shapes, width=65, height=h)

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
            height=40,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            border_radius=8,
            expand=True,
            on_change=self._on_search_change,
        )

        header = ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.AUTO_GRAPH, color=ft.Colors.INDIGO_300, size=24
                        ),
                        ft.Text(
                            "Commit & Branch Graph (Fullscreen View)",
                            weight=ft.FontWeight.BOLD,
                            size=18,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                ft.Row(
                    [
                        self._legend_chip("Base (A)", ft.Colors.BLUE_400),
                        self._legend_chip("Compare (B)", ft.Colors.TEAL_400),
                        self._legend_chip("Modified", ft.Colors.AMBER_400),
                        self._legend_chip(
                            "Resolved", ft.Colors.GREEN_400, is_ring=True
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

        # Filtered Rows
        self.fullscreen_list = ft.ListView(
            spacing=3,
            expand=True,
            padding=ft.Padding.symmetric(vertical=6),
        )
        self._populate_fullscreen_list()

        return ft.Container(
            content=ft.Column(
                [
                    header,
                    ft.Divider(height=1, color=ft.Colors.GREY_800),
                    ft.Row([search_field]),
                    self.fullscreen_list,
                ],
                spacing=10,
                expand=True,
            ),
            width=900,
            height=600,
            padding=10,
        )

    def _on_search_change(self, e):
        self.filter_text = e.control.value.lower()
        self._populate_fullscreen_list()
        try:
            self.fullscreen_list.update()
        except RuntimeError:
            pass

    def _populate_fullscreen_list(self):
        self.fullscreen_list.controls.clear()
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

        for i, diff in enumerate(filtered):
            self.fullscreen_list.controls.append(
                self._build_commit_row(
                    diff,
                    is_first=(i == 0),
                    is_last=(i == len(filtered) - 1),
                    close_dialog=True,
                )
            )

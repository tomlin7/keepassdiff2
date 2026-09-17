from typing import Callable, List, Optional
import flet as ft

class BranchGraph(ft.Container):
    def __init__(
        self,
        diff_results: list,
        resolved_uuids: set,
        resolutions: dict,
        on_select_diff: Callable[[any], None],
    ):
        super().__init__()
        self.diff_results = diff_results
        self.resolved_uuids = resolved_uuids
        self.resolutions = resolutions
        self.on_select_diff = on_select_diff
        self.padding = 10
        self.border_radius = 10
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

    def _build_ui(self) -> ft.Control:
        if not self.diff_results:
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=24),
                        ft.Text(
                            "Branches are fully merged and in sync — no divergence.",
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREEN,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=25,
            )

        # Legend header
        header = ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.AUTO_GRAPH, color=ft.Colors.INDIGO_300, size=20),
                        ft.Text(
                            "Horizontal Branch & Merge Graph",
                            weight=ft.FontWeight.BOLD,
                            size=15,
                        ),
                    ],
                    tight=True,
                ),
                ft.Row(
                    [
                        self._legend_chip("Base (Lane A)", ft.Colors.INDIGO_400),
                        self._legend_chip("Compare (Lane B)", ft.Colors.TEAL_400),
                        self._legend_chip("Diverged", ft.Colors.ORANGE_400),
                        self._legend_chip("Incoming (B→A)", ft.Colors.LIGHT_BLUE_400),
                        self._legend_chip("Resolved", ft.Colors.GREEN_400),
                    ],
                    spacing=6,
                    tight=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # Fixed Lane Labels on Left
        lane_labels = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.COMMIT, size=16, color=ft.Colors.INDIGO_300),
                                ft.Text(
                                    "Base (A)",
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    color=ft.Colors.INDIGO_300,
                                ),
                            ],
                            tight=True,
                        ),
                        height=54,
                        alignment=ft.Alignment(-1, 0),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.MERGE_TYPE, size=16, color=ft.Colors.GREY_400),
                                ft.Text(
                                    "Flow (B→A)",
                                    weight=ft.FontWeight.BOLD,
                                    size=11,
                                    color=ft.Colors.GREY_400,
                                ),
                            ],
                            tight=True,
                        ),
                        height=46,
                        alignment=ft.Alignment(-1, 0),
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.CALL_SPLIT, size=16, color=ft.Colors.TEAL_300),
                                ft.Text(
                                    "Compare (B)",
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    color=ft.Colors.TEAL_300,
                                ),
                            ],
                            tight=True,
                        ),
                        height=54,
                        alignment=ft.Alignment(-1, 0),
                    ),
                ],
                spacing=0,
            ),
            width=110,
            padding=ft.Padding.only(right=10),
            border=ft.Border(right=ft.BorderSide(1, ft.Colors.GREY_800)),
        )

        # Scrollable node columns
        columns = []
        for i, diff in enumerate(self.diff_results):
            col = self._build_diff_column(diff, is_first=(i == 0), is_last=(i == len(self.diff_results) - 1))
            columns.append(col)

        scrollable_graph = ft.Container(
            content=ft.Row(
                columns,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )

        graph_body = ft.Row(
            [
                lane_labels,
                scrollable_graph,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Column(
            [
                header,
                ft.Divider(height=10, color=ft.Colors.GREY_800),
                graph_body,
            ],
            spacing=5,
        )

    def _legend_chip(self, label: str, color: str) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=8, height=8, border_radius=4, bgcolor=color),
                    ft.Text(label, size=10, color=ft.Colors.GREY_300),
                ],
                spacing=4,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            border_radius=10,
            bgcolor=ft.Colors.WHITE10,
        )

    def _build_diff_column(self, diff: any, is_first: bool, is_last: bool) -> ft.Control:
        is_resolved = diff.uuid in self.resolved_uuids
        title = diff.title or "Untitled"

        # Track line colors
        line_a_color = ft.Colors.INDIGO_700
        line_b_color = ft.Colors.TEAL_700

        # --- Lane A Node ---
        if diff.state == "ONLY_IN_B":
            # Absent in A (dashed ghost node)
            node_a = ft.Container(
                content=ft.Text("— absent in A —", size=10, italic=True, color=ft.Colors.GREY_600),
                width=150,
                height=42,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.GREY_800),
                bgcolor=ft.Colors.TRANSPARENT,
                alignment=ft.Alignment(0, 0),
            )
        else:
            # Present in A (MODIFIED or ONLY_IN_A)
            status_text = "Only in A" if diff.state == "ONLY_IN_A" else ("A NEWER" if diff.ahead == "A" else "Base")
            node_a_bg = ft.Colors.INDIGO_900 if not is_resolved else ft.Colors.BLUE_GREY_900
            border_color = ft.Colors.INDIGO_400 if not is_resolved else ft.Colors.GREEN_600

            node_a = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=10,
                            height=10,
                            border_radius=5,
                            bgcolor=ft.Colors.INDIGO_400 if not is_resolved else ft.Colors.GREEN_400,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    status_text,
                                    size=9,
                                    color=ft.Colors.INDIGO_200 if not is_resolved else ft.Colors.GREEN_200,
                                ),
                            ],
                            spacing=0,
                            alignment=ft.MainAxisAlignment.CENTER,
                            expand=True,
                        ),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=150,
                height=42,
                border_radius=8,
                border=ft.Border.all(1, border_color),
                bgcolor=node_a_bg,
                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                alignment=ft.Alignment(0, 0),
            )

        lane_a_row = ft.Row(
            [
                ft.Container(width=15, height=2, bgcolor=line_a_color if not is_first else ft.Colors.TRANSPARENT),
                node_a,
                ft.Container(width=15, height=2, bgcolor=line_a_color if not is_last else ft.Colors.TRANSPARENT),
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # --- Middle Connector ---
        if is_resolved:
            action = self.resolutions.get(diff.uuid, "Resolved")
            middle_ctrl = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=14),
                        ft.Text(f"Resolved ({action})", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                ),
                bgcolor=ft.Colors.GREEN_900,
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                border=ft.Border.all(1, ft.Colors.GREEN_700),
            )
        elif diff.state == "MODIFIED":
            ahead_arrow = "↑" if diff.ahead == "B" else ("↓" if diff.ahead == "A" else "⮀")
            diff_label = f"{ahead_arrow} {', '.join(diff.diffs[:2])}"
            connector_color = ft.Colors.LIGHT_BLUE_400 if diff.ahead == "B" else ft.Colors.ORANGE_400

            middle_ctrl = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.ARROW_UPWARD if diff.ahead == "B" else ft.Icons.SWAP_VERT,
                            color=connector_color,
                            size=13,
                        ),
                        ft.Text(
                            diff_label,
                            size=9,
                            weight=ft.FontWeight.BOLD,
                            color=connector_color,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=3,
                    tight=True,
                ),
                bgcolor=ft.Colors.WHITE10,
                border_radius=10,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, connector_color),
            )
        elif diff.state == "ONLY_IN_B":
            middle_ctrl = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.ARROW_UPWARD, color=ft.Colors.TEAL_300, size=13),
                        ft.Text("↑ Import to A", size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_200),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=3,
                    tight=True,
                ),
                bgcolor=ft.Colors.TEAL_900,
                border_radius=10,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, ft.Colors.TEAL_600),
            )
        else: # ONLY_IN_A
            middle_ctrl = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.REMOVE_CIRCLE_OUTLINE, color=ft.Colors.RED_300, size=12),
                        ft.Text("Base only", size=9, color=ft.Colors.RED_200),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=3,
                    tight=True,
                ),
                bgcolor=ft.Colors.RED_900,
                border_radius=10,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border=ft.Border.all(1, ft.Colors.RED_700),
            )

        connector_row = ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=1, height=14, bgcolor=ft.Colors.GREY_700),
                    middle_ctrl,
                    ft.Container(width=1, height=14, bgcolor=ft.Colors.GREY_700),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            height=36,
            alignment=ft.Alignment(0, 0),
        )

        # --- Lane B Node ---
        if diff.state == "ONLY_IN_A":
            # Absent in B (dashed ghost node)
            node_b = ft.Container(
                content=ft.Text("— absent in B —", size=10, italic=True, color=ft.Colors.GREY_600),
                width=150,
                height=42,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.GREY_800),
                bgcolor=ft.Colors.TRANSPARENT,
                alignment=ft.Alignment(0, 0),
            )
        else:
            # Present in B (MODIFIED or ONLY_IN_B)
            status_text = "Incoming (B)" if diff.state == "ONLY_IN_B" else ("B NEWER" if diff.ahead == "B" else "Compare")
            node_b_bg = ft.Colors.TEAL_900 if not is_resolved else ft.Colors.BLUE_GREY_900
            border_color = ft.Colors.TEAL_400 if not is_resolved else ft.Colors.GREEN_600

            node_b = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=10,
                            height=10,
                            border_radius=5,
                            bgcolor=ft.Colors.TEAL_400 if not is_resolved else ft.Colors.GREEN_400,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    status_text,
                                    size=9,
                                    color=ft.Colors.TEAL_200 if not is_resolved else ft.Colors.GREEN_200,
                                ),
                            ],
                            spacing=0,
                            alignment=ft.MainAxisAlignment.CENTER,
                            expand=True,
                        ),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=150,
                height=42,
                border_radius=8,
                border=ft.Border.all(1, border_color),
                bgcolor=node_b_bg,
                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                alignment=ft.Alignment(0, 0),
            )

        lane_b_row = ft.Row(
            [
                ft.Container(width=15, height=2, bgcolor=line_b_color if not is_first else ft.Colors.TRANSPARENT),
                node_b,
                ft.Container(width=15, height=2, bgcolor=line_b_color if not is_last else ft.Colors.TRANSPARENT),
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Entire Column Container with click callback
        return ft.Container(
            content=ft.Column(
                [
                    lane_a_row,
                    connector_row,
                    lane_b_row,
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=4, vertical=6),
            border_radius=8,
            on_click=lambda _, d=diff: self.on_select_diff(d),
            tooltip=f"Click to inspect '{title}' ({diff.state})",
            ink=True,
        )

import shutil
from datetime import datetime
import flet as ft
from core.comparator import Comparator
from state.app_state import app_state

from core.merger import Merger

class DiffView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.diff_results = []
        self.resolved_uuids = set()
        self.merger = Merger(app_state.kp_a, app_state.kp_b)
        
        # Save As File Picker
        self.save_file_picker = ft.FilePicker()
        # No longer adding to page.overlay as it is a service in v0.84.0
        self.pending_save_target = None
        self.current_filter = "all"

        self.calculate_diff()
        self.setup_ui()



    async def open_save_dialog(self, target_db):
        default_name = f"merged_{target_db.lower()}_{int(datetime.now().timestamp())}.kdbx"
        path = await self.save_file_picker.save_file(file_name=default_name, allowed_extensions=["kdbx"])
        
        if not path:
            return
            
        try:
            if target_db == 'A':
                app_state.kp_a.save(filename=path)
            else:
                app_state.kp_b.save(filename=path)
                
            snack = ft.SnackBar(ft.Text(f"Successfully saved Database {target_db} to {path}", color=ft.Colors.GREEN))
            self.page.overlay.append(snack)
            snack.open = True
            self.page.update()
            
        except Exception as ex:
            err_dlg = ft.AlertDialog(
                title=ft.Text("Error"),
                content=ft.Text(f"Failed to save: {str(ex)}"),
            )
            self.page.dialog = err_dlg
            err_dlg.open = True
            self.page.update()

    def sort_diff_entries(self):
        # TODO: Sort mainly by modification time? 
        # For now just keep order or sort by title
        self.diff_results.sort(key=lambda x: x.title or "")



    def calculate_diff(self):
        comparator = Comparator(app_state.kp_a, app_state.kp_b)
        self.diff_results = comparator.compare()

    def setup_ui(self):
        # Left Panel: List of Changes
        self.diff_list = ft.ListView(
            expand=True, 
            spacing=10, 
            padding=10, 
            auto_scroll=False
        )

        # Filter Tabs
        self.filter_tabs = ft.Tabs(
            selected_index=0,
            length=5,
            on_change=self.on_filter_change,
            content=ft.TabBar(
                tabs=[
                    ft.Tab(label="All"),
                    ft.Tab(label="Changed"),
                    ft.Tab(label="A Only"),
                    ft.Tab(label="B Only"),
                    ft.Tab(label="Resolved"),
                ],
            )
        )
        
        self.refresh_list(update_ui=False)

        # Right Panel: Details
        self.details_container = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text("Select an item to view details", italic=True, color=ft.Colors.GREY_500)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        self.layout = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Column([
                        self.filter_tabs,
                        self.diff_list
                    ]),
                    width=350,
                    bgcolor=ft.Colors.SURFACE,
                    border_radius=10,
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_800),
                ft.Container(
                    content=self.details_container,
                    expand=True,
                    padding=20
                )
            ],
            expand=True
        )

    def on_filter_change(self, e):
        # In v0.84.0, e.data contains the index
        idx = int(e.data) if e.data is not None else self.filter_tabs.selected_index
        filters = ["all", "MODIFIED", "ONLY_IN_A", "ONLY_IN_B", "resolved"]
        self.current_filter = filters[idx]
        self.refresh_list()

    def refresh_list(self, update_ui=True):
        self.diff_list.controls.clear()
        
        # Filter and Sort
        filtered = []
        for d in self.diff_results:
            is_resolved = d.uuid in self.resolved_uuids
            if self.current_filter == "all":
                filtered.append(d)
            elif self.current_filter == "resolved" and is_resolved:
                filtered.append(d)
            elif self.current_filter == d.state and not is_resolved:
                filtered.append(d)
        
        # Sort: Resolved at bottom, then by state, then by title
        def sort_key(d):
            is_resolved = d.uuid in self.resolved_uuids
            # Resolved (1) or Not (0)
            res_val = 1 if is_resolved else 0
            # State priority: MODIFIED (0), ONLY_IN_A (1), ONLY_IN_B (2)
            state_priority = {'MODIFIED': 0, 'ONLY_IN_A': 1, 'ONLY_IN_B': 2}.get(d.state, 3)
            return (res_val, state_priority, d.title or "")
            
        filtered.sort(key=sort_key)

        for diff in filtered:
            is_resolved = diff.uuid in self.resolved_uuids
            
            icon = ft.Icons.QUESTION_MARK
            color = ft.Colors.GREY
            subtitle = ""
            trailing = None
            
            if is_resolved:
                icon = ft.Icons.CHECK_CIRCLE
                color = ft.Colors.BLUE_400
                subtitle = "Resolved"
            elif diff.state == 'ONLY_IN_A':
                icon = ft.Icons.REMOVE_CIRCLE_OUTLINE
                color = ft.Colors.RED_400
                subtitle = "Only in DB A"
            elif diff.state == 'ONLY_IN_B':
                icon = ft.Icons.ADD_CIRCLE_OUTLINE
                color = ft.Colors.GREEN_400
                subtitle = "Only in DB B"
            elif diff.state == 'MODIFIED':
                icon = ft.Icons.EDIT
                color = ft.Colors.ORANGE_400
                subtitle = f"Changed: {', '.join(diff.diffs)}"
                
                # Directional indicator
                if diff.ahead == 'A':
                    trailing = ft.Container(
                        content=ft.Text("A NEWER", size=10, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.INDIGO_700,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=4
                    )
                elif diff.ahead == 'B':
                    trailing = ft.Container(
                        content=ft.Text("B NEWER", size=10, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.TEAL_700,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=4
                    )

            tile = ft.ListTile(
                leading=ft.Icon(icon, color=color),
                title=ft.Text(diff.title or "Untitled"),
                subtitle=ft.Text(subtitle),
                trailing=trailing,
                on_click=lambda e, d=diff: self.show_details(d),
                selected=False
            )
            self.diff_list.controls.append(tile)
        
        if update_ui:
            self.page.update()

    def show_details(self, diff):
        self.details_container.alignment = ft.MainAxisAlignment.START
        self.details_container.horizontal_alignment = ft.CrossAxisAlignment.START
        self.details_container.controls.clear()
        
        # Header
        self.details_container.controls.append(
            ft.Text(f"Entry: {diff.title}", size=24, weight=ft.FontWeight.BOLD)
        )
        self.details_container.controls.append(ft.Divider())

        if diff.uuid in self.resolved_uuids:
            self.details_container.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("This conflict has been resolved.", size=16, color=ft.Colors.GREEN)
                    ]),
                    bgcolor=ft.Colors.GREEN_900,
                    padding=15,
                    border_radius=10
                )
            )
            self.page.update()
            return

        fields = ['title', 'username', 'password', 'url', 'notes']

        if diff.state == 'MODIFIED':
            # Side by side comparison

            
            import os
            
            # Use DB file modification time as requested
            try:
                ts_a = datetime.fromtimestamp(os.path.getmtime(app_state.db_path_a)) if app_state.db_path_a else None
            except:
                ts_a = None
                
            try:
                ts_b = datetime.fromtimestamp(os.path.getmtime(app_state.db_path_b)) if app_state.db_path_b else None
            except:
                ts_b = None
            
            latest_is_a = (diff.ahead == 'A')
            latest_is_b = (diff.ahead == 'B')
            
            # If ahead is None (no history match and identical mtime), use mtime as fallback
            if diff.ahead is None and ts_a and ts_b:
                if ts_a > ts_b:
                    latest_is_a = True
                elif ts_b > ts_a:
                    latest_is_b = True

            def format_ts(ts):
                if not ts: return "Unknown"
                return ts.strftime("%Y-%m-%d %H:%M:%S")

            def create_header_content(title, title_color, ts, is_latest):
                items = [
                    ft.Text(title, weight=ft.FontWeight.BOLD, color=title_color),
                    ft.Text(f"Modified: {format_ts(ts)}", size=12, color=ft.Colors.GREY_400)
                ]
                
                if is_latest:
                    items.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.STAR, size=14, color=ft.Colors.WHITE),
                                ft.Text("LATEST VERSION", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                            ], alignment=ft.MainAxisAlignment.START, spacing=4, tight=True),
                            bgcolor=ft.Colors.GREEN_600,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=4,
                        )
                    )
                return items

            header_a = ft.Column(
                create_header_content("Database A (Current)", ft.Colors.INDIGO_200, ts_a, latest_is_a)
            )
            
            header_b = ft.Column(
                create_header_content("Database B (Incoming)", ft.Colors.TEAL_200, ts_b, latest_is_b)
            )

            self.details_container.controls.append(
                ft.Row([
                    ft.Text("Field", width=100, weight=ft.FontWeight.BOLD),
                    ft.Container(content=header_a, expand=True),
                    ft.Container(content=header_b, expand=True),
                ])
            )
            self.details_container.controls.append(ft.Divider())
            
            for field in fields:
                val_a = getattr(diff.entry_a, field)
                val_b = getattr(diff.entry_b, field)
                
                is_diff = field in diff.diffs
                bg_color = ft.Colors.WHITE10 if is_diff else ft.Colors.TRANSPARENT
                
                if field == 'password':
                    control_a = ft.TextField(value=str(val_a), password=True, can_reveal_password=True, read_only=True, expand=True)
                    control_b = ft.TextField(value=str(val_b), password=True, can_reveal_password=True, read_only=True, expand=True)
                else:
                    control_a = ft.Text(str(val_a), expand=True, selectable=True)
                    control_b = ft.Text(str(val_b), expand=True, selectable=True)

                self.details_container.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(field.capitalize(), width=100),
                            control_a,
                            control_b,
                        ]),
                        bgcolor=bg_color,
                        padding=5,
                        border_radius=5
                    )
                )

            # Action Buttons
            self.details_container.controls.append(ft.Divider())
            self.details_container.controls.append(
                ft.Row([
                    ft.ElevatedButton("Keep Current (A)", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=lambda _: self.page.run_task(self.resolve_conflict, diff, 'A')),
                    ft.ElevatedButton("Accept Incoming (B)", icon=ft.Icons.ARROW_CIRCLE_RIGHT_OUTLINED, on_click=lambda _: self.page.run_task(self.resolve_conflict, diff, 'B')),
                    ft.ElevatedButton("Keep Both", icon=ft.Icons.COPY_ALL, on_click=lambda _: self.page.run_task(self.resolve_conflict, diff, 'BOTH')),
                ])
            )

        elif diff.state == 'ONLY_IN_A':
            self.details_container.controls.append(
                ft.Text("This entry exists only in Database A (Current).", color=ft.Colors.INDIGO_200, size=16)
            )
            self.details_container.controls.append(ft.Divider())
             
            for field in fields:
                val_a = getattr(diff.entry_a, field)
                
                if field == 'password':
                    control_a = ft.TextField(value=str(val_a), password=True, can_reveal_password=True, read_only=True, expand=True)
                else:
                    control_a = ft.Text(str(val_a), selectable=True, expand=True)

                self.details_container.controls.append(
                    ft.Row([
                        ft.Text(field.capitalize(), width=100, weight=ft.FontWeight.BOLD),
                        control_a
                    ])
                )
            
            self.details_container.controls.append(ft.Divider())
            self.details_container.controls.append(
                ft.Row([
                    ft.ElevatedButton("Keep in A", icon=ft.Icons.CHECK, on_click=lambda _: self.page.run_task(self.resolve_conflict, diff, 'KEEP_A')),
                    ft.ElevatedButton("Delete from A", icon=ft.Icons.DELETE, style=ft.ButtonStyle(color=ft.Colors.RED), on_click=lambda _: self.page.run_task(self.resolve_conflict, diff, 'DELETE_A')),
                ])
            )
        
        elif diff.state == 'ONLY_IN_B':
            self.details_container.controls.append(
                ft.Text("This entry exists only in Database B (Incoming).", color=ft.Colors.TEAL_200, size=16)
            )
            self.details_container.controls.append(ft.Divider())
            
            for field in fields:
                val_b = getattr(diff.entry_b, field)
                
                if field == 'password':
                    control_b = ft.TextField(value=str(val_b), password=True, can_reveal_password=True, read_only=True, expand=True)
                else:
                    control_b = ft.Text(str(val_b), selectable=True, expand=True)

                self.details_container.controls.append(
                    ft.Row([
                        ft.Text(field.capitalize(), width=100, weight=ft.FontWeight.BOLD),
                        control_b
                    ])
                )

            self.details_container.controls.append(ft.Divider())
            self.details_container.controls.append(
                ft.Row([
                     ft.ElevatedButton("Import to A", icon=ft.Icons.ADD, on_click=lambda _: self.page.run_task(self.resolve_conflict, diff, 'IMPORT_B')),
                     ft.ElevatedButton("Ignore", icon=ft.Icons.CLOSE, on_click=lambda _: self.page.run_task(self.resolve_conflict, diff, 'IGNORE_B')),
                ])
            )

        self.page.update()

    async def resolve_conflict(self, diff, action):
        try:
            self.merger.apply_resolution(diff, action)
            self.resolved_uuids.add(diff.uuid)
            self.refresh_list()
            self.show_details(diff) 
            
            snack = ft.SnackBar(ft.Text(f"Resolved: {diff.title} -> {action}"))
            self.page.overlay.append(snack)
            snack.open = True
            self.page.update()
        except Exception as e:
            snack = ft.SnackBar(ft.Text(f"Error resolving: {str(e)}", color=ft.Colors.RED))
            self.page.overlay.append(snack)
            snack.open = True
            self.page.update()

    async def bulk_accept_incoming(self, e):
        count = 0
        for diff in self.diff_results:
            if diff.uuid in self.resolved_uuids:
                continue
            
            if diff.state == 'MODIFIED':
                self.merger.apply_resolution(diff, 'B')
                self.resolved_uuids.add(diff.uuid)
                count += 1
            elif diff.state == 'ONLY_IN_B':
                self.merger.apply_resolution(diff, 'IMPORT_B')
                self.resolved_uuids.add(diff.uuid)
                count += 1
        
        self.refresh_list()
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Bulk Accepted {count} entries."))
        self.page.snack_bar.open = True
        self.page.update()



    async def go_back(self, e):
        await self.page.push_route("/")

    @property
    def view(self):
        return ft.View(
            controls=[
                ft.AppBar(
                    leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=self.go_back),
                    title=ft.Text("Comparison Results"),
                    bgcolor=ft.Colors.SURFACE,
                    actions=[
                        ft.PopupMenuButton(
                            items=[
                                ft.PopupMenuItem(content=ft.Text("Accept All Incoming (Update/Import)"), on_click=self.bulk_accept_incoming),
                            ]
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.SAVE,
                            tooltip="Save Options",
                            items=[
                                ft.PopupMenuItem(content=ft.Text("Save A as..."), on_click=lambda _: self.page.run_task(self.open_save_dialog, 'A')),
                                ft.PopupMenuItem(content=ft.Text("Save B as..."), on_click=lambda _: self.page.run_task(self.open_save_dialog, 'B')),
                            ]
                        )
                    ]
                ),
                self.layout
            ],
            route="/diff",
            bgcolor=ft.Colors.BLUE_GREY_900,
            padding=10
        )

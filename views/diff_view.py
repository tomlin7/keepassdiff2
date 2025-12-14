import shutil
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
        self.calculate_diff()
        self.setup_ui()

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
                    content=self.diff_list,
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

    def refresh_list(self, update_ui=True):
        self.diff_list.controls.clear()
        for diff in self.diff_results:
            is_resolved = diff.uuid in self.resolved_uuids
            
            icon = ft.Icons.QUESTION_MARK
            color = ft.Colors.GREY
            subtitle = ""
            
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

            tile = ft.ListTile(
                leading=ft.Icon(icon, color=color),
                title=ft.Text(diff.title or "Untitled"),
                subtitle=ft.Text(subtitle),
                on_click=lambda e, d=diff: self.show_details(d),
                selected=False # Can track selection if needed
            )
            self.diff_list.controls.append(tile)
        
        if update_ui:
            self.diff_list.update()

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
            self.details_container.update()
            return

        fields = ['title', 'username', 'password', 'url', 'notes']

        if diff.state == 'MODIFIED':
            # Side by side comparison
            self.details_container.controls.append(
                ft.Row([
                    ft.Text("Field", width=100, weight=ft.FontWeight.BOLD),
                    ft.Text("Database A (Current)", expand=True, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_200),
                    ft.Text("Database B (Incoming)", expand=True, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_200),
                ])
            )
            self.details_container.controls.append(ft.Divider())
            
            for field in fields:
                val_a = getattr(diff.entry_a, field)
                val_b = getattr(diff.entry_b, field)
                
                is_diff = field in diff.diffs
                bg_color = ft.Colors.WHITE10 if is_diff else ft.Colors.TRANSPARENT
                
                self.details_container.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(field.capitalize(), width=100),
                            ft.Text(str(val_a), expand=True, selectable=True),
                            ft.Text(str(val_b), expand=True, selectable=True),
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
                    ft.ElevatedButton("Keep Current (A)", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=lambda _: self.resolve_conflict(diff, 'A')),
                    ft.ElevatedButton("Accept Incoming (B)", icon=ft.Icons.ARROW_CIRCLE_RIGHT_OUTLINED, on_click=lambda _: self.resolve_conflict(diff, 'B')),
                ])
            )

        elif diff.state == 'ONLY_IN_A':
            self.details_container.controls.append(
                ft.Text("This entry exists only in Database A (Current).", color=ft.Colors.INDIGO_200, size=16)
            )
            self.details_container.controls.append(ft.Divider())
             
            for field in fields:
                val_a = getattr(diff.entry_a, field)
                self.details_container.controls.append(
                    ft.Row([
                        ft.Text(field.capitalize(), width=100, weight=ft.FontWeight.BOLD),
                        ft.Text(str(val_a), selectable=True)
                    ])
                )
            
            self.details_container.controls.append(ft.Divider())
            self.details_container.controls.append(
                ft.Row([
                    ft.ElevatedButton("Keep in A", icon=ft.Icons.CHECK, on_click=lambda _: self.resolve_conflict(diff, 'KEEP_A')),
                    ft.ElevatedButton("Delete from A", icon=ft.Icons.DELETE, style=ft.ButtonStyle(color=ft.Colors.RED), on_click=lambda _: self.resolve_conflict(diff, 'DELETE_A')),
                ])
            )
        
        elif diff.state == 'ONLY_IN_B':
            self.details_container.controls.append(
                ft.Text("This entry exists only in Database B (Incoming).", color=ft.Colors.TEAL_200, size=16)
            )
            self.details_container.controls.append(ft.Divider())
            
            for field in fields:
                val_b = getattr(diff.entry_b, field)
                self.details_container.controls.append(
                    ft.Row([
                        ft.Text(field.capitalize(), width=100, weight=ft.FontWeight.BOLD),
                        ft.Text(str(val_b), selectable=True)
                    ])
                )

            self.details_container.controls.append(ft.Divider())
            self.details_container.controls.append(
                ft.Row([
                     ft.ElevatedButton("Import to A", icon=ft.Icons.ADD, on_click=lambda _: self.resolve_conflict(diff, 'IMPORT_B')),
                     ft.ElevatedButton("Ignore", icon=ft.Icons.CLOSE, on_click=lambda _: self.resolve_conflict(diff, 'IGNORE_B')),
                ])
            )

        self.details_container.update()

    def resolve_conflict(self, diff, action):
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

    def bulk_accept_incoming(self, e):
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

    def save_db(self, e):
        try:
            # Backup
            if app_state.db_path_a:
                shutil.copy2(app_state.db_path_a, app_state.db_path_a + ".bak")

            # Save A
            app_state.kp_a.save()
            
            dlg = ft.AlertDialog(
                title=ft.Text("Success"),
                content=ft.Text("Database A has been backed up (.bak) and saved successfully!"),
            )
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
        except Exception as ex:
             dlg = ft.AlertDialog(
                title=ft.Text("Error"),
                content=ft.Text(f"Failed to save: {str(ex)}"),
            )
             self.page.dialog = dlg
             dlg.open = True
             self.page.update()

    @property
    def view(self):
        return ft.View(
            "/diff",
            controls=[
                ft.AppBar(
                    leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: self.page.go("/")),
                    title=ft.Text("Comparison Results"),
                    bgcolor=ft.Colors.SURFACE,
                    actions=[
                        ft.PopupMenuButton(
                            items=[
                                ft.PopupMenuItem(text="Accept All Incoming (Update/Import)", on_click=self.bulk_accept_incoming),
                            ]
                        ),
                        ft.IconButton(ft.Icons.SAVE, tooltip="Save Merged DB Changes to A", on_click=self.save_db)
                    ]
                ),
                self.layout
            ],
            bgcolor=ft.Colors.BLUE_GREY_900,
            padding=10
        )

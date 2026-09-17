import os
import flet as ft
from state.app_state import app_state
from storage.config_manager import config_manager

class WelcomeView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_ui()
        
    def setup_ui(self):
        # File pickers
        self.file_picker_a = ft.FilePicker()
        self.file_picker_b = ft.FilePicker()
        self.keyfile_picker_a = ft.FilePicker()
        self.keyfile_picker_b = ft.FilePicker()
        # No longer adding to page.overlay as it is a service in v0.84.0
        
        # Inputs A
        self.path_field_a = ft.TextField(
            label="Database A (Base)",
            value=app_state.db_path_a or "",
            read_only=True,
            expand=True,
            icon=ft.Icons.FILE_OPEN,
        )
        self.pass_field_a = ft.TextField(
            label="Password A",
            value=app_state.password_a or "",
            password=True,
            can_reveal_password=True,
            expand=True,
        )
        self.key_field_a = ft.TextField(
            label="Keyfile A (Optional)",
            value=app_state.keyfile_a or "",
            read_only=True,
            expand=True,
            icon=ft.Icons.KEY,
        )

        # Inputs B
        self.path_field_b = ft.TextField(
            label="Database B (Compare)",
            value=app_state.db_path_b or "",
            read_only=True,
            expand=True,
            icon=ft.Icons.FILE_OPEN,
        )
        self.pass_field_b = ft.TextField(
            label="Password B",
            value=app_state.password_b or "",
            password=True,
            can_reveal_password=True,
            expand=True,
        )
        self.key_field_b = ft.TextField(
            label="Keyfile B (Optional)",
            value=app_state.keyfile_b or "",
            read_only=True,
            expand=True,
            icon=ft.Icons.KEY,
        )

        # MRU History buttons
        self.mru_button_a = ft.PopupMenuButton(
            icon=ft.Icons.HISTORY,
            tooltip="Recent Databases",
            items=self._build_mru_items("A"),
        )
        self.mru_button_b = ft.PopupMenuButton(
            icon=ft.Icons.HISTORY,
            tooltip="Recent Databases",
            items=self._build_mru_items("B"),
        )
        
        self.loading = ft.ProgressBar(visible=False)
        self.error_text = ft.Text(color=ft.Colors.RED_400, visible=False)

    def _build_mru_items(self, side: str):
        paths = config_manager.get_mru_paths()
        if not paths:
            return [
                ft.PopupMenuItem(
                    content=ft.Text("No recent databases", italic=True),
                    disabled=True,
                )
            ]
        items = []
        for p in paths:
            file_name = os.path.basename(p)
            items.append(
                ft.PopupMenuItem(
                    content=ft.Column(
                        [
                            ft.Text(file_name, weight=ft.FontWeight.BOLD),
                            ft.Text(p, size=11, color=ft.Colors.GREY_400),
                        ],
                        spacing=2,
                    ),
                    on_click=lambda _, path=p, s=side: self._select_mru(s, path),
                )
            )
        return items

    def _select_mru(self, side: str, path: str):
        if side == "A":
            app_state.db_path_a = path
            self.path_field_a.value = path
        else:
            app_state.db_path_b = path
            self.path_field_b.value = path
        self.page.update()

    def _refresh_mru_menus(self):
        self.mru_button_a.items = self._build_mru_items("A")
        self.mru_button_b.items = self._build_mru_items("B")

    async def pick_file_a(self, e):
        init_dir = config_manager.get_last_directory()
        files = await self.file_picker_a.pick_files(
            allowed_extensions=["kdbx"], initial_directory=init_dir
        )
        if files:
            app_state.db_path_a = files[0].path
            self.path_field_a.value = files[0].path
            config_manager.add_mru_path(files[0].path)
            self._refresh_mru_menus()
            self.page.update()

    async def pick_file_b(self, e):
        init_dir = config_manager.get_last_directory()
        files = await self.file_picker_b.pick_files(
            allowed_extensions=["kdbx"], initial_directory=init_dir
        )
        if files:
            app_state.db_path_b = files[0].path
            self.path_field_b.value = files[0].path
            config_manager.add_mru_path(files[0].path)
            self._refresh_mru_menus()
            self.page.update()

    async def pick_key_a(self, e):
        files = await self.keyfile_picker_a.pick_files()
        if files:
            app_state.keyfile_a = files[0].path
            self.key_field_a.value = files[0].path
            self.page.update()

    async def pick_key_b(self, e):
        files = await self.keyfile_picker_b.pick_files()
        if files:
            app_state.keyfile_b = files[0].path
            self.key_field_b.value = files[0].path
            self.page.update()

    async def load_databases(self, e):
        self.loading.visible = True
        self.error_text.visible = False
        self.page.update()
        
        try:
            if not app_state.db_path_a or not app_state.db_path_b:
                raise ValueError("Please select both database files.")
            
            # Load A
            app_state.load_database('A', self.pass_field_a.value, keyfile=self.key_field_a.value)
            
            # Load B
            app_state.load_database('B', self.pass_field_b.value, keyfile=self.key_field_b.value)
            
            config_manager.add_mru_path(app_state.db_path_a)
            config_manager.add_mru_path(app_state.db_path_b)
            
            # If successful, navigate
            await self.page.push_route("/diff")
            
        except Exception as ex:
            self.error_text.value = f"Error: {str(ex)}"
            self.error_text.visible = True
            self.loading.visible = False
            self.page.update()

    @property
    def view(self):
        return ft.View(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("KeePass Diff & Merge", size=40, weight=ft.FontWeight.BOLD),
                            ft.Text("Compare and synchronize your password databases intelligently.", size=16, color=ft.Colors.GREY_400),
                            ft.Text("Database A is your Base database. Incoming entries and updates from Database B (Compare) can be reviewed and merged into Database A.", size=13, color=ft.Colors.INDIGO_200, text_align=ft.TextAlign.CENTER),
                            ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                            
                            # Database A Section
                            ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Text("Database A (Base)", weight=ft.FontWeight.BOLD),
                                        ft.Row([
                                            self.path_field_a,
                                            ft.IconButton(ft.Icons.FOLDER_OPEN, tooltip="Browse Database A", on_click=self.pick_file_a),
                                            self.mru_button_a,
                                        ]),
                                        ft.Row([
                                            self.key_field_a,
                                            ft.IconButton(ft.Icons.KEY, tooltip="Browse Keyfile A", on_click=self.pick_key_a)
                                        ]),
                                        self.pass_field_a
                                    ]),
                                    padding=20
                                )
                            ),
                            
                            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                            # Database B Section
                            ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Text("Database B (Compare)", weight=ft.FontWeight.BOLD),
                                        ft.Row([
                                            self.path_field_b,
                                            ft.IconButton(ft.Icons.FOLDER_OPEN, tooltip="Browse Database B", on_click=self.pick_file_b),
                                            self.mru_button_b,
                                        ]),
                                        ft.Row([
                                            self.key_field_b,
                                            ft.IconButton(ft.Icons.KEY, on_click=self.pick_key_b)
                                        ]),
                                        self.pass_field_b
                                    ]),
                                    padding=20
                                )
                            ),
                            
                            ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                            
                            self.loading,
                            self.error_text,
                            
                            ft.ElevatedButton(
                                "UNLOCK & COMPARE",
                                icon=ft.Icons.COMPARE_ARROWS,
                                style=ft.ButtonStyle(
                                    padding=20,
                                    shape=ft.RoundedRectangleBorder(radius=10)
                                ),
                                width=300,
                                on_click=self.load_databases
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=50,
                    alignment=ft.Alignment(0, 0)
                )
            ],
            route="/",
            bgcolor=ft.Colors.BLUE_GREY_900,
            scroll=ft.ScrollMode.AUTO
        )

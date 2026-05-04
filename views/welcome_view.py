import flet as ft
from state.app_state import app_state

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
        self.path_field_a = ft.TextField(label="Database A Source", read_only=True, expand=True, icon=ft.Icons.FILE_OPEN)
        self.pass_field_a = ft.TextField(label="Password A", password=True, can_reveal_password=True, expand=True)
        self.key_field_a = ft.TextField(label="Keyfile A (Optional)", read_only=True, expand=True, icon=ft.Icons.KEY)

        # Inputs B
        self.path_field_b = ft.TextField(label="Database B Target", read_only=True, expand=True, icon=ft.Icons.FILE_OPEN)
        self.pass_field_b = ft.TextField(label="Password B", password=True, can_reveal_password=True, expand=True)
        self.key_field_b = ft.TextField(label="Keyfile B (Optional)", read_only=True, expand=True, icon=ft.Icons.KEY)
        
        self.loading = ft.ProgressBar(visible=False)
        self.error_text = ft.Text(color=ft.Colors.RED_400, visible=False)

    async def pick_file_a(self, e):
        files = await self.file_picker_a.pick_files(allowed_extensions=["kdbx"])
        if files:
            app_state.db_path_a = files[0].path
            self.path_field_a.value = files[0].path
            self.page.update()

    async def pick_file_b(self, e):
        files = await self.file_picker_b.pick_files(allowed_extensions=["kdbx"])
        if files:
            app_state.db_path_b = files[0].path
            self.path_field_b.value = files[0].path
            self.page.update()

    async def pick_key_a(self, e):
        files = await self.keyfile_picker_a.pick_files()
        if files:
            self.key_field_a.value = files[0].path
            self.page.update()

    async def pick_key_b(self, e):
        files = await self.keyfile_picker_b.pick_files()
        if files:
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
                            ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                            
                            # Database A Section
                            ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Text("Database A (Base)", weight=ft.FontWeight.BOLD),
                                        ft.Row([
                                            self.path_field_a,
                                            ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=self.pick_file_a)
                                        ]),
                                        ft.Row([
                                            self.key_field_a,
                                            ft.IconButton(ft.Icons.KEY, on_click=self.pick_key_a)
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
                                            ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=self.pick_file_b)
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

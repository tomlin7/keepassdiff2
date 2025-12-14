import flet as ft
from views.welcome_view import WelcomeView
from views.diff_view import DiffView
from state.app_state import app_state

def main(page: ft.Page):
    page.title = "KeePassDiff - Sophisticated DB Merger"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window.width = 1200
    page.window.height = 800
    
    # Define a modern theme
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ft.Colors.INDIGO_400,
            secondary=ft.Colors.TEAL_400,
            background=ft.Colors.BLUE_GREY_900,
            surface=ft.Colors.BLUE_GREY_800,
        )
    )

    def route_change(route):
        page.views.clear()
        
        # Welcome / Setup View
        if page.route == "/":
            page.views.append(WelcomeView(page).view)
            
        # Main Diff View
        elif page.route == "/diff":
            if not app_state.kp_a or not app_state.kp_b:
                page.go("/")
                return
            page.views.append(DiffView(page).view)
            
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)

if __name__ == "__main__":
    ft.app(target=main)

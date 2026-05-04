import flet as ft
import asyncio
from views.welcome_view import WelcomeView
from views.diff_view import DiffView
from state.app_state import app_state

async def main(page: ft.Page):
    page.title = "KeePassDiff - Diff & Merge"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window.width = 1000
    page.window.height = 1000
    
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ft.Colors.INDIGO_400,
            secondary=ft.Colors.TEAL_400,
            surface=ft.Colors.BLUE_GREY_900,
            on_surface=ft.Colors.WHITE,
        )
    )

    async def route_change(e):
        page.views.clear()
        
        # Welcome / Setup View
        if page.route == "/":
            page.views.append(WelcomeView(page).view)
            
        # Main Diff View
        elif page.route == "/diff":
            if not app_state.kp_a or not app_state.kp_b:
                await page.push_route("/")
                return
            page.views.append(DiffView(page).view)
        
        else:
            page.views.append(WelcomeView(page).view)
            
        page.update()

    async def view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        await page.push_route(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Initialize views
    await route_change(None)
    page.update()

if __name__ == "__main__":
    ft.run(main)

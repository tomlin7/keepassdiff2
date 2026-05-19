# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-05-04

### Changed
- **Migrated to Flet v0.84.0**:
    - Converted `main()` and all core event handlers to `async` coroutines.
    - Replaced `ft.app()` with `ft.run()`.
    - Replaced deprecated `page.go()` with `await page.push_route()`.
- **Refactored FilePicker Logic**:
    - Transitioned `FilePicker` from a UI Control to a Service.
    - Removed `FilePicker` instances from `page.overlay` to prevent "Unknown control" errors.
    - Updated file picking and saving to use the new `await pick_files()` and `await save_file()` return patterns.
- **UI & Layout Updates**:
    - Corrected `ft.View` constructor calls to reflect new argument ordering (`controls` is now positional first).
    - Replaced `PopupMenuItem(text=...)` with `PopupMenuItem(content=ft.Text(...))`.
    - **Migrated `ft.Tabs`**: Overhauled Tabs implementation to use the new `length`, `content`, and `ft.TabBar` structure required by v0.84.0.
    - Replaced `Tab(text=...)` with `Tab(label=...)`.
    - Migrated legacy `ft.alignment` constants to `ft.Alignment(x, y)` coordinates.
- **Navigation Fixes**:
    - Refactored `DiffView` navigation handlers to use `self.page.run_task()` for reliable async execution from button clicks.
    - Fixed a bug where a naked `page.update()` call caused a crash during database loading.

### Fixed
- Resolved "Blank Screen" on startup caused by unhandled exceptions in the new async lifecycle.
- Fixed "Unknown control: FilePicker" error by removing Services from the visual control tree.
- Fixed `TypeError` in `PopupMenuItem` caused by deprecated arguments.

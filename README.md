# KeePass Diff & Merge Tool

A sophisticated Python Flet application to compare and merge two KeePass (`.kdbx`) databases.

## Features
- **Load Two Databases**: Compare a "Base" (A) against a "Target" (B). Supports passwords and keyfiles.
- **Visual Diff**: See entries that are Added, Removed, or Modified.
- **Side-by-Side Comparison**: intelligent field-level comparison (Title, Username, Password, URL, Notes).
- **Conflict Resolution**: Decide per-entry whether to Keep A, Accept B, Import from B, or Delete.
- **Bulk Actions**: One-click "Accept All Incoming" to quickly merge changes from B to A.
- **Safety First**: Automatically creates a backup (`.bak`) of Database A before saving changes.

## Installation
1. Install Python 3.8+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the application:
```bash
flet run main.py
```
1. Select **Database A** (Your main database).
2. Select **Database B** (The other database you want to merge from).
3. Unlock both.
4. Use the interface to Compare and Merge.
5. Click **Save** to apply changes to Database A.

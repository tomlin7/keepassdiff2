from pykeepass import PyKeePass
import os

class AppState:
    def __init__(self):
        self.db_path_a: str = None
        self.db_path_b: str = None
        self.password_a: str = None
        self.password_b: str = None
        self.kp_a: PyKeePass = None
        self.kp_b: PyKeePass = None
        self.diff_result = None

    def load_database(self, side: str, password: str, keyfile: str = None):
        path = self.db_path_a if side == 'A' else self.db_path_b
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Database {side} path not found")
        
        kp = PyKeePass(path, password=password, keyfile=keyfile)
        if side == 'A':
            self.kp_a = kp
            self.password_a = password
        else:
            self.kp_b = kp
            self.password_b = password
            
    def close_databases(self):
        self.kp_a = None
        self.kp_b = None
        # Verify if explicit close is needed for pykeepass (usually generic python GC handles file handles, but explicit is better if available)

app_state = AppState()

from pykeepass import PyKeePass
from pykeepass.entry import Entry
from collections import namedtuple

DiffEntry = namedtuple('DiffEntry', ['uuid', 'title', 'state', 'entry_a', 'entry_b', 'diffs', 'ahead'])

class Comparator:
    def __init__(self, kp_a: PyKeePass, kp_b: PyKeePass):
        self.kp_a = kp_a
        self.kp_b = kp_b

    def compare(self):
        entries_a = {e.uuid: e for e in self.kp_a.entries}
        entries_b = {e.uuid: e for e in self.kp_b.entries}
        
        all_uuids = set(entries_a.keys()) | set(entries_b.keys())
        diff_results = []

        for uuid in all_uuids:
            entry_a = entries_a.get(uuid)
            entry_b = entries_b.get(uuid)
            
            if entry_a and not entry_b:
                diff_results.append(DiffEntry(uuid, entry_a.title, 'ONLY_IN_A', entry_a, None, [], 'A'))
            elif entry_b and not entry_a:
                diff_results.append(DiffEntry(uuid, entry_b.title, 'ONLY_IN_B', None, entry_b, [], 'B'))
            else:
                # In both, compare fields
                diffs = self._compare_fields(entry_a, entry_b)
                if diffs:
                    ahead = self._detect_ahead(entry_a, entry_b)
                    diff_results.append(DiffEntry(uuid, entry_a.title, 'MODIFIED', entry_a, entry_b, diffs, ahead))
                else:
                    # Identical
                    pass # We might want to skip identical ones for the diff view
        
        return diff_results

    def _detect_ahead(self, a, b):
        # 1. Check history
        # If a is in b's history, then b is ahead
        if self._is_in_history(a, b.history):
            return 'B'
        # If b is in a's history, then a is ahead
        if self._is_in_history(b, a.history):
            return 'A'
            
        # 2. Fallback to mtime
        if a.mtime > b.mtime:
            return 'A'
        elif b.mtime > a.mtime:
            return 'B'
            
        return None

    def _is_in_history(self, entry, history):
        if not history:
            return False
        
        # Check the last 5 history entries (limit to avoid performance issues)
        for h_entry in reversed(history[-5:]):
            if not self._compare_fields(entry, h_entry):
                return True
        return False

    def _compare_fields(self, a: Entry, b: Entry):
        diffs = []
        fields = ['title', 'username', 'password', 'url', 'notes']
        
        for field in fields:
            val_a = getattr(a, field)
            val_b = getattr(b, field)
            if val_a != val_b:
                diffs.append(field)
                
        return diffs

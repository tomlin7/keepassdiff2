from pykeepass import PyKeePass
from pykeepass.entry import Entry
from collections import namedtuple

DiffEntry = namedtuple('DiffEntry', ['uuid', 'title', 'state', 'entry_a', 'entry_b', 'diffs'])

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
                diff_results.append(DiffEntry(uuid, entry_a.title, 'ONLY_IN_A', entry_a, None, []))
            elif entry_b and not entry_a:
                diff_results.append(DiffEntry(uuid, entry_b.title, 'ONLY_IN_B', None, entry_b, []))
            else:
                # In both, compare fields
                diffs = self._compare_fields(entry_a, entry_b)
                if diffs:
                    diff_results.append(DiffEntry(uuid, entry_a.title, 'MODIFIED', entry_a, entry_b, diffs))
                else:
                    # Identical
                    pass # We might want to skip identical ones for the diff view
        
        return diff_results

    def _compare_fields(self, a: Entry, b: Entry):
        diffs = []
        fields = ['title', 'username', 'password', 'url', 'notes']
        
        for field in fields:
            val_a = getattr(a, field)
            val_b = getattr(b, field)
            if val_a != val_b:
                diffs.append(field)
                
        return diffs

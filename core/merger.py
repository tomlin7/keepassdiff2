from pykeepass import PyKeePass
from pykeepass.entry import Entry
from pykeepass.group import Group

class Merger:
    def __init__(self, kp_a: PyKeePass, kp_b: PyKeePass):
        self.kp_a = kp_a
        self.kp_b = kp_b

    def apply_resolution(self, diff_entry, action):
        """
        Apply resolution to kp_a (the base database).
        """
        if diff_entry.state == 'MODIFIED':
            if action == 'B': # Accept Incoming
                self._update_fields(diff_entry.entry_a, diff_entry.entry_b)
                # print(f"Updated entry {diff_entry.title} with values from B")
        
        elif diff_entry.state == 'ONLY_IN_A':
            if action == 'DELETE_A':
                self.kp_a.delete_entry(diff_entry.entry_a)
                # print(f"Deleted entry {diff_entry.title} from A")

        elif diff_entry.state == 'ONLY_IN_B':
            if action == 'IMPORT_B':
                self._import_entry(diff_entry.entry_b)
                # print(f"Imported entry {diff_entry.title} from B")

    def _update_fields(self, target: Entry, source: Entry):
        fields = ['title', 'username', 'password', 'url', 'notes']
        for field in fields:
            val = getattr(source, field)
            setattr(target, field, val)

    def _import_entry(self, source_entry: Entry):
        # 1. Find or create group path
        group_path = self._get_group_path(source_entry.group)
        target_group = self._ensure_group_path(group_path)
        
        # 2. Add entry
        self.kp_a.add_entry(
            destination_group=target_group,
            title=source_entry.title,
            username=source_entry.username,
            password=source_entry.password,
            url=source_entry.url,
            notes=source_entry.notes,
            tags=source_entry.tags,
            expiry_time=source_entry.expiry_time,
            icon=source_entry.icon
        )

    def _get_group_path(self, group: Group):
        path = []
        current = group
        while current:
            path.insert(0, current.name)
            current = current.parent_group
        return path # e.g. ['Root', 'Internet']

    def _ensure_group_path(self, path_names):
        # Start from root of A
        current_group = self.kp_a.root_group
        
        # Check if root name matches (usually 'Root' or file name). 
        # Sometimes root names differ but we treat them as equivalent roots.
        # We'll assume the path is relative to root group structure.
        # PyKeePass structure: root_group is the top one.
        
        # Skip the first element if it matches root name, or just try to traverse children.
        # Path[0] is typically the root group name.
        start_index = 0
        if path_names and current_group.name == path_names[0]:
            start_index = 1
            
        for name in path_names[start_index:]:
            found = None
            for child in current_group.subgroups:
                if child.name == name:
                    found = child
                    break
            
            if found:
                current_group = found
            else:
                # Create it
                current_group = self.kp_a.add_group(destination_group=current_group, group_name=name)
        
        return current_group

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pykeepass import create_database, PyKeePass
from core.comparator import Comparator
from core.merger import Merger

class TestComparatorMerger(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.path_a = os.path.join(self.test_dir, "db_a.kdbx")
        self.path_b = os.path.join(self.test_dir, "db_b.kdbx")
        self.password = "secret"

        self.kp_a = create_database(self.path_a, password=self.password)
        self.kp_a.save()

        self.kp_b = create_database(self.path_b, password=self.password)
        self.kp_b.save()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_import_preserves_uuid_and_timestamps(self):
        # Create an entry in B
        past_ctime = datetime.now(timezone.utc) - timedelta(days=10)
        past_mtime = datetime.now(timezone.utc) - timedelta(days=5)

        entry_b = self.kp_b.add_entry(
            self.kp_b.root_group,
            title="ServiceX",
            username="user1",
            password="pwd"
        )
        entry_b.ctime = past_ctime
        entry_b.mtime = past_mtime
        original_uuid = entry_b.uuid
        self.kp_b.save()

        # Compare
        comparator = Comparator(self.kp_a, self.kp_b)
        diffs = comparator.compare()
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].state, "ONLY_IN_B")

        # Import to A
        merger = Merger(self.kp_a, self.kp_b)
        merger.apply_resolution(diffs[0], "IMPORT_B")
        self.kp_a.save()

        # Check in A
        entry_a = self.kp_a.find_entries(title="ServiceX", first=True)
        self.assertIsNotNone(entry_a)
        # Fix #16: UUID preserved
        self.assertEqual(entry_a.uuid, original_uuid)
        # Fix #11: Timestamps preserved
        self.assertEqual(entry_a.ctime, entry_b.ctime)
        self.assertEqual(entry_a.mtime, entry_b.mtime)

        # Re-compare A and B: should have NO differences!
        reloaded_a = PyKeePass(self.path_a, password=self.password)
        reloaded_b = PyKeePass(self.path_b, password=self.password)
        comparator2 = Comparator(reloaded_a, reloaded_b)
        diffs2 = comparator2.compare()
        self.assertEqual(len(diffs2), 0, "Entries should now be identical with matching UUIDs")

    def test_import_unexpired_entry_does_not_expire(self):
        # Fix #8: Unexpired entry in B should remain unexpired in A
        entry_b = self.kp_b.add_entry(
            self.kp_b.root_group,
            title="ActiveService",
            username="user2",
            password="pwd"
        )
        self.assertFalse(entry_b.expires)
        self.kp_b.save()

        comparator = Comparator(self.kp_a, self.kp_b)
        diffs = comparator.compare()
        self.assertEqual(diffs[0].state, "ONLY_IN_B")

        merger = Merger(self.kp_a, self.kp_b)
        merger.apply_resolution(diffs[0], "IMPORT_B")
        self.kp_a.save()

        reloaded_a = PyKeePass(self.path_a, password=self.password)
        entry_a = reloaded_a.find_entries(title="ActiveService", first=True)
        self.assertIsNotNone(entry_a)
        self.assertFalse(entry_a.expires, "Imported entry should NOT have expires=True")
        self.assertFalse(entry_a.expired, "Imported entry should not be expired")

    def test_import_preserves_history(self):
        # Fix #16: History should be preserved when imported
        entry_b = self.kp_b.add_entry(
            self.kp_b.root_group,
            title="HistoryService",
            username="user_v1",
            password="pwd"
        )
        entry_b.save_history()
        entry_b.username = "user_v2"
        entry_b.save_history()
        entry_b.username = "user_v3"
        self.kp_b.save()

        self.assertEqual(len(entry_b.history), 2)

        comparator = Comparator(self.kp_a, self.kp_b)
        diffs = comparator.compare()
        merger = Merger(self.kp_a, self.kp_b)
        merger.apply_resolution(diffs[0], "IMPORT_B")
        self.kp_a.save()

        reloaded_a = PyKeePass(self.path_a, password=self.password)
        entry_a = reloaded_a.find_entries(title="HistoryService", first=True)
        self.assertIsNotNone(entry_a)
        self.assertEqual(len(entry_a.history), 2)
        self.assertEqual(entry_a.history[0].username, "user_v1")
        self.assertEqual(entry_a.history[1].username, "user_v2")

    def test_update_fields_saves_history(self):
        entry_a = self.kp_a.add_entry(
            self.kp_a.root_group,
            title="SharedService",
            username="old_user",
            password="old_password"
        )
        self.kp_a.save()

        # Copy to B and change
        shutil.copy2(self.path_a, self.path_b)
        reloaded_b = PyKeePass(self.path_b, password=self.password)
        entry_b = reloaded_b.find_entries(title="SharedService", first=True)
        entry_b.password = "new_secret_password"
        reloaded_b.save()

        reloaded_a = PyKeePass(self.path_a, password=self.password)
        entry_a_loaded = reloaded_a.find_entries(title="SharedService", first=True)
        self.assertEqual(len(entry_a_loaded.history), 0)

        comparator = Comparator(reloaded_a, reloaded_b)
        diffs = comparator.compare()
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].state, "MODIFIED")

        merger = Merger(reloaded_a, reloaded_b)
        merger.apply_resolution(diffs[0], "B")
        reloaded_a.save()

        # Check that A has the new password AND history of old password
        verified_a = PyKeePass(self.path_a, password=self.password)
        target = verified_a.find_entries(title="SharedService", first=True)
        self.assertEqual(target.password, "new_secret_password")
        self.assertEqual(len(target.history), 1)
        self.assertEqual(target.history[0].password, "old_password")

    def test_force_creation_prevents_duplicate_title_crash(self):
        # Fix #16: If an entry with same title already exists in destination group,
        # import does not raise an exception
        self.kp_a.add_entry(self.kp_a.root_group, "DuplicateName", "user1", "pass1")
        self.kp_a.save()

        entry_b = self.kp_b.add_entry(self.kp_b.root_group, "DuplicateName", "user1", "pass2")
        self.kp_b.save()

        comparator = Comparator(self.kp_a, self.kp_b)
        diffs = comparator.compare()
        # Find ONLY_IN_B diff
        diff_b = [d for d in diffs if d.state == "ONLY_IN_B"][0]

        merger = Merger(self.kp_a, self.kp_b)
        # Should NOT raise an exception
        merger.apply_resolution(diff_b, "IMPORT_B")
        self.kp_a.save()

    def test_config_manager_mru(self):
        from storage.config_manager import ConfigManager
        cm = ConfigManager()
        # Override file path to temp directory
        cm.config_file = os.path.join(self.test_dir, "test_mru.json")
        cm.data_dir = self.test_dir

        self.assertIsNone(cm.get_last_directory())
        self.assertEqual(cm.get_mru_paths(), [])

        # Add path A
        cm.add_mru_path(self.path_a)
        self.assertEqual(cm.get_mru_paths(), [self.path_a])
        self.assertEqual(cm.get_last_directory(), self.test_dir)

        # Add path B
        cm.add_mru_path(self.path_b)
        self.assertEqual(cm.get_mru_paths(), [self.path_b, self.path_a])

        # Add path A again (should move to top)
        cm.add_mru_path(self.path_a)
        self.assertEqual(cm.get_mru_paths(), [self.path_a, self.path_b])

if __name__ == "__main__":
    unittest.main()

import os
import shutil
from pykeepass import create_database, PyKeePass

def generate_dbs():
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_a = os.path.join(base_dir, "db_a.kdbx")
    path_b = os.path.join(base_dir, "db_b.kdbx")
    password = "password"

    # --- Create Database A (Source) ---
    if os.path.exists(path_a):
        os.remove(path_a)
    
    kp_a = create_database(path_a, password=password)
    
    # Groups
    group_internet = kp_a.add_group(kp_a.root_group, "Internet")
    group_work = kp_a.add_group(kp_a.root_group, "Work")
    
    # Entries A
    kp_a.add_entry(group_internet, "Google", "my_email@gmail.com", "secure_pass_123", url="https://google.com", notes="Primary email")
    kp_a.add_entry(group_internet, "Facebook", "fb_user", "social_pass_456", url="https://facebook.com")
    kp_a.add_entry(group_work, "Slack", "worker_bee", "slack_pass_789", url="https://slack.com", notes="Work workspace")
    kp_a.add_entry(group_work, "Jira", "dev_lead", "jira_ticket_1", url="https://jira.atlassian.com")
    
    kp_a.save()
    print(f"Created Database A at {path_a} (Password: '{password}')")

    # --- Create Database B (Clone of A + Modifications) ---
    # Copy A to B so UUIDs match
    if os.path.exists(path_b):
        os.remove(path_b)
    shutil.copy2(path_a, path_b)
    
    kp_b = PyKeePass(path_b, password=password)
    
    # Helper to find entry by title (since we want to edit specific ones)
    def find_entry(title):
        return kp_b.find_entries(title=title, first=True)

    # 1. Google: MODIFIED (Changed Password)
    google = find_entry("Google")
    if google:
        google.password = "NEW_UPDATED_PASS_999"
    
    # 2. Facebook: IDENTICAL (Do nothing)
    
    # 3. Slack: REMOVED (Exists in A, but delete from B)
    slack = find_entry("Slack")
    if slack:
        kp_b.delete_entry(slack)

    # 4. Jira: MODIFIED (Changed Username)
    jira = find_entry("Jira")
    if jira:
        jira.username = "product_manager"

    # 5. Twitter: ADDED (Only in B)
    # Need to get group ref in B (references are different objects even if same UUID, usually need to re-find)
    # but PyKeePass groups can be found by name/path
    group_internet_b = kp_b.find_groups(name="Internet", first=True)
    kp_b.add_entry(group_internet_b, "Twitter", "tweeter_dummy", "tweet_pass_xyz", url="https://twitter.com", notes="New account")
    
    kp_b.save()
    print(f"Created Database B at {path_b} (Modified version of A)")

if __name__ == "__main__":
    generate_dbs()

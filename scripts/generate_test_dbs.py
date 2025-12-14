import os
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

    # --- Create Database B (Target/Modified) ---
    if os.path.exists(path_b):
        os.remove(path_b)
        
    kp_b = create_database(path_b, password=password)
    
    # Recreate structure for B
    group_internet_b = kp_b.add_group(kp_b.root_group, "Internet")
    group_work_b = kp_b.add_group(kp_b.root_group, "Work")
    
    # Entries B
    
    # 1. Google: MODIFIED (Changed Password)
    kp_b.add_entry(group_internet_b, "Google", "my_email@gmail.com", "NEW_UPDATED_PASS_999", url="https://google.com", notes="Primary email")
    
    # 2. Facebook: IDENTICAL
    kp_b.add_entry(group_internet_b, "Facebook", "fb_user", "social_pass_456", url="https://facebook.com")
    
    # 3. Slack: REMOVED (Exists in A, but not in B)
    # (Do nothing)

    # 4. Jira: MODIFIED (Changed Username)
    kp_b.add_entry(group_work_b, "Jira", "product_manager", "jira_ticket_1", url="https://jira.atlassian.com")

    # 5. Twitter: ADDED (Only in B)
    kp_b.add_entry(group_internet_b, "Twitter", "tweeter_dummy", "tweet_pass_xyz", url="https://twitter.com", notes="New account")
    
    kp_b.save()
    print(f"Created Database B at {path_b} (Password: '{password}')")

if __name__ == "__main__":
    generate_dbs()

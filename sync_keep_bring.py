import os
import logging
import gkeepapi
from bring_api import Bring, BringItem

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Environment variables
GOOGLE_EMAIL = os.getenv("GOOGLE_EMAIL")
KEEP_LIST_ID = os.getenv("KEEP_LIST_ID")  # Google Keep ID already set
BRING_EMAIL = os.getenv("BRING_EMAIL")
BRING_PASSWORD = os.getenv("BRING_PASSWORD")
BRING_LIST_UUID = os.getenv("BRING_LIST_UUID")  # from GitHub secret

# Sync mode: 0 = both, 1 = Keep -> Bring, 2 = Bring -> Keep
SYNC_MODE = int(os.getenv("SYNC_MODE", 0))


# --- KEEP FUNCTIONS ---

def login_keep(email, password):
    keep = gkeepapi.Keep()
    try:
        if keep.login(email, password):
            logging.info("Logged in to Google Keep")
            return keep
    except Exception as e:
        logging.error(f"Google Keep login failed: {e}")
    return None


def get_keep_list(keep, list_id):
    try:
        note = keep.get(list_id)
        if isinstance(note, gkeepapi.node.List):
            logging.info(f"Fetched Google Keep list: {note.title} ({list_id})")
            return note
        else:
            logging.error(f"Item with ID {list_id} is not a list.")
    except Exception as e:
        logging.error(f"Error fetching Keep list: {e}")
    return None


# --- BRING FUNCTIONS ---

def login_bring(email, password):
    try:
        bring = Bring(email, password)
        logging.info("Logged in to Bring")
        return bring
    except Exception as e:
        logging.error(f"Bring login failed: {e}")
    return None


def get_bring_items(bring, list_uuid):
    try:
        logging.info(f"Fetching Bring items for list UUID: {list_uuid}")
        return bring.getItems(list_uuid)
    except Exception as e:
        logging.error(f"Error fetching Bring list: {e}")
        return None


# --- SYNC FUNCTIONS ---

def sync_keep_to_bring(keep, keep_list, bring, bring_list_uuid):
    keep_items = [item.text for item in keep_list.items if not item.checked]
    bring_items = bring.getItems(bring_list_uuid)
    bring_item_names = [i["name"] for i in bring_items["purchase"]]

    for item in keep_items:
        if item not in bring_item_names:
            logging.info(f"Adding '{item}' to Bring")
            bring.saveItem(bring_list_uuid, BringItem(item))


def sync_bring_to_keep(keep, keep_list, bring_items):
    keep_items = [item.text for item in keep_list.items if not item.checked]
    bring_item_names = [i["name"] for i in bring_items["purchase"]]

    for item in bring_item_names:
        if item not in keep_items:
            logging.info(f"Adding '{item}' to Google Keep")
            keep_list.add(item)
    keep.sync()


# --- MAIN ---

def main():
    # Log into both services
    keep = login_keep(GOOGLE_EMAIL, os.getenv("GOOGLE_PASSWORD"))
    bring = login_bring(BRING_EMAIL, BRING_PASSWORD)

    if not keep or not bring:
        logging.error("Login failed. Exiting.")
        return

    # Fetch Keep list
    keep_list = get_keep_list(keep, KEEP_LIST_ID)
    if not keep_list:
        logging.error("Google Keep list not found. Exiting.")
        return

    # Fetch Bring items (using explicit UUID)
    bring_items = get_bring_items(bring, BRING_LIST_UUID)
    if not bring_items:
        logging.error("Bring list not found. Exiting.")
        return

    # Perform sync
    if SYNC_MODE in [0, 1]:
        sync_keep_to_bring(keep, keep_list, bring, BRING_LIST_UUID)
    if SYNC_MODE in [0, 2]:
        sync_bring_to_keep(keep, keep_list, bring_items)


if __name__ == "__main__":
    main()




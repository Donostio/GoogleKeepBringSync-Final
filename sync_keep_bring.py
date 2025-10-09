import os
import logging
import asyncio
import aiohttp
import gkeepapi
from python_bring_api.bring import Bring


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Environment variables
GOOGLE_EMAIL = os.getenv("GOOGLE_EMAIL")
GOOGLE_PASSWORD = os.getenv("GOOGLE_PASSWORD")
GOOGLE_MASTER_TOKEN = os.getenv("GOOGLE_MASTER_TOKEN")
KEEP_LIST_ID = os.getenv("KEEP_LIST_ID")  # Google Keep ID already set
BRING_EMAIL = os.getenv("BRING_EMAIL")
BRING_PASSWORD = os.getenv("BRING_PASSWORD")
BRING_LIST_UUID = os.getenv("BRING_LIST_UUID")  # from GitHub secret


def validate_env_vars():
    required_vars = {
        "GOOGLE_EMAIL": GOOGLE_EMAIL,
        "KEEP_LIST_ID": KEEP_LIST_ID,
        "BRING_EMAIL": BRING_EMAIL,
        "BRING_PASSWORD": BRING_PASSWORD,
        "BRING_LIST_UUID": BRING_LIST_UUID,
    }

    missing = [name for name, value in required_vars.items() if not value]
    if missing:
        logging.error(
            "Missing required environment variables: %s",
            ", ".join(missing),
        )
        return False

    if not GOOGLE_PASSWORD and not GOOGLE_MASTER_TOKEN:
        logging.error(
            "Provide either GOOGLE_PASSWORD or GOOGLE_MASTER_TOKEN for Google Keep authentication."
        )
        return False
    return True

# Sync mode: 0 = both, 1 = Keep -> Bring, 2 = Bring -> Keep
SYNC_MODE = int(os.getenv("SYNC_MODE", 0))


# --- KEEP FUNCTIONS ---

def login_keep(email, password=None, master_token=None):
    keep = gkeepapi.Keep()
    try:
        if master_token:
            keep.resume(email, master_token)
            logging.info("Resumed Google Keep session using master token")
            return keep

        if password and keep.login(email, password):
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

async def login_bring(session, email, password):
    try:
        bring = Bring(email, password, sessionAsync=session)
        await bring.loginAsync()
        await bring.loadListsAsync()
        logging.info("Logged in to Bring")
        return bring
    except Exception as e:
        logging.error(f"Bring login failed: {e}")
    return None


async def get_bring_items(bring, list_uuid):
    try:
        logging.info(f"Fetching Bring items for list UUID: {list_uuid}")
        return await bring.getItemsAsync(list_uuid)
    except Exception as e:
        logging.error(f"Error fetching Bring list: {e}")
        return None


# --- SYNC FUNCTIONS ---

async def sync_keep_to_bring(keep, keep_list, bring, bring_list_uuid):
    keep_items = [item.text for item in keep_list.items if not item.checked]
    bring_items = await get_bring_items(bring, bring_list_uuid)
    if not bring_items:
        logging.error("Unable to read Bring list, skipping Keep -> Bring sync")
        return

    bring_item_names = [i["name"] for i in bring_items["purchase"]]

    added_count = 0
    for item in keep_items:
        if item not in bring_item_names:
            logging.info(f"Adding '{item}' to Bring")
            await bring.saveItemAsync(bring_list_uuid, item)
            added_count += 1

    if added_count:
        logging.info("Added %d items to Bring", added_count)
    else:
        logging.info("Bring list already up to date with Google Keep")


def sync_bring_to_keep(keep, keep_list, bring_items):
    keep_items = [item.text for item in keep_list.items if not item.checked]
    bring_item_names = [i["name"] for i in bring_items["purchase"]]

    added_count = 0
    for item in bring_item_names:
        if item not in keep_items:
            logging.info(f"Adding '{item}' to Google Keep")
            keep_list.add(item)
            added_count += 1

    if added_count:
        logging.info("Added %d items to Google Keep", added_count)
    else:
        logging.info("Google Keep list already up to date with Bring")

    keep.sync()


# --- MAIN ---

async def main_async():
    if not validate_env_vars():
        return

    # Log into both services
    keep = login_keep(GOOGLE_EMAIL, GOOGLE_PASSWORD, GOOGLE_MASTER_TOKEN)

    async with aiohttp.ClientSession() as session:
        bring = await login_bring(session, BRING_EMAIL, BRING_PASSWORD)

        if not keep or not bring:
            logging.error("Login failed. Exiting.")
            return

        # Fetch Keep list
        keep_list = get_keep_list(keep, KEEP_LIST_ID)
        if not keep_list:
            logging.error("Google Keep list not found. Exiting.")
            return

        bring_items = None

        # Perform sync
        if SYNC_MODE in [0, 1]:
            await sync_keep_to_bring(keep, keep_list, bring, BRING_LIST_UUID)

        if SYNC_MODE in [0, 2]:
            if SYNC_MODE == 0 or bring_items is None:
                bring_items = await get_bring_items(bring, BRING_LIST_UUID)
                if not bring_items:
                    logging.error("Bring list not found. Exiting.")
                    return

            sync_bring_to_keep(keep, keep_list, bring_items)

def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

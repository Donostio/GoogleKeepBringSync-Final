import os
import logging
from gkeepapi import Keep
from gkeepapi.node import List
from python_bring_api.bring import Bring

# Enable debug logging for the GitHub Actions runner
# This must be done in the workflow file, not here.
# For now, we will use INFO level for our script.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_keep_list(keep, list_id):
    """Retrieves the Google Keep list by its ID."""
    try:
        keep.sync()
        note = keep.get(list_id)
        if not note:
            logging.error("Google Keep note not found.")
            return None
        
        if not isinstance(note, List):
            logging.error("Google Keep ID is for a Note, not a List.")
            return None
            
        logging.info(f"Found {len(note.items)} items in Google Keep list.")
        return note
    except Exception as e:
        logging.error(f"Error getting Google Keep list: {e}")
        return None

def get_bring_list(bring, list_name=None):
    """Retrieves the Bring! list, either by name or the first one found."""
    try:
        response = bring.loadLists()
        if not isinstance(response, dict) or 'lists' not in response:
            logging.error("Bring! API returned an invalid response.")
            return None
        
        lists = response['lists']
        bring_list = None
        
        if list_name:
            for l in lists:
                if l.get('name') == list_name:
                    bring_list = l
                    break
        elif lists:
            bring_list = lists[0]
        
        if not bring_list:
            logging.error(f"Bring! list '{list_name}' not found.")
            return None

        return bring.getItems(bring_list.get('listUuid'))
    except Exception as e:
        logging.error(f"Error getting Bring! list: {e}")
        return None

def log_item_status(item_text, normalized_name, is_checked, exists_in_bring):
    """Logs the detailed status of each item for debugging."""
    logging.info(f"Processing Item: '{item_text.strip()}'")
    logging.info(f"    Normalized Name: '{normalized_name}'")
    logging.info(f"    IS CHECKED: {is_checked}")
    logging.info(f"    EXISTS IN BRING!: {exists_in_bring}")
    
    if not is_checked and not exists_in_bring:
        logging.info("    -> Condition met: Will attempt to add to Bring!")
    elif is_checked:
        logging.info("    -> Condition not met: Item is checked in Keep.")
    elif exists_in_bring:
        logging.info("    -> Condition not met: Item already exists in Bring!.")
    else:
        logging.info("    -> Condition not met: Item name is blank or invalid.")

def sync_lists(keep_client, keep_list, bring_items, bring_client, sync_mode):
    """Performs the synchronization logic between the two lists."""
    logging.info(f"Starting sync in mode: {sync_mode}")
    
    normalized_keep_items_dict = {
        ''.join(char for char in item.text.strip().lower() if char.isalnum()): item
        for item in keep_list.items
    }
    
    logging.info(f"Normalized Keep Items: {list(normalized_keep_items_dict.keys())}")
    
    normalized_bring_item_names = {
        ''.join(char for char in item.get('name', '').strip().lower() if char.isalnum())
        for item in bring_items.get('purchase', []) if item.get('name')
    }

    if sync_mode in [0, 2]:
        bring_list_id = bring_items.get('listUuid')
        if bring_list_id:
            for normalized_name, item_obj in normalized_keep_items_dict.items():
                
                # Use the new logging function for clarity
                is_checked = item_obj.checked
                exists_in_bring = normalized_name in normalized_bring_item_names
                log_item_status(item_obj.text, normalized_name, is_checked, exists_in_bring)
                
                if normalized_name and not is_checked and not exists_in_bring:
                    try:
                        bring_client.saveItem(bring_list_id, item_obj.text.strip())
                        logging.info(f"✅ Added '{item_obj.text.strip()}' to Bring!")
                    except Exception as e:
                        logging.warning(f"⚠️ Could not add '{item_obj.text.strip()}' to Bring!: {e}")

    if sync_mode in [0, 1]:
        for item in bring_items['purchase']:
            item_spec = item.get('name', '').strip()
            normalized_spec = ''.join(char for char in item_spec.lower() if char.isalnum())
            if item_spec and normalized_spec not in normalized_keep_items_dict:
                try:
                    keep_list.add(item_spec)
                    keep_client.sync()
                    logging.info(f"✅ Added '{item_spec}' to Google Keep")
                except Exception as e:
                    logging.warning(f"⚠️ Could not add '{item_spec}' to Google Keep: {e}")

    logging.info("Sync complete.")

def main():
    """Main function to handle authentication and initiate the sync."""
    google_email = os.environ.get('GOOGLE_EMAIL')
    keep_list_id = os.environ.get('KEEP_LIST_ID')
    bring_email = os.environ.get('BRING_EMAIL')
    bring_password = os.environ.get('BRING_PASSWORD')
    google_token = os.environ.get('GOOGLE_TOKEN') or open('token.txt').read().strip()

    sync_mode = int(os.environ.get('SYNC_MODE', 0))
    bring_list_name = os.environ.get('BRING_LIST_NAME')

    keep = Keep()
    try:
        logging.info("Logging into Google Keep...")
        keep.authenticate(google_email, google_token)
        logging.info("Google Keep login successful.")
    except Exception as e:
        logging.error(f"Failed to log into Google Keep: {e}")
        return

    bring = Bring(bring_email, bring_password)
    try:
        logging.info("Logging into Bring!...")
        bring.login()
        logging.info("Bring! login successful.")
    except Exception as e:
        logging.error(f"Failed to log into Bring!: {e}")
        return
    
    keep_list = get_keep_list(keep, keep_list_id)
    bring_items = get_bring_list(bring, bring_list_name)
    
    if keep_list and bring_items:
        sync_lists(keep, keep_list, bring_items, bring, sync_mode)
    
if __name__ == "__main__":
    main()

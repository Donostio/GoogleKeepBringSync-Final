import os
import logging
import json
from python_bring_api.bring import Bring

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main function to test Bring! API calls."""
    bring_email = os.environ.get('BRING_EMAIL')
    bring_password = os.environ.get('BRING_PASSWORD')
    bring_list_uuid = os.environ.get('BRING_LIST_UUID')  # from secret

    # Authentication with Bring!
    bring = Bring(bring_email, bring_password)
    try:
        logging.info("Logging into Bring!...")
        bring.login()
        logging.info("Bring! login successful.")
    except Exception as e:
        logging.error(f"Failed to log into Bring!: {e}")
        return
    
    # Test 1: Get all lists
    logging.info("\n--- Getting all lists ---")
    try:
        response = bring.loadLists()
        logging.info("Raw response from bring.loadLists():\n%s", json.dumps(response, indent=2))

        # Test 2: Use explicit UUID from secret
        if bring_list_uuid:
            logging.info(f"\n--- Getting items from UUID: {bring_list_uuid} ---")
            items_response = bring.getItems(bring_list_uuid)
            logging.info("Raw response from getItems for SHOPPING UUID:\n%s", json.dumps(items_response, indent=2))
        else:
            logging.warning("No BRING_LIST_UUID provided in environment!")

    except Exception as e:
        logging.error(f"Error while fetching Bring! data: {e}")

if __name__ == "__main__":
    main()

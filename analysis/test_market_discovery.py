
import json
import sys
import os

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_discovery import fetch_all_markets

def inspect_market_structure():
    """
    Fetches all markets, then prints the keys and the full structure
    of the first market object to understand its data structure.
    """
    print("--- Market Structure Inspection ---")
    
    response = fetch_all_markets()
    
    if not response:
        print("Could not fetch any markets. Please check connection and polymarket_client.")
        return

    print(f"\n[INFO] Type of the response from fetch_all_markets: {type(response)}")

    if isinstance(response, dict):
        print("\n[INFO] Keys in the response dictionary:")
        print("------------------------------------")
        for key in response.keys():
            print(f"- {key}")

        # Assuming the list of markets is in a key, e.g., 'data' or 'results'
        # Let's find the key that contains a list
        market_list = []
        for key, value in response.items():
            if isinstance(value, list) and value:
                market_list = value
                print(f"\n[INFO] Found a list of markets under the key: '{key}'")
                break
    elif isinstance(response, list):
        market_list = response
    else:
        print("\n[ERROR] Response is not a dictionary or a list. Cannot proceed.")
        print(response)
        return

    if not market_list:
        print("\n[WARNING] Could not find a list of markets in the response.")
        print("\n[INFO] Full response structure:")
        print("------------------------------")
        print(json.dumps(response, indent=2))
        return

    # Get the first market object
    first_market = market_list[0]
    
    print("\n[INFO] Keys available in the first market object:")
    print("------------------------------------------------")
    if isinstance(first_market, dict):
        for key in first_market.keys():
            print(f"- {key}")
    else:
        for attr in dir(first_market):
            if not attr.startswith('_'):
                print(f"- {attr}")

    print("\n[INFO] Full JSON structure of the first market:")
    print("-----------------------------------------------")
    print(json.dumps(first_market, indent=2))
        
    print("\n--- Inspection Complete ---")

if __name__ == "__main__":
    inspect_market_structure()

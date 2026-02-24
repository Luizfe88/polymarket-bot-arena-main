
import requests
import json

def direct_api_test():
    """
    Performs a direct HTTP GET request to the Polymarket API
    to check its status and response structure.
    """
    print("--- Direct API Request Test ---")
    
    url = "https://clob.polymarket.com/markets"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"Status Code: {response.status_code}")
        
        # Check if the response is successful
        response.raise_for_status()
        
        data = response.json()
        
        print("\n[INFO] Successfully fetched data from the API.")
        
        if isinstance(data, list) and data:
            print(f"Response is a list with {len(data)} items.")
            first_item = data[0]
            print("\n[INFO] Keys of the first item:")
            for key in first_item.keys():
                print(f"- {key}")
            
            print("\n[INFO] Full structure of the first item:")
            print(json.dumps(first_item, indent=2))
            
        elif isinstance(data, dict):
            print("Response is a dictionary.")
            print("\n[INFO] Keys in the dictionary:")
            for key in data.keys():
                print(f"- {key}")

            print("\n[INFO] Full response structure:")
            print(json.dumps(data, indent=2))

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] An error occurred during the request: {e}")
    except json.JSONDecodeError:
        print("\n[ERROR] Failed to decode JSON from the response.")
        print("Response content:")
        print(response.text)

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    direct_api_test()

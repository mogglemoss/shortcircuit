import asyncio
import httpx
import sys

# Replicate the User-Agent from the app
USER_AGENT = 'Short Circuit v1.1.0 (Debug); @SecondFry, secondfry@gmail.com'

async def debug_login(url, username, password):
    url = url.rstrip('/')
    login_url = f'{url}/login.php'
    
    print(f"Target URL: {login_url}")
    print(f"Username: {username}")
    
    headers = {
        'Referer': login_url,
        'User-Agent': USER_AGENT,
    }
    
    async with httpx.AsyncClient(verify=True) as client:
        print("\n--- Step 1: Initial GET request (Session Setup) ---")
        try:
            response = await client.get(login_url, headers=headers, follow_redirects=True)
            print(f"Status: {response.status_code}")
            print(f"Final URL: {response.url}")
            print(f"Cookies: {dict(client.cookies)}")
        except Exception as e:
            print(f"GET failed: {e}")
            return

        print("\n--- Step 2: POST login request ---")
        payload = {
            'username': username,
            'password': password,
            'mode': 'login',
        }
        
        try:
            response = await client.post(
                login_url,
                data=payload,
                headers=headers,
                follow_redirects=True,
            )
            print(f"Status: {response.status_code}")
            print(f"Final URL: {response.url}")
            print(f"Cookies: {dict(client.cookies)}")
            
            if 'login.php' in str(response.url):
                print("\n[FAILURE] Redirected back to login page.")
                print("Possible causes: Invalid credentials, missing CSRF token, or server rejected session.")
            elif 'name="password"' in response.text.lower():
                print("\n[FAILURE] Password field found in response (Login page).")
            else:
                print("\n[SUCCESS] Seems to have logged in!")
                
            # Print a snippet of the body to see if there are error messages
            print("\n--- Response Body Snippet ---")
            print(response.text[:500])
            
        except Exception as e:
            print(f"POST failed: {e}")
            return

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python debug_connection.py <url> <username> <password>")
        sys.exit(1)
        
    asyncio.run(debug_login(sys.argv[1], sys.argv[2], sys.argv[3]))


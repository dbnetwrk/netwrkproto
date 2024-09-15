from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def scrape_menu():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set headless=True for production
        page = browser.new_page()

        # Navigate to the search results page
        page.goto("https://www.google.com/search?q=Moxies+Miami")

        # Try to close the pop-up if it appears
        try:
            not_now_button = page.locator("text='Not now'").first
            not_now_button.click(timeout=5000)  # Wait up to 5 seconds for the button to be clickable
        except PlaywrightTimeoutError:
            print("Pop-up not found or couldn't be closed. Proceeding anyway.")

        # Find and click the menu button using jsname and text content
        try:
            menu_button = (page.locator("[data-id='menu-viewer-entrypoint'] span:has-text('Menu')").first)
            #menu_button = (page.locator("[jsname='UXbvIb'] span:has-text('Menu')").first)
            menu_button.click(timeout=5000)
        except PlaywrightTimeoutError:
            print("Couldn't find or click the Menu button. The page might have changed.")
            browser.close()
            return

        # Wait for menu items to load
        try:
            page.wait_for_selector("[data-menu-item-id]", timeout=10000)  # Wait up to 10 seconds
        except PlaywrightTimeoutError:
            print("Menu items didn't load in time. The page structure might have changed.")
            browser.close()
            return

        # Extract menu items
        menu_items = page.query_selector_all("[data-menu-item-id]")

        # Parse each menu item
        for item in menu_items:
            # Use text content of the entire item, then split it to get name and price
            full_text = item.inner_text()
            # Assuming the price is always at the end, separated by a space
            parts = full_text.rsplit(' ', 1)
            
            if len(parts) == 2:
                name, price = parts
            else:
                name = full_text
                price = "N/A"
            
            print(f"{name.strip()} {price.strip()}")

        browser.close()

if __name__ == "__main__":
    scrape_menu()
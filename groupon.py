from playwright.sync_api import sync_playwright
import time

def scrape_groupon(url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)  # Visible browser
        page = browser.new_page()
        page.goto(url, wait_until='domcontentloaded')
        # Wait a few seconds to let additional resources load
        page.wait_for_timeout(15000)  # Initial wait for content

        # Incremental scrolling
        step_size = 1000  # Scroll step size
        attempts = 0  # to avoid infinite loops

        while True:
            last_height = page.evaluate("document.body.scrollHeight")
            page.evaluate(f"window.scrollBy(0, {step_size})")
            # Wait for network to be idle or a maximum of 5 seconds after each scroll
            try:
                page.wait_for_timeout(15000)
            except:
                # Timeout implies no significant network activity after 5 seconds
                pass
            new_height = page.evaluate("document.body.scrollHeight")
            
            # Stop if no new content is loaded or if we have tried too many times
            if new_height == last_height or attempts > 10:
                break
            attempts += 1

        # Extract links
        links = page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('div[data-item-type="card"] a').forEach(link => {
                    links.push(link.href);
                });
                return links;
            }
        """)

        # Save HTML content
        html_content = page.content()
        with open('groupon.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

        browser.close()
        return list(set(links))

if __name__ == '__main__':
    url = "https://www.groupon.com/local/miami/food-and-drink"  # Replace with the specific Groupon page URL if needed
    links = scrape_groupon(url)
    print("Extracted links:")
    for link in links:
        print(link)
    print("\nScraping completed. Check groupon.html for the page content.")
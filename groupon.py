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

        while attempts < 2:
            last_height = page.evaluate("document.body.scrollHeight")
            page.evaluate(f"window.scrollBy(0, {step_size})")
            # Wait for network to be idle or a maximum of 5 seconds after each scroll
            try:
                page.wait_for_timeout(10000)
            except:
                # Timeout implies no significant network activity after 5 seconds
                pass
            new_height = page.evaluate("document.body.scrollHeight")
            
            attempts += 1

        items = page.evaluate("""
            () => {
                const items = [];
                document.querySelectorAll('div[data-item-type="card"]').forEach(card => {
                    const link = card.querySelector('a');
                    const priceElement = card.querySelector('div[data-testid="green-price"]');
                    if (link && priceElement) {
                        const priceText = priceElement.textContent.trim().replace(/[^0-9.]/g, '');
                        items.push({
                            url: link.href,
                            price: parseFloat(priceText) || null
                        });
                    }
                });
                return items;
            }
        """)
        
        browser.close()
        
        # Now process each item
        content_data = []
        for item in items:
            result = scrape_individual_page(item['url'], playwright)
            result['price'] = item['price']
            content_data.append(result)
        
        return content_data

def scrape_individual_page(url, playwright):
    """Function to scrape individual pages with adaptive title extraction."""
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded')
    
    # Attempt to extract the title in a more flexible manner
    title_element = page.query_selector('h1[data-testid="deal-title"]')
    if not title_element:  # Fallback to a more generic selector if specific one fails
        title_element = page.query_selector('h1')
    
    # Get text content from the selected title element
    title = title_element.text_content() if title_element else "Title Not Found"
    
    # Extract all paragraphs and concatenate them into one description string
    paragraphs = page.query_selector_all('p')  # This gets all paragraph elements
    description = ' '.join(p.text_content().strip() for p in paragraphs if p.text_content().strip())
    
    browser.close()
    
    return {'url': url, 'title': title, 'description': description}



def scrape_eventbrite(url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)  # Visible browser
        page = browser.new_page()
        page.goto(url, wait_until='domcontentloaded')
        # Wait a few seconds to let additional resources load
        page.wait_for_timeout(15000)  # Initial wait for content

        # Incremental scrolling
        step_size = 1000  # Scroll step size
        attempts = 0  # to avoid infinite loops

        while attempts < 2:
            last_height = page.evaluate("document.body.scrollHeight")
            page.evaluate(f"window.scrollBy(0, {step_size})")
            # Wait for network to be idle or a maximum of 5 seconds after each scroll
            try:
                page.wait_for_timeout(10000)
            except:
                # Timeout implies no significant network activity after 5 seconds
                pass
            new_height = page.evaluate("document.body.scrollHeight")
            
            attempts += 1
        
        # Extract links
        links = page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('a.event-card-link').forEach(link => {
                    links.push(link.href);
                });
                return links;
            }
        """)
        browser.close()
        content_data = []
        for link in set(links):
            content_data.append(scrape_individual_eventbrite_page(link, playwright))
        return content_data

def scrape_individual_eventbrite_page(url, playwright):
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded')
    
    title_element = page.query_selector('h1.event-title')
    title = title_element.text_content() if title_element else "Title Not Found"
    
    date_element = page.query_selector('time.start-date')
    date = date_element.get_attribute('datetime') if date_element else None
    
    paragraphs = page.query_selector_all('p')
    description = ' '.join(p.text_content().strip() for p in paragraphs if p.text_content().strip())
    
    browser.close()
    
    return {'url': url, 'title': title, 'description': description, 'event_date': date}



def scrape_eventbrite2(url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)  # Visible browser
        page = browser.new_page()
        page.goto(url, wait_until='domcontentloaded')
        page.wait_for_timeout(10000)  # Initial wait for content

        # Scroll down the page in chunks
        viewport_height = page.viewport_size['height']
        scroll_step = viewport_height * 0.8  # Scroll 80% of the viewport height each time
        last_height = 0
        while True:
            last_height = page.evaluate("document.body.scrollHeight")

            # Scroll down by one step
            page.evaluate(f"window.scrollBy(0, {scroll_step})")
            page.wait_for_timeout(3000)  # Wait for content to load

            # Check if we've reached the bottom
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                # If no new content loaded, try scrolling to the very bottom
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)
                final_height = page.evaluate("document.body.scrollHeight")
                if final_height == new_height:
                    # If still no change, we've reached the bottom
                    break

            

        # Extract links
        links = page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('a.event-card-link').forEach(link => {
                    links.push(link.href);
                });
                return links;
            }
        """)
        browser.close()
        return list(set(links))


if __name__ == '__main__':
    #url = "https://www.groupon.com/local/miami/things-to-do?distance=%5B0..10%5D"  # Replace with the specific Groupon page URL if needed
    #links = scrape_groupon(url)

    url = "https://www.eventbrite.com/b/fl--miami/business/startups-and-small-business/"  # Replace with the specific Groupon page URL if needed
    links = scrape_eventbrite(url)

    print("Extracted links:")
    for link in links:
        print(link)

    print(" We got this many: ", len(links))
    print("\nScraping completed. Check groupon.html for the page content.")

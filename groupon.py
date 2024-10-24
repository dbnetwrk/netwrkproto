from playwright.sync_api import sync_playwright
import time
from datetime import datetime, timedelta
import re

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



def scrape_miami_general(url):
    all_links = set()
    
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        
        while url:
            page.goto(url, wait_until='domcontentloaded')
            
            # Extract links from the current page
            new_links = page.evaluate("""
                () => {
                    const links = [];
                    document.querySelectorAll('article.ys-card[data-type="event"] a').forEach(link => {
                        links.push(link.href);
                    });
                    return links;
                }
            """)
            all_links.update(new_links)
            
            # Check for the next page
            next_button = page.query_selector('li.ys-pagination__item:not(.pagination-disabled) a[aria-label="Next"]')
            if next_button:
                url = next_button.get_attribute('href')
                if url and not url.startswith('http'):
                    # If it's a relative URL, make it absolute
                    url = f"https://www.miamiandbeaches.com{url}"
            else:
                url = None  # No more pages to scrape
        
        browser.close()
    
        content_data = []
        for link in all_links:
            content_data.append(scrape_individual_miami_beaches_page(link, playwright))
        return content_data


def scrape_individual_miami_beaches_page(url, playwright):
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(url, wait_until='domcontentloaded')
    
    # Extract title
    title_element = page.query_selector('h1.h1.text-uppercase')
    title = title_element.text_content().strip() if title_element else "Title Not Found"
    
    # Extract date
    date_element = page.query_selector('h3.date-range')
    date_text = date_element.text_content().strip() if date_element else None
    event_date = parse_date(date_text)
    
    # Extract time
    time_element = page.query_selector('h5.time-frame')
    time = time_element.text_content().strip() if time_element else None
    
    # Extract description
    paragraphs = page.query_selector_all('p')
    description = ' '.join(p.text_content().strip() for p in paragraphs if p.text_content().strip())
    
    browser.close()
    
    return {
        'url': url,
        'title': title,
        'description': description,
        'event_date': event_date,
        'event_time': time
    }

def parse_date(date_text):
    if not date_text:
        return None
    
    # Try to parse a single date
    try:
        return datetime.strptime(date_text, "%b %d, %Y").date()
    except ValueError:
        pass
    
    # Check for date range
    if ' - ' in date_text:
        start_date = date_text.split(' - ')[0]
        try:
            return datetime.strptime(start_date, "%b %d, %Y").date()
        except ValueError:
            pass
    
    # Check for "Through" format
    if date_text.startswith("Through"):
        # Return the date for the coming weekend
        return get_coming_weekend()
    
    # If all else fails, return the coming weekend
    return get_coming_weekend()

def get_coming_weekend():
    today = datetime.now().date()
    days_ahead = 5 - today.weekday()  # Saturday is 5
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return today + timedelta(days=days_ahead)




def scrape_timeout(url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)  # Visible browser
        page = browser.new_page()
        page.goto(url, wait_until='domcontentloaded')
        
        # Wait for initial content to load
        page.wait_for_timeout(5000)

        # Function to click "Show more" button and load more content
        def load_more_content(max_attempts=50):
            for _ in range(max_attempts):
                try:
                    # Try to find and click the "Show more" button
                    show_more_button = page.query_selector('a[data-testID="view-more-cta_testID"]')
                    if show_more_button:
                        show_more_button.click()
                        print("Clicked 'Show more' button")
                        # Wait for new content to load
                        page.wait_for_timeout(15000)
                    else:
                        print("'Show more' button not found. All content loaded.")
                        break
                except Exception as e:
                    print(f"Error clicking 'Show more' button: {e}")
                    break

        # Load more content
        load_more_content()
        
        # Extract event information
        events = page.evaluate("""
            () => {
                const events = [];
                document.querySelectorAll('div.articleContent').forEach(article => {
                    const titleElement = article.querySelector('h3');
                    const title = titleElement ? titleElement.textContent.trim() : 'No Title';
                    
                    
                    const summaryElement = article.querySelector('._summary_1dc5j_23');
                    const summary = summaryElement ? summaryElement.textContent.trim() : 'No Summary';
                    
                    events.push({
                        title: title,
                        summary: summary
                    });
                });
                return events;
            }
        """)
        
        browser.close()
        return events



if __name__ == '__main__':


    url = "https://www.timeout.com/miami/things-to-do/things-to-do-in-miami-this-weekend"
    scraped_events = scrape_timeout(url)
    for event in scraped_events:
        print(event)

    #url = "https://www.groupon.com/local/miami/things-to-do?distance=%5B0..10%5D"  # Replace with the specific Groupon page URL if needed
    #links = scrape_groupon(url)

    #url = "https://www.miamiandbeaches.com/events?dates._datesFilter=week"  # Replace with the specific Groupon page URL if needed
    #links = scrape_miami_general(url)

    #print("Extracted links:")
    #for link in links:
        #print(link)

    #print(" We got this many: ", len(links))
    #print("\nScraping completed. Check groupon.html for the page content.")

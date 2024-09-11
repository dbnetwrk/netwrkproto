from playwright.sync_api import sync_playwright
import time
import re

def run(playwright):
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.eventbrite.com/b/fl--miami/nightlife/?category=this-weekend")

    # Wait for the main content to load
    page.wait_for_selector(".eds-structure__main")

    # Scroll to bottom of page multiple times to trigger lazy loading
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)

    # Extract all links that match the pattern we're looking for
    links = page.evaluate("""
        () => {
            const links = [];
            document.querySelectorAll('a[href*="/e/"][class*="event-card-link"]').forEach(link => {
                links.push(link.href);
            });
            return links;
        }
    """)

    # Print all unique links
    for link in set(links):
        print(link)

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        print("Launching browser in non-headless mode...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "accept-language": "en-US,en;q=0.9",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "referer": "https://www.google.com/"
            }
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        url = "https://www.naukri.com/ai-engineer-fresher-jobs"
        print(f"Navigating to {url}...")
        try:
            response = await page.goto(url, timeout=30000)
            print(f"Response status: {response.status if response else 'No response'}")
            print("Waiting 5 seconds...")
            await page.wait_for_timeout(5000)
            
            # Save screenshot
            screenshot_path = "scratch/naukri_screenshot.png"
            await page.screenshot(path=screenshot_path)
            print(f"Saved screenshot to {screenshot_path}")
            
            # Check for selectors
            elements = await page.locator(".srp-jobtuple-wrapper").all()
            print(f"Found {len(elements)} instances of .srp-jobtuple-wrapper")
            
            # Print page title
            print(f"Page Title: {await page.title()}")
            
        except Exception as e:
            print(f"Failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

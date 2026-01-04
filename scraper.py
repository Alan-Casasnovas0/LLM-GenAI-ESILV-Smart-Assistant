import asyncio
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

LOGIN_URL = "https://learning.devinci.fr"

class DeVinciScraper:
    """Web scraper for De Vinci Moodle platform"""
    
    def __init__(self, page):
        self.page = page

    async def force_summary_view(self):
        """
        Force the courses display mode to 'Summary View' if not already in that mode.
        
        Moodle De Vinci provides multiple display modes for courses. This method ensures
        we're in Summary mode which provides a consistent structure for scraping.
        """
        if not self.page:
            return False
            
        print("🔄 Checking display mode...")
        try:
            # Wait for courses view container to be loaded
            courses_view = self.page.locator('div[data-region="courses-view"]')
            await courses_view.wait_for(state="visible", timeout=10000)

            # Check the current display mode attribute
            current_display = await courses_view.get_attribute("data-display")
            
            if current_display == "summary":
                print("  ✅ Already in summary mode.")
                return True

            # Switch to summary mode if not already there
            print("  -> Switching to summary mode...")
            
            # Click the display dropdown button to open the menu
            dropdown_btn = self.page.locator('button#displaydropdown')
            if await dropdown_btn.count() == 0:
                dropdown_btn = self.page.locator('div.display-style button.dropdown-toggle')
            
            await dropdown_btn.click()
            await asyncio.sleep(0.5)  # Wait for menu animation

            # Click the "Summary" option in the dropdown
            summary_option = self.page.locator('a[data-value="summary"]')
            if await summary_option.count() > 0:
                await summary_option.click()
                
                # Wait for the DOM to update with the new view
                await courses_view.wait_for(state="visible", timeout=10000)
                
                # Verify the display mode changed successfully
                current_display = await courses_view.get_attribute("data-display")
                if current_display == "summary":
                    print("  ✅ Summary mode activated successfully.")
                    return True
                else:
                    print("  ⚠️ Display mode change not detected.")
                    return False
            else:
                print("  ⚠️ Summary option not found in menu.")
                return False

        except Exception as e:
            print(f"  ❌ Error switching to summary view: {e}")
            return False

    async def get_timeline_events(self):
        """
        Extract upcoming deadlines from the timeline section.
        
        Parses the timeline events and formats them into a readable list
        showing dates, times, and assignment names.
        """
        if not self.page:
            return "Error: Scraper not connected"
        
        print("🔍 Extracting timeline events...")
        try:
            timeline_section = self.page.locator('section[data-block="timeline"]')
            await timeline_section.wait_for(state="visible", timeout=10000)
            
            container = timeline_section.locator('div[data-region="event-list-container"]')
            await container.wait_for(state="visible", timeout=10000)

            print("  -> Waiting for content to load...")
            loader = container.locator('div[data-region="event-list-loading-placeholder"]')
            
            # Wait for loading spinner to disappear if present
            if await loader.count() > 0:
                await loader.wait_for(state="hidden", timeout=10000)
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.5)

            # Extract event data using JavaScript for performance
            events_data = await container.evaluate('''(element) => {
                const items = [];
                const eventItems = element.querySelectorAll('.timeline-event-list-item');
                
                eventItems.forEach(item => {
                    try {
                        const nameLink = item.querySelector('h6.event-name a');
                        if (!nameLink) return;
                        
                        const timeEl = item.querySelector('small.text-right');
                        const timeStr = timeEl ? timeEl.innerText.trim() : "";
                        
                        const listGroup = item.closest('.list-group');
                        let dateStr = "Unknown date";
                        
                        if (listGroup && listGroup.previousElementSibling) {
                            const dateHeader = listGroup.previousElementSibling.querySelector('h5');
                            if (dateHeader) {
                                dateStr = dateHeader.innerText.trim();
                            }
                        }

                        items.push({
                            date: dateStr,
                            title: nameLink.innerText.trim(),
                            url: nameLink.href,
                            time: timeStr
                        });
                    } catch (e) {}
                });
                return items;
            }''')

            events = []
            for data in events_data:
                full_date = f"{data['date']} {data['time']}"
                events.append(f"⏰ {full_date} - {data['title']}")

            print(f"✅ Found {len(events)} events.")
            return "\n".join(events) if events else "No deadlines found."

        except Exception as e:
            print(f"❌ Error extracting timeline: {e}")
            return f"Error: {e}"

    async def get_course_list(self):
        """
        Extract the list of courses from Moodle in Summary View.
        
        Switches to summary view mode and extracts course information including:
        - Course name and URL
        - Category
        - Progress if available
        """
        if not self.page:
            return "Error: Scraper not connected"
        
        courses = []
        print("📚 Extracting course list...")

        try:
            overview_section = self.page.locator('section[data-block="myoverviewdevinci"]')
            await overview_section.wait_for(state="visible", timeout=15000)

            # Ensure we're viewing in Summary mode for consistent data structure
            await self.force_summary_view()

            courses_container = overview_section.locator('div[data-region="courses-view"]')
            await courses_container.wait_for(state="visible", timeout=15000)

            # Wait for loading animation to disappear
            print("  -> Waiting for content to load...")
            try:
                await self.page.wait_for_selector('div[data-region="courses-view"] .bg-pulse-grey', state="detached", timeout=15000)
            except Exception:
                pass 

            # Extract course data using JavaScript for performance and DOM traversal
            courses_data = await courses_container.evaluate('''(container) => {
                const items = [];
                // In Summary mode, courses have the class 'course-summaryitem'
                const courseItems = container.querySelectorAll('div.course-summaryitem');
                
                courseItems.forEach(item => {
                    try {
                        // Main course information is in the right column (col-md-9)
                        const colContent = item.querySelector('.col-md-9');
                        if (!colContent) return;

                        // Extract course title and link
                        const nameLink = colContent.querySelector('a.aalink.coursename');
                        const name = nameLink ? nameLink.innerText.trim() : "Unknown";
                        const url = nameLink ? nameLink.href : "#";
                        
                        // Extract course category
                        const catSpan = colContent.querySelector('.categoryname');
                        const category = catSpan ? catSpan.innerText.trim() : "N/A";
                        
                        // Extract course description summary
                        const summaryDiv = colContent.querySelector('.summary');
                        const summary = summaryDiv ? summaryDiv.innerText.trim() : "";

                        // Extract progress if available
                        let progressText = "";
                        const progressDiv = colContent.querySelector('.progress-text span');
                        if (progressDiv) {
                            // Extract percentage completed text
                            const fullText = progressDiv.parentElement.innerText;
                            progressText = fullText.replace('terminé', '').trim();
                        }

                        items.push({
                            name: name,
                            url: url,
                            category: category,
                            summary: summary,
                            progress: progressText
                        });
                    } catch (e) {
                        console.log("Error scraping course item: " + e);
                    }
                });
                return items;
            }''')

            # Format the results for display
            for data in courses_data:
                course_info = f"📚 {data['name']}"
                if data['category'] and data['category'] != "N/A":
                    course_info += f" ({data['category']})"
                
                if data['progress']:
                    course_info += f" - {data['progress']}"
                    
                courses.append(course_info)

            print(f"✅ Retrieved {len(courses)} courses in summary view.")
            return "\n".join(courses) if courses else "No courses found."

        except Exception as e:
            print(f"❌ Error extracting course list: {e}")
            return f"Error: {e}"
        
    async def get_all_courses(self):
        """Get all courses wrapper"""
        return await self.get_course_list()

# Global browser and context state
# These are reused across requests to maintain a persistent session
_browser = None
_context = None
_page = None
_scraper = None
_playwright = None

async def cleanup_browser():
    """
    Close and reset the browser connection.
    
    Called after each tool execution to ensure a fresh start on the next request.
    This prevents broken WebSocket connections and memory leaks.
    """
    global _browser, _context, _page, _scraper, _playwright
    
    try:
        if _page:
            await _page.close()
        if _context:
            await _context.close()
        if _playwright:
            await _playwright.stop()
    except Exception as e:
        logger.error(f"Error cleaning up browser: {e}")
    finally:
        _browser = None
        _context = None
        _page = None
        _scraper = None
        _playwright = None

async def init_browser(email: str = None, password: str = None):
    """
    Initialize Playwright browser and authenticate with De Vinci Moodle.
    
    Creates a persistent browser context that maintains login session across requests.
    If already initialized, returns the existing scraper instance.
    
    Args:
        email: De Vinci email address for login
        password: De Vinci password for login
        
    Returns:
        DeVinciScraper instance if successful, None if credentials missing
    """
    global _browser, _context, _page, _scraper, _playwright
    
    if _scraper is not None:
        return _scraper
    
    try:
        _playwright = await async_playwright().start()
        _context = await _playwright.chromium.launch_persistent_context(
            user_data_dir="playwright_data",
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        _page = await _context.new_page()
        await asyncio.sleep(2)

        print("🔌 Connecting to Moodle...")
        await _page.goto(LOGIN_URL, timeout=30000)
        
        try:
            # Check if already logged in
            if "learning.devinci.fr/my/" not in _page.url:
                if not email or not password:
                    return None
                await _page.fill("input[type='email']", email)
                await _page.fill("input[type='password']", password)
                await asyncio.sleep(0.5)
                await _page.click("#submitButton")
                await _page.wait_for_load_state("networkidle", timeout=20000)
                print("✅ Connection successful.")
            else:
                print("✅ Already logged in.")
        except Exception as e:
            print(f"⚠️ Connection error: {e}")

        _scraper = DeVinciScraper(_page)
        return _scraper
    except Exception as e:
        print(f"❌ Browser initialization error: {e}")
        return None

async def get_courses_async(email: str = None, password: str = None) -> str:
    """
    Get all courses asynchronously.
    
    Initializes browser, logs in, and extracts course list.
    Cleanup happens automatically in the finally block.
    """
    try:
        scraper = await init_browser(email, password)
        if scraper is None:
            return "Please provide De Vinci credentials."
        result = await scraper.get_all_courses()
        return result
    finally:
        # Always cleanup to prevent broken connections on next call
        await cleanup_browser()

async def get_deadlines_async(email: str = None, password: str = None) -> str:
    """
    Get deadlines asynchronously.
    
    Initializes browser, logs in, and extracts upcoming deadlines.
    Cleanup happens automatically in the finally block.
    """
    try:
        scraper = await init_browser(email, password)
        if scraper is None:
            return "Please provide De Vinci credentials."
        result = await scraper.get_timeline_events()
        return result
    finally:
        # Always cleanup to prevent broken connections on next call
        await cleanup_browser()

def get_courses_blocking(email: str = None, password: str = None) -> str:
    """
    Blocking wrapper for get_courses_async.
    
    Creates a new event loop with Windows ProactorEventLoopPolicy support
    and runs the async function to completion.
    """
    try:
        import sys
        # Windows requires ProactorEventLoopPolicy for Playwright subprocess support
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(get_courses_async(email, password))
            return result
        except Exception as e:
            logger.error(f"Get courses error: {e}")
            return f"Error: {e}"
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Get courses error: {e}")
        return f"Error: {e}"

def get_deadlines_blocking(email: str = None, password: str = None) -> str:
    """
    Blocking wrapper for get_deadlines_async.
    
    Creates a new event loop with Windows ProactorEventLoopPolicy support
    and runs the async function to completion.
    """
    try:
        import sys
        # Windows requires ProactorEventLoopPolicy for Playwright subprocess support
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(get_deadlines_async(email, password))
            return result
        except Exception as e:
            logger.error(f"Get deadlines error: {e}")
            return f"Error: {e}"
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Get deadlines error: {e}")
        return f"Error: {e}"
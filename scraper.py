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
        """Force le passage en mode 'Résumé' si ce n'est pas déjà le cas"""
        if not self.page:
            return False
            
        print("🔄 Vérification du mode d'affichage...")
        try:
            # On attend que le conteneur des cours soit là
            courses_view = self.page.locator('div[data-region="courses-view"]')
            await courses_view.wait_for(state="visible", timeout=10000)

            # On regarde l'attribut data-display du conteneur
            current_display = await courses_view.get_attribute("data-display")
            
            if current_display == "summary":
                print("  ✅ Déjà en mode Résumé.")
                return True

            # Sinon, on force le changement
            print("  -> Passage en mode Résumé...")
            
            # 1. Cliquer sur le menu déroulant (Bouton "Afficher par")
            # On cible le bouton avec l'ID displaydropdown ou le dropdown-toggle
            dropdown_btn = self.page.locator('button#displaydropdown')
            if await dropdown_btn.count() == 0:
                dropdown_btn = self.page.locator('div.display-style button.dropdown-toggle')
            
            await dropdown_btn.click()
            await asyncio.sleep(0.5) # Attendre l'ouverture du menu

            # 2. Cliquer sur l'option "Résumé" (data-value="summary")
            summary_option = self.page.locator('a[data-value="summary"]')
            if await summary_option.count() > 0:
                await summary_option.click()
                
                # 3. Attendre que l'attribut data-display passe à "summary"
                # Cela confirme que le DOM a été rechargé avec la nouvelle vue
                await courses_view.wait_for(state="visible", timeout=10000)
                
                # On vérifie l'attribut pour être sûr
                current_display = await courses_view.get_attribute("data-display")
                if current_display == "summary":
                    print("  ✅ Vue Résumé activée avec succès.")
                    return True
                else:
                    print("  ⚠️ Le changement de vue n'a pas été détecté.")
                    return False
            else:
                print("  ⚠️ Option Résumé introuvable dans le menu.")
                return False

        except Exception as e:
            print(f"  ❌ Erreur lors du forçage de la vue : {e}")
            return False

    async def get_timeline_events(self):
        """Extract deadlines from timeline"""
        if not self.page:
            return "Erreur: Scraper non connecté"
        
        print("🔍 Extraction de la Chronologie...")
        try:
            timeline_section = self.page.locator('section[data-block="timeline"]')
            await timeline_section.wait_for(state="visible", timeout=10000)
            
            container = timeline_section.locator('div[data-region="event-list-container"]')
            await container.wait_for(state="visible", timeout=10000)

            print("  -> Attente fin du chargement...")
            loader = container.locator('div[data-region="event-list-loading-placeholder"]')
            
            if await loader.count() > 0:
                await loader.wait_for(state="hidden", timeout=10000)
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.5)

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
                        let dateStr = "Date inconnue";
                        
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

            print(f"✅ {len(events)} événements trouvés.")
            return "\n".join(events) if events else "Aucune deadline trouvée."

        except Exception as e:
            print(f"❌ Erreur extraction chronologie : {e}")
            return f"Erreur: {e}"

    async def get_course_list(self):
        """Get list of courses in Summary View"""
        if not self.page:
            return "Erreur: Scraper non connecté"
        
        courses = []
        print("📚 Extraction de la liste des cours...")

        try:
            overview_section = self.page.locator('section[data-block="myoverviewdevinci"]')
            await overview_section.wait_for(state="visible", timeout=15000)

            # Force le mode d'affichage des cours en "Résumé"
            await self.force_summary_view()

            courses_container = overview_section.locator('div[data-region="courses-view"]')
            await courses_container.wait_for(state="visible", timeout=15000)

            # Attendre que le contenu (le pulse) disparaisse avant de lire
            print("  -> Attente fin du chargement...")
            try:
                await self.page.wait_for_selector('div[data-region="courses-view"] .bg-pulse-grey', state="detached", timeout=15000)
            except:
                pass 

            # 2. EXTRACTION DES DONNÉES (Vue Résumé)
            # On utilise evaluate pour aller vite et gérer les structures imbriquées
            courses_data = await courses_container.evaluate('''(container) => {
                const items = [];
                // En mode Résumé, les cours ont la classe 'course-summaryitem'
                const courseItems = container.querySelectorAll('div.course-summaryitem');
                
                courseItems.forEach(item => {
                    try {
                        // On cherche les infos principales dans la colonne de droite (col-md-9)
                        const colContent = item.querySelector('.col-md-9');
                        if (!colContent) return;

                        // Titre et Lien
                        const nameLink = colContent.querySelector('a.aalink.coursename');
                        const name = nameLink ? nameLink.innerText.trim() : "Nom inconnu";
                        const url = nameLink ? nameLink.href : "#";
                        
                        // Catégorie
                        const catSpan = colContent.querySelector('.categoryname');
                        const category = catSpan ? catSpan.innerText.trim() : "N/A";
                        
                        // Résumé / Description
                        const summaryDiv = colContent.querySelector('.summary');
                        const summary = summaryDiv ? summaryDiv.innerText.trim() : "";

                        // Progression (si présente)
                        let progressText = "";
                        const progressDiv = colContent.querySelector('.progress-text span');
                        if (progressDiv) {
                            // On récupère le texte "% terminé" ou juste le chiffre
                            const fullText = progressDiv.parentElement.innerText;
                            // Nettoyage pour avoir juste "X %"
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
                        console.log("Erreur scraping item: " + e);
                    }
                });
                return items;
            }''')

            # Formatage des résultats
            for data in courses_data:
                # On crée une chaîne d'affichage propre
                course_info = f"📚 {data['name']}"
                if data['category'] and data['category'] != "N/A":
                    course_info += f" ({data['category']})"
                
                if data['progress']:
                    course_info += f" - {data['progress']} done"
                    
                courses.append(course_info)

            print(f"✅ {len(courses)} cours récupérés en mode Résumé.")
            return "\n".join(courses) if courses else "Aucun cours trouvé."

        except Exception as e:
            print(f"❌ Erreur liste cours : {e}")
            # On ne nettoie pas le navigateur ici pour éviter de déconnecter l'utilisateur à chaque erreur
            return f"Erreur: {e}"
        
    async def get_all_courses(self):
        """Get all courses wrapper"""
        return await self.get_course_list()

# Global browser and context
_browser = None
_context = None
_page = None
_scraper = None
_playwright = None

async def cleanup_browser():
    """Close and reset browser connection"""
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
    """Initialize browser and login"""
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

        print("🔌 Connexion au serveur...")
        await _page.goto(LOGIN_URL, timeout=30000)
        
        try:
            if "learning.devinci.fr/my/" not in _page.url:
                if not email or not password:
                    return None
                await _page.fill("input[type='email']", email)
                await _page.fill("input[type='password']", password)
                await asyncio.sleep(0.5)
                await _page.click("#submitButton")
                await _page.wait_for_load_state("networkidle", timeout=20000)
                print("✅ Connexion réussie.")
            else:
                print("✅ Déjà connecté.")
        except Exception as e:
            print(f"⚠️ Erreur connexion: {e}")

        _scraper = DeVinciScraper(_page)
        return _scraper
    except Exception as e:
        print(f"❌ Erreur initialisation browser: {e}")
        return None

async def get_courses_async(email: str = None, password: str = None) -> str:
    """Get all courses asynchronously"""
    try:
        scraper = await init_browser(email, password)
        if scraper is None:
            return "Veuillez fournir vos identifiants De Vinci."
        result = await scraper.get_all_courses()
        return result
    finally:
        # Always cleanup after use to avoid broken connections
        await cleanup_browser()

async def get_deadlines_async(email: str = None, password: str = None) -> str:
    """Get deadlines asynchronously"""
    try:
        scraper = await init_browser(email, password)
        if scraper is None:
            return "Veuillez fournir vos identifiants De Vinci."
        result = await scraper.get_timeline_events()
        return result
    finally:
        # Always cleanup after use to avoid broken connections
        await cleanup_browser()

def get_courses_blocking(email: str = None, password: str = None) -> str:
    """Blocking wrapper for getting all courses"""
    try:
        import sys
        # Windows requires ProactorEventLoopPolicy for subprocess (needed by Playwright)
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(get_courses_async(email, password))
            return result
        except Exception as e:
            logger.error(f"Get courses error: {e}")
            return f"Erreur: {e}"
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Get courses error: {e}")
        return f"Erreur: {e}"

def get_deadlines_blocking(email: str = None, password: str = None) -> str:
    """Blocking wrapper for deadlines"""
    try:
        import sys
        # Windows requires ProactorEventLoopPolicy for subprocess (needed by Playwright)
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(get_deadlines_async(email, password))
            return result
        except Exception as e:
            logger.error(f"Get deadlines error: {e}")
            loop.run_until_complete(cleanup_browser())
            return f"Erreur: {e}"
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Get deadlines error: {e}")
        return f"Erreur: {e}"
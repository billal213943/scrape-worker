#!/usr/bin/env python3
"""
Scraper spécialisé pour le site FlashBack FA
Navigue automatiquement dans toutes les pages de la navbar pour extraire les images
"""

import asyncio
import aiohttp
import aiofiles
import os
import re
import logging
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path
from typing import Set, List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import time
from tqdm.asyncio import tqdm
import io
import hashlib

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gestion des imports optionnels
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    logger.warning("Pillow non disponible - validation d'images désactivée")

# Détection du parser disponible
try:
    import lxml
    HTML_PARSER = 'lxml'
except ImportError:
    HTML_PARSER = 'html.parser'
    logger.warning("lxml non disponible - utilisation de html.parser (plus lent)")

class FlashBackScraper:
    def __init__(self, 
                 base_url: str = "https://sites.google.com/view/reglement-flashback-fa/accueil?authuser=0",
                 output_dir: str = "flashback_images",
                 max_concurrent: int = 8,  # Plus conservateur pour Google Sites
                 delay_between_requests: float = 0.5,  # Plus respectueux
                 timeout: int = 45):
        """
        Scraper spécialisé pour FlashBack FA
        
        Args:
            base_url: URL de départ du site FlashBack FA
            output_dir: Répertoire où sauvegarder les images
            max_concurrent: Nombre de requêtes simultanées max
            delay_between_requests: Délai entre les requêtes (secondes)
            timeout: Timeout des requêtes HTTP
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.max_concurrent = max_concurrent
        self.delay_between_requests = delay_between_requests
        self.timeout = timeout
        
        # Créer le répertoire de sortie
        self.output_dir.mkdir(exist_ok=True)
        
        # Session aiohttp
        self.session = None
        
        # Statistiques
        self.stats = {
            'pages_crawled': 0,
            'images_found': 0,
            'images_downloaded': 0,
            'images_skipped': 0,
            'duplicates_removed': 0,
            'size_filtered': 0
        }
        
        # Tracking des doublons par contenu d'image
        self.image_hashes = set()
        
        # Headers pour simuler un navigateur réel (important pour Google Sites)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Sets pour éviter les doublons
        self.visited_urls: Set[str] = set()
        self.found_images: Set[str] = set()
        self.navbar_pages: Set[str] = set()
        
        # Semaphore pour contrôler la concurrence
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Parser HTML à utiliser
        self.html_parser = HTML_PARSER
        
        # Patterns spécifiques pour détecter les pages FlashBack FA
        self.flashback_patterns = [
            r'reglement-flashback-fa',
            r'flashback',
            r'/view/',
            r'sites\.google\.com'
        ]

    async def __aenter__(self):
        """Context manager pour gérer la session aiohttp"""
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent, 
            limit_per_host=self.max_concurrent,
            ssl=False  # Pour éviter les problèmes SSL avec Google Sites
        )
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fermeture propre de la session"""
        if self.session:
            await self.session.close()

    def is_flashback_url(self, url: str) -> bool:
        """Vérifie si l'URL appartient au site FlashBack FA"""
        try:
            for pattern in self.flashback_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return True
            return False
        except Exception:
            return False

    def normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalise une URL relative ou absolue"""
        try:
            # Joindre l'URL relative à l'URL de base
            full_url = urljoin(base_url, url)
            
            # Supprimer les fragments (#) mais garder les paramètres
            if '#' in full_url:
                full_url = full_url.split('#')[0]
            
            # Décoder l'URL
            full_url = unquote(full_url)
            
            return full_url if self.is_flashback_url(full_url) else None
        except Exception:
            return None

    def should_skip_image(self, image_url: str, context: str = "") -> bool:
        """Détermine si une image doit être ignorée"""
        # URLs à ignorer (réduit aux plus importants)
        skip_patterns = [
            r'catalogue.*illegal',  # Plus spécifique
            r'header.*background',  # Plus spécifique
            r'banner.*main',        # Plus spécifique
            r'wallpaper',
            r'backdrop'
        ]
        
        # Vérifier les patterns dans l'URL
        for pattern in skip_patterns:
            if re.search(pattern, image_url, re.IGNORECASE):
                logger.debug(f"Image ignorée (pattern URL): {image_url}")
                return True
        
        # Vérifier les patterns dans le contexte (plus spécifique)
        if context:
            # Seulement ignorer si c'est clairement un header/banner principal
            if re.search(r'main.*header|hero.*banner|cover.*background', context, re.IGNORECASE):
                logger.debug(f"Image ignorée (pattern contexte): {image_url}")
                return True
        
        return False

    def extract_navbar_urls(self, html_content: str, page_url: str) -> Set[str]:
        """Extrait spécifiquement les URLs de la navbar FlashBack FA"""
        navbar_urls = set()
        
        try:
            soup = BeautifulSoup(html_content, self.html_parser)
            
            # Chercher dans la navigation principale
            nav_elements = soup.find_all(['nav', 'ul', 'div'], class_=re.compile(r'nav|menu|header', re.I))
            
            # Aussi chercher tous les liens qui pourraient être dans la navbar
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                if href:
                    normalized_url = self.normalize_url(href, page_url)
                    if normalized_url and normalized_url not in self.visited_urls:
                        # EXCLURE spécifiquement les pages catalogue
                        if 'catalogue' in href.lower():
                            logger.info(f"Page catalogue ignorée: {normalized_url}")
                            continue
                            
                        # Vérifier si c'est un lien de navigation interne
                        if any(keyword in href.lower() for keyword in [
                            'reglement', 'savoir', 'aide', 'discord', 'services', 'gouvernement', 
                            'ems', 'pompier', 'police', 'army', 'illegal', 
                            'gang', 'orga', 'petite', 'frappe', 'independant', 'entreprise'
                        ]):
                            navbar_urls.add(normalized_url)
                            logger.info(f"Page de navigation trouvée: {normalized_url}")
            
            # Aussi chercher des patterns spécifiques dans les URLs
            for link in all_links:
                href = link.get('href', '')
                if href and 'view/' in href and 'reglement-flashback-fa' in href:
                    # EXCLURE les catalogues
                    if 'catalogue' in href.lower():
                        continue
                        
                    normalized_url = self.normalize_url(href, page_url)
                    if normalized_url:
                        navbar_urls.add(normalized_url)
                        logger.info(f"Page FlashBack trouvée: {normalized_url}")
                        
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la navbar depuis {page_url}: {e}")
        
        return navbar_urls

    def extract_image_urls_from_html(self, html_content: str, page_url: str) -> Set[str]:
        """Extrait toutes les URLs d'images depuis le contenu HTML, spécialement dans les divs"""
        image_urls = set()
        
        try:
            soup = BeautifulSoup(html_content, self.html_parser)
            
            # IGNORER les sections header/banner
            for header in soup.find_all(['header', 'div'], class_=re.compile(r'header|banner|hero|cover', re.I)):
                header.decompose()
            
            # IGNORER les sections avec "catalogue" dans les attributs
            for catalog_section in soup.find_all(attrs={'class': re.compile(r'catalogue', re.I)}):
                catalog_section.decompose()
            for catalog_section in soup.find_all(attrs={'id': re.compile(r'catalogue', re.I)}):
                catalog_section.decompose()
            
            # Rechercher spécifiquement dans toutes les divs restantes
            divs = soup.find_all('div')
            logger.info(f"Analysing {len(divs)} divs sur {page_url} (après filtrage)")
            
            for div in divs:
                # Obtenir le contexte de la div (CORRECTION DU BUG)
                div_classes = div.get('class', [])
                if isinstance(div_classes, list):
                    div_classes = ' '.join(div_classes)
                else:
                    div_classes = str(div_classes)
                
                div_context = ' '.join([
                    div_classes,
                    str(div.get('id', '')),
                    str(div.get('style', ''))
                ])
                
                # Images dans les balises img à l'intérieur des divs
                for img in div.find_all('img'):
                    # Obtenir le contexte de l'image (CORRECTION DU BUG)
                    img_classes = img.get('class', [])
                    if isinstance(img_classes, list):
                        img_classes = ' '.join(img_classes)
                    else:
                        img_classes = str(img_classes)
                    
                    img_context = ' '.join([
                        img_classes,
                        str(img.get('alt', '')),
                        str(img.get('title', '')),
                        div_context
                    ])
                    
                    # Essayer différents attributs d'image
                    for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'srcset']:
                        src = img.get(attr)
                        if src:
                            # Pour srcset, prendre la première URL
                            if attr == 'srcset':
                                src = src.split(',')[0].split(' ')[0]
                            
                            normalized_url = self.normalize_image_url(src, page_url)
                            if normalized_url and not self.should_skip_image(normalized_url, img_context):
                                image_urls.add(normalized_url)
                                logger.debug(f"Image trouvée dans div: {normalized_url}")
                
                # Images en arrière-plan CSS dans les divs (MAIS PAS les headers/banners)
                if not re.search(r'header|banner|hero|cover|background.*large|bg.*main', div_context, re.I):
                    style = div.get('style', '')
                    if 'background-image' in style or 'background' in style:
                        # Extraire l'URL depuis background-image: url(...)
                        matches = re.findall(r'background(?:-image)?:\s*url\(["\']?(.*?)["\']?\)', style)
                        for match in matches:
                            normalized_url = self.normalize_image_url(match, page_url)
                            if normalized_url and not self.should_skip_image(normalized_url, div_context):
                                image_urls.add(normalized_url)
                                logger.debug(f"Image CSS trouvée dans div: {normalized_url}")
            
            # Aussi chercher dans tous les éléments pouvant contenir des images (mais pas les headers)
            for img in soup.find_all('img'):
                # Vérifier que l'image n'est pas dans un header
                parent_context = ""
                parent = img.parent
                while parent and parent.name:
                    parent_classes = parent.get('class', [])
                    if isinstance(parent_classes, list):
                        parent_classes = ' '.join(parent_classes)
                    else:
                        parent_classes = str(parent_classes)
                    
                    parent_context += f" {parent.name} {parent_classes} {parent.get('id', '')}"
                    parent = parent.parent
                
                if not re.search(r'header|banner|hero|cover|catalogue', parent_context, re.I):
                    for attr in ['src', 'data-src', 'data-lazy-src', 'data-original']:
                        src = img.get(attr)
                        if src:
                            normalized_url = self.normalize_image_url(src, page_url)
                            if normalized_url and not self.should_skip_image(normalized_url, parent_context):
                                image_urls.add(normalized_url)
                            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction d'images depuis {page_url}: {e}")
        
        return image_urls

    def normalize_image_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalise une URL d'image"""
        try:
            # Joindre l'URL relative à l'URL de base
            full_url = urljoin(base_url, url)
            
            # Décoder l'URL
            full_url = unquote(full_url)
            
            # Vérifier que c'est bien une image
            if re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|svg)(\?|$)', full_url.lower()):
                return full_url
            
            # Accepter aussi les URLs Google qui peuvent contenir des images
            if 'googleusercontent.com' in full_url or 'ggpht.com' in full_url or 'lh3.google' in full_url:
                return full_url
                
            return None
        except Exception:
            return None

    async def fetch_page(self, url: str) -> Optional[Tuple[str, str]]:
        """Récupère le contenu d'une page web"""
        async with self.semaphore:
            try:
                await asyncio.sleep(self.delay_between_requests)
                
                logger.info(f"Fetching: {url}")
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if 'text/html' in content_type:
                            content = await response.text()
                            logger.info(f"✓ Page récupérée: {url} ({len(content)} chars)")
                            return url, content
                    else:
                        logger.warning(f"Status {response.status} pour {url}")
                        
            except asyncio.TimeoutError:
                logger.error(f"Timeout pour {url}")
            except Exception as e:
                logger.error(f"Erreur lors du fetch de {url}: {e}")
        
        return None

    async def download_image(self, image_url: str, session: aiohttp.ClientSession) -> bool:
        """Télécharge une image avec validation de taille et détection de doublons"""
        try:
            # Vérifier encore une fois si l'image doit être ignorée
            if self.should_skip_image(image_url):
                logger.debug(f"Image ignorée lors du téléchargement: {image_url}")
                return False
            
            async with session.get(image_url) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Vérifier la taille du fichier (ignorer les très gros fichiers)
                    if len(content) > 15 * 1024 * 1024:  # Plus de 15MB
                        logger.debug(f"Image trop lourde ignorée ({len(content)} bytes): {image_url}")
                        return False
                    
                    # Calculer le hash du contenu pour détecter les doublons
                    content_hash = hashlib.md5(content).hexdigest()
                    if content_hash in self.image_hashes:
                        logger.debug(f"Image dupliquée ignorée (hash: {content_hash[:8]}...): {image_url}")
                        self.stats['duplicates_removed'] += 1
                        return False
                    
                    # Vérifier que c'est bien une image valide et de taille suffisante
                    if HAS_PILLOW:
                        try:
                            img = Image.open(io.BytesIO(content))
                            width, height = img.size
                            
                            # Filtrer les images trop petites (< 100x100px)
                            if width < 100 or height < 100:
                                logger.debug(f"Image trop petite ignorée ({width}x{height}): {image_url}")
                                self.stats['size_filtered'] += 1
                                return False
                            
                            # Ignorer les images vraiment énormes (probablement des banners)
                            if width > 4000 or height > 3000:
                                logger.debug(f"Image trop grande ignorée ({width}x{height}): {image_url}")
                                self.stats['size_filtered'] += 1
                                return False
                            
                            logger.info(f"✓ Image valide ({width}x{height}, {len(content)} bytes): {image_url}")
                                
                        except Exception:
                            logger.warning(f"Fichier non valide ignoré: {image_url}")
                            return False
                    else:
                        # Sans Pillow, on se contente de vérifier la taille du fichier
                        if len(content) < 1000:  # Moins de 1KB, probablement pas une vraie image
                            logger.debug(f"Fichier trop petit ignoré: {image_url}")
                            self.stats['size_filtered'] += 1
                            return False
                        
                        logger.info(f"✓ Image téléchargée ({len(content)} bytes): {image_url}")
                    
                    # Générer un nom de fichier unique
                    parsed_url = urlparse(image_url)
                    
                    # Extraire le nom de fichier depuis l'URL
                    if parsed_url.path:
                        filename = os.path.basename(parsed_url.path)
                    else:
                        filename = f"flashback_image_{abs(hash(image_url))}.jpg"
                    
                    # Nettoyer le nom de fichier
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    if not re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|svg)$', filename.lower()):
                        filename += '.jpg'
                    
                    # Préfixer avec flashback pour l'organisation
                    filename = f"flashback_{filename}"
                    
                    # Ajouter le hash pour éviter les collisions de noms
                    name_part, ext_part = os.path.splitext(filename)
                    filename = f"{name_part}_{content_hash[:8]}{ext_part}"
                    
                    filepath = self.output_dir / filename
                    
                    # Ajouter le hash à notre set de tracking
                    self.image_hashes.add(content_hash)
                    
                    # Sauvegarder l'image
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(content)
                    
                    logger.info(f"✓ Image sauvegardée: {filename}")
                    self.stats['images_downloaded'] += 1
                    return True
                else:
                    logger.warning(f"Échec téléchargement {image_url}: status {response.status}")
                    
        except Exception as e:
            logger.error(f"Erreur téléchargement {image_url}: {e}")
        
        self.stats['images_skipped'] += 1
        return False

    async def cleanup_output_directory(self):
        """Nettoie le répertoire de sortie pour commencer un nouveau scraping."""
        if self.output_dir.exists():
            logger.info(f"Nettoyage du répertoire de sortie: {self.output_dir}")
            for item in self.output_dir.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                        logger.debug(f"Fichier supprimé: {item}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la suppression du fichier {item}: {e}")
                elif item.is_dir():
                    try:
                        item.rmdir()
                        logger.debug(f"Dossier supprimé: {item}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la suppression du dossier {item}: {e}")
            logger.info(f"Répertoire de sortie nettoyé: {self.output_dir}")
        else:
            logger.info(f"Répertoire de sortie déjà vide: {self.output_dir}")

    async def crawl_flashback_site(self) -> Dict[str, int]:
        """Fonction principale pour crawler le site FlashBack FA"""
        logger.info("🚀 Démarrage du scraping du site FlashBack FA")
        logger.info(f"📁 Répertoire de sortie: {self.output_dir}")
        
        # Nettoyer le dossier de sortie avant de commencer
        await self.cleanup_output_directory()
        
        start_time = time.time()
        stats = {'pages_crawled': 0, 'images_found': 0, 'images_downloaded': 0}
        
        # Normaliser l'URL d'accueil pour comparaison
        home_url_normalized = self.base_url.split('?')[0].split('#')[0]  # Enlever paramètres et fragments
        
        # Phase 1: Découvrir toutes les pages de la navbar
        logger.info("Phase 1: Découverte des pages de navigation...")
        
        # Commencer par la page d'accueil (MAIS NE PAS extraire ses images)
        home_result = await self.fetch_page(self.base_url)
        if home_result:
            url, content = home_result
            self.visited_urls.add(url)
            stats['pages_crawled'] += 1
            
            # SEULEMENT découvrir les pages de la navbar (pas d'extraction d'images pour l'accueil)
            logger.info("🏠 Page d'accueil: extraction des liens de navigation uniquement (images ignorées)")
            navbar_urls = self.extract_navbar_urls(content, url)
            self.navbar_pages.update(navbar_urls)
        
        logger.info(f"📄 {len(self.navbar_pages)} pages de navigation découvertes")
        
        # Phase 2: Crawler toutes les pages découvertes (SANS la page d'accueil)
        logger.info("Phase 2: Crawling des pages de navigation (hors accueil)...")
        
        with tqdm(desc="Pages FlashBack", unit="pages") as pbar:
            remaining_pages = self.navbar_pages - self.visited_urls
            
            while remaining_pages:
                # Traiter par batch pour éviter de surcharger
                current_batch = list(remaining_pages)[:self.max_concurrent]
                remaining_pages -= set(current_batch)
                
                # Crawler le batch en parallèle
                tasks = [self.fetch_page(url) for url in current_batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, tuple):
                        url, content = result
                        self.visited_urls.add(url)
                        stats['pages_crawled'] += 1
                        pbar.update(1)
                        
                        # VÉRIFIER si c'est la page d'accueil avant d'extraire les images
                        url_normalized = url.split('?')[0].split('#')[0]
                        if url_normalized == home_url_normalized or 'accueil' in url.lower():
                            logger.info(f"🏠 Page d'accueil détectée et ignorée pour l'extraction d'images: {url}")
                            continue
                        
                        # Extraire les images de cette page (toutes SAUF l'accueil)
                        page_images = self.extract_image_urls_from_html(content, url)
                        self.found_images.update(page_images)
                        logger.info(f"📄 Page {url}: {len(page_images)} images trouvées")
                        
                        # PLUS de découverte de navbar - on a déjà tout découvert depuis l'accueil
                        # (supprimé pour éviter les logs répétitifs)
        
        stats['images_found'] = len(self.found_images)
        logger.info(f"Phase 2 terminée: {stats['pages_crawled']} pages, {stats['images_found']} images trouvées")
        
        # Phase 3: Télécharger toutes les images
        logger.info("Phase 3: Téléchargement des images FlashBack...")
        
        if self.found_images:
            # Session spéciale pour les téléchargements
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)
            timeout = aiohttp.ClientTimeout(total=self.timeout * 2)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=self.headers) as download_session:
                semaphore = asyncio.Semaphore(max(1, self.max_concurrent // 2))  # Plus conservateur
                
                async def download_with_semaphore(image_url):
                    async with semaphore:
                        await asyncio.sleep(0.2)  # Délai entre téléchargements
                        return await self.download_image(image_url, download_session)
                
                # Télécharger toutes les images avec barre de progression
                tasks = [download_with_semaphore(img_url) for img_url in self.found_images]
                
                results = []
                for task in tqdm.as_completed(tasks, desc="Images FlashBack", unit="img"):
                    result = await task
                    results.append(result)
                    if result:
                        stats['images_downloaded'] += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Rapport final
        logger.info("=" * 60)
        logger.info("🎮 RAPPORT FINAL - FLASHBACK FA SCRAPING")
        logger.info("=" * 60)
        logger.info(f"🌐 Site crawlé: FlashBack FA")
        logger.info(f"⏱️  Durée totale: {duration:.2f} secondes")
        logger.info(f"📄 Pages crawlées: {stats['pages_crawled']}")
        logger.info(f"🖼️  Images trouvées: {stats['images_found']}")
        logger.info(f"💾 Images téléchargées: {stats['images_downloaded']}")
        logger.info(f"🔍 Doublons supprimés: {self.stats['duplicates_removed']}")
        logger.info(f"📏 Images filtrées (taille): {self.stats['size_filtered']}")
        logger.info(f"⚠️  Images ignorées: {self.stats['images_skipped']}")
        logger.info(f"📁 Répertoire: {self.output_dir.absolute()}")
        if stats['images_found'] > 0:
            success_rate = (stats['images_downloaded'] / stats['images_found']) * 100
            logger.info(f"✅ Taux de réussite: {success_rate:.1f}%")
        logger.info("=" * 60)
        
        return stats

async def main():
    """Fonction principale pour scraper FlashBack FA"""
    flashback_url = "https://sites.google.com/view/reglement-flashback-fa/accueil?authuser=0"
    
    print("🎮 FLASHBACK FA IMAGE SCRAPER")
    print("=" * 40)
    print(f"🌐 Site cible: {flashback_url}")
    print("🔍 Recherche d'images dans toutes les divs de navigation...")
    print()
    
    async with FlashBackScraper(
        base_url=flashback_url,
        output_dir="flashback_images",
        max_concurrent=6,  # Respectueux avec Google Sites
        delay_between_requests=0.8,  # Plus lent mais plus sûr
        timeout=60
    ) as scraper:
        stats = await scraper.crawl_flashback_site()
        
        print("\n🎉 Scraping FlashBack FA terminé!")
        print(f"📊 Résultats:")
        print(f"   🌐 Pages explorées: {stats['pages_crawled']}")
        print(f"   🖼️  Images découvertes: {stats['images_found']}")
        print(f"   💾 Images sauvegardées: {stats['images_downloaded']}")
        
        if stats['images_found'] > 0:
            success_rate = (stats['images_downloaded'] / stats['images_found']) * 100
            print(f"   ✅ Taux de réussite: {success_rate:.1f}%")

if __name__ == "__main__":
    asyncio.run(main()) 
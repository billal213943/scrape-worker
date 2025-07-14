#!/usr/bin/env python3
"""
Pipeline complète FlashBack FA
Scraping des images + Extraction automatique des DataFrames par IA
"""

import os
import sys
import asyncio
import time
from pathlib import Path

def load_env_file():
    """Charge le fichier .env s'il existe"""
    env_file = Path('.env')
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement du fichier .env: {e}")

async def run_scraper():
    """Lance le scraper FlashBack FA"""
    print("🎯 ÉTAPE 1: SCRAPING DES IMAGES")
    print("=" * 50)
    
    try:
        # Importer et lancer le scraper
        from flashback_scraper import FlashBackScraper
        
        flashback_url = "https://sites.google.com/view/reglement-flashback-fa/accueil?authuser=0"
        
        print(f"🌐 Site cible: {flashback_url}")
        print("🔍 Recherche d'images dans toutes les divs...")
        print("📏 Filtrage: > 100x100px, détection de doublons")
        print()
        
        async with FlashBackScraper(
            base_url=flashback_url,
            output_dir="flashback_images",
            max_concurrent=6,  # Respectueux avec Google Sites
            delay_between_requests=0.8,  # Plus lent mais plus sûr
            timeout=60
        ) as scraper:
            stats = await scraper.crawl_flashback_site()
            
            print("\n✅ SCRAPING TERMINÉ!")
            print(f"📊 Résultats:")
            print(f"   🌐 Pages explorées: {stats['pages_crawled']}")
            print(f"   🖼️  Images découvertes: {stats['images_found']}")
            print(f"   💾 Images téléchargées: {stats['images_downloaded']}")
            print(f"   🔍 Doublons supprimés: {scraper.stats['duplicates_removed']}")
            print(f"   📏 Images filtrées: {scraper.stats['size_filtered']}")
            
            if stats['images_found'] > 0:
                success_rate = (stats['images_downloaded'] / stats['images_found']) * 100
                print(f"   ✅ Taux de réussite: {success_rate:.1f}%")
            
            return stats['images_downloaded'] > 0
            
    except ImportError as e:
        print(f"❌ Erreur d'importation du scraper: {e}")
        print("   Vérifiez que tous les modules sont installés")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du scraping: {e}")
        return False

def run_ai_extraction():
    """Lance l'extraction IA des DataFrames"""
    print("\n🎯 ÉTAPE 2: EXTRACTION IA DES DATAFRAMES")
    print("=" * 50)
    
    try:
        # Vérifier qu'on a des images
        images_dir = Path("flashback_images")
        if not images_dir.exists():
            print("❌ Dossier 'flashback_images' non trouvé!")
            return False
        
        # Compter les images
        image_count = sum(1 for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp'] 
                         for _ in images_dir.glob(ext))
        
        if image_count == 0:
            print(f"❌ Aucune image trouvée dans {images_dir}")
            return False
        
        print(f"📷 {image_count} images trouvées pour analyse IA")
        print("🤖 GPT-4 Vision va analyser automatiquement tous les tableaux")
        print()
        
        # Importer et lancer l'extracteur IA
        from image_to_dataframe import UniversalTableExtractorAI
        
        ai_extractor = UniversalTableExtractorAI("flashback_images")
        dataframes_by_type = ai_extractor.process_all_images()
        
        if dataframes_by_type:
            total_elements = sum(len(df) for df in dataframes_by_type.values())
            print(f"\n📊 {total_elements} éléments détectés dans {len(dataframes_by_type)} types de tableaux!")
            
            # Exporter les DataFrames
            ai_extractor.export_all_dataframes(dataframes_by_type)
            print("✅ DataFrames exportés vers flashback_dataframes/")
            
            # Statistiques détaillées
            print(f"\n📈 Statistiques:")
            for table_type, df in dataframes_by_type.items():
                print(f"   📋 {table_type.capitalize()}: {len(df)} éléments")
                if table_type == 'armes' and 'Type' in df.columns:
                    type_counts = df['Type'].value_counts()
                    for weapon_type, count in type_counts.items():
                        print(f"      - {weapon_type}: {count} armes")
            
            print(f"\n🎯 TOTAL: {total_elements} éléments extraits automatiquement!")
            return True
        else:
            print("❌ Aucun tableau détecté par l'IA")
            return False
            
    except ImportError as e:
        print(f"❌ Erreur d'importation de l'extracteur IA: {e}")
        print("   Vérifiez que tous les modules sont installés")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction IA: {e}")
        return False

def check_prerequisites():
    """Vérifie que tous les prérequis sont remplis"""
    print("🔍 VÉRIFICATION DES PRÉREQUIS")
    print("=" * 40)
    
    # Vérifier la clé API OpenAI
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Clé API OpenAI non configurée!")
        print()
        print("🔧 Solutions:")
        print("   1. Configurez automatiquement: python setup_openai.py")
        print("   2. Ou définissez manuellement: export OPENAI_API_KEY=your_api_key")
        print("   3. Ou créez un fichier .env avec: OPENAI_API_KEY=your_api_key")
        print()
        print("💡 Obtenez votre clé API sur: https://platform.openai.com/api-keys")
        
        # Proposer de lancer la configuration
        choice = input("Voulez-vous configurer maintenant ? (O/n): ").lower()
        if choice not in ['n', 'non', 'no']:
            print()
            os.system("python setup_openai.py")
            # Recharger après configuration
            load_env_file()
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print("❌ Configuration échouée")
                return False
        else:
            return False
    
    print(f"✅ Clé API OpenAI configurée (***{api_key[-6:]})")
    
    # Vérifier les modules requis
    missing_modules = []
    required_modules = [
        ('aiohttp', 'aiohttp'),
        ('aiofiles', 'aiofiles'),
        ('beautifulsoup4', 'bs4'),
        ('pandas', 'pandas'),
        ('openai', 'openai'),
        ('pillow', 'PIL'),
        ('tqdm', 'tqdm')
    ]
    
    for module_name, import_name in required_modules:
        try:
            __import__(import_name)
            print(f"✅ {module_name}")
        except ImportError:
            missing_modules.append(module_name)
            print(f"❌ {module_name}")
    
    if missing_modules:
        print(f"\n❌ Modules manquants: {', '.join(missing_modules)}")
        print("   Installez avec: pip install -r requirements.txt")
        return False
    
    print("✅ Tous les modules requis sont installés")
    return True

async def main():
    """Pipeline principale"""
    start_time = time.time()
    
    print("🎮 FLASHBACK FA - PIPELINE COMPLÈTE")
    print("🤖 SCRAPING + EXTRACTION IA AUTOMATIQUE")
    print("=" * 60)
    print()
    
    # Charger les variables d'environnement
    load_env_file()
    
    # Vérifier les prérequis
    if not check_prerequisites():
        print("\n❌ Prérequis non remplis. Veuillez corriger avant de continuer.")
        return
    
    print("\n🚀 Tous les prérequis sont OK, démarrage de la pipeline...")
    
    # Demander confirmation
    print("\n📋 Cette pipeline va:")
    print("   1. 🕷️  Scraper toutes les images du site FlashBack FA")
    print("   2. 🤖 Analyser les images avec GPT-4 Vision")
    print("   3. 📊 Extraire automatiquement tous les tableaux")
    print("   4. 💾 Générer les DataFrames dans flashback_dataframes/")
    print()
    
    choice = input("Voulez-vous continuer ? (O/n): ").lower()
    if choice in ['n', 'non', 'no']:
        print("Pipeline annulée.")
        return
    
    print("\n" + "="*60)
    
    # ÉTAPE 1: Scraping
    scraping_success = await run_scraper()
    
    if not scraping_success:
        print("\n❌ Échec du scraping. Pipeline interrompue.")
        return
    
    print("\n" + "="*60)
    
    # ÉTAPE 2: Extraction IA
    extraction_success = run_ai_extraction()
    
    # Résumé final
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "="*60)
    print("🎉 PIPELINE FLASHBACK FA TERMINÉE")
    print("="*60)
    print(f"⏱️  Durée totale: {duration:.2f} secondes")
    
    if scraping_success and extraction_success:
        print("✅ Succès complet!")
        print("📁 Résultats disponibles dans:")
        print("   📷 flashback_images/ (images scrapées)")
        print("   📊 flashback_dataframes/ (DataFrames générés)")
        print()
        print("🎯 Vous pouvez maintenant utiliser les DataFrames:")
        print("   from flashback_dataframes.flashback_armes_data import armes_df")
    else:
        print("⚠️  Pipeline partiellement réussie")
        if scraping_success:
            print("✅ Scraping: OK")
        else:
            print("❌ Scraping: Échec")
        if extraction_success:
            print("✅ Extraction IA: OK")
        else:
            print("❌ Extraction IA: Échec")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 
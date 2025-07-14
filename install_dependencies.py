#!/usr/bin/env python3
"""
Script d'installation des dépendances avec gestion des erreurs pour Pillow et lxml
"""

import subprocess
import sys
import os

def run_command(cmd):
    """Execute une commande et retourne True si succès"""
    try:
        print(f"⚡ Exécution: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Succès: {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur: {cmd}")
        print(f"   Message: {e.stderr}")
        return False

def install_dependencies():
    """Installe les dépendances avec plusieurs stratégies pour Pillow et lxml"""
    
    print("🚀 INSTALLATION DES DÉPENDANCES FLASHBACK SCRAPER")
    print("=" * 60)
    
    # Dépendances de base (sans Pillow ni lxml)
    base_deps = [
        "requests==2.31.0",
        "beautifulsoup4==4.12.2", 
        "aiohttp==3.9.1",
        "aiofiles==23.2.1",
        "urllib3==2.1.0",
        "tqdm==4.66.1"
    ]
    
    print("📦 Installation des dépendances de base...")
    for dep in base_deps:
        if not run_command(f"pip install {dep}"):
            print(f"⚠️  Impossible d'installer {dep}, mais on continue...")
    
    # Stratégies pour lxml (problématique sur Windows/Python 3.13)
    print("\n📄 Installation de lxml...")
    lxml_strategies = [
        "pip install --only-binary=lxml lxml",  # Wheel pré-compilé uniquement
        "pip install lxml==4.9.2",             # Version plus stable
        "pip install lxml==4.8.0",             # Version encore plus ancienne
        "pip install --no-deps lxml",          # Sans dépendances
    ]
    
    lxml_installed = False
    for strategy in lxml_strategies:
        print(f"   Tentative: {strategy}")
        if run_command(strategy):
            lxml_installed = True
            break
        print(f"   ❌ Échec, tentative suivante...")
    
    if not lxml_installed:
        print("\n⚠️  ATTENTION: lxml n'a pas pu être installé!")
        print("   Le scraper utilisera html.parser (plus lent mais fonctionnel)")
        print("   Alternatives pour lxml:")
        print("   1. Installer via conda: conda install lxml")
        print("   2. Utiliser WSL (Windows Subsystem for Linux)")
        print("   3. Télécharger wheel depuis: https://pypi.org/project/lxml/#files")
    
    # Stratégies pour Pillow
    print("\n🖼️  Installation de Pillow...")
    pillow_strategies = [
        "pip install --only-binary=Pillow Pillow",  # Wheel pré-compilé
        "pip install Pillow==10.2.0",               # Version stable
        "pip install Pillow==9.5.0",                # Version plus ancienne
        "pip install Pillow",                       # Dernière version
    ]
    
    pillow_installed = False
    for strategy in pillow_strategies:
        print(f"   Tentative: {strategy}")
        if run_command(strategy):
            pillow_installed = True
            break
        print(f"   ❌ Échec, tentative suivante...")
    
    if not pillow_installed:
        print("\n⚠️  ATTENTION: Pillow n'a pas pu être installé!")
        print("   Alternatives:")
        print("   1. Installer via conda: conda install pillow")
        print("   2. Télécharger wheel depuis: https://pypi.org/project/Pillow/#files")
        print("   3. Le scraper fonctionnera mais sans validation d'images")
    
    print("\n" + "=" * 60)
    print("📋 VÉRIFICATION DES INSTALLATIONS")
    print("=" * 60)
    
    # Vérifier les installations
    packages_to_check = [
        "requests", "beautifulsoup4", "aiohttp", "aiofiles", 
        "urllib3", "tqdm", "lxml", "PIL"
    ]
    
    essential_working = True
    for package in packages_to_check:
        try:
            if package == "PIL":
                import PIL
                print(f"✅ {package} (Pillow): {PIL.__version__}")
            else:
                module = __import__(package)
                version = getattr(module, '__version__', 'Version inconnue')
                print(f"✅ {package}: {version}")
        except ImportError:
            print(f"❌ {package}: Non installé")
            if package in ["requests", "beautifulsoup4", "aiohttp"]:
                essential_working = False
    
    print("\n" + "=" * 60)
    if essential_working:
        print("🎉 Installation terminée! Les composants essentiels sont installés.")
        print("💡 Vous pouvez maintenant lancer: python run_flashback.py")
        if not lxml_installed:
            print("⚠️  Note: lxml manquant, le parsing sera plus lent mais fonctionnel")
        if not pillow_installed:
            print("⚠️  Note: Pillow manquant, pas de validation d'images")
    else:
        print("❌ Installation incomplète. Composants essentiels manquants.")
        print("💡 Essayez: pip install --upgrade pip")
        print("💡 Ou utilisez conda: conda install requests beautifulsoup4 aiohttp")

if __name__ == "__main__":
    install_dependencies() 
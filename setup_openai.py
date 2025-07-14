#!/usr/bin/env python3
"""
Script de configuration de la clé API OpenAI pour l'extracteur d'armes FlashBack FA
"""

import os
import sys
from pathlib import Path

def setup_openai_api():
    """Configure la clé API OpenAI"""
    print("🔑 CONFIGURATION API OPENAI")
    print("=" * 40)
    print()
    
    # Vérifier si une clé existe déjà
    existing_key = os.getenv('OPENAI_API_KEY')
    if existing_key:
        print(f"✅ Clé API déjà configurée: ***{existing_key[-6:]}")
        
        choice = input("Voulez-vous la remplacer ? (o/N): ").lower()
        if choice not in ['o', 'oui', 'y', 'yes']:
            print("Configuration annulée.")
            return
    
    print("💡 Obtenez votre clé API sur: https://platform.openai.com/api-keys")
    print("📝 Format attendu: sk-...")
    print()
    
    # Demander la clé API
    api_key = input("Entrez votre clé API OpenAI: ").strip()
    
    if not api_key:
        print("❌ Clé API vide. Configuration annulée.")
        return
    
    if not api_key.startswith('sk-'):
        print("⚠️  Attention: La clé ne commence pas par 'sk-'")
        confirm = input("Continuer quand même ? (o/N): ").lower()
        if confirm not in ['o', 'oui', 'y', 'yes']:
            print("Configuration annulée.")
            return
    
    # Créer le fichier .env
    env_file = Path('.env')
    
    try:
        # Lire le fichier existant
        env_content = ""
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filtrer les lignes OPENAI_API_KEY existantes
            filtered_lines = [line for line in lines if not line.startswith('OPENAI_API_KEY=')]
            env_content = ''.join(filtered_lines)
        
        # Ajouter la nouvelle clé
        env_content += f"OPENAI_API_KEY={api_key}\n"
        
        # Écrire le fichier
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"✅ Clé API sauvegardée dans {env_file}")
        
        # Définir aussi la variable d'environnement pour cette session
        os.environ['OPENAI_API_KEY'] = api_key
        print("✅ Variable d'environnement définie pour cette session")
        
        print()
        print("🎯 Configuration terminée!")
        print("   Vous pouvez maintenant lancer l'extracteur IA avec: python run_ocr.py")
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        
        # Méthode alternative: afficher les instructions manuelles
        print()
        print("🔧 Configuration manuelle:")
        if os.name == 'nt':  # Windows
            print(f"   set OPENAI_API_KEY={api_key}")
        else:  # Unix/Linux/Mac
            print(f"   export OPENAI_API_KEY={api_key}")

def test_openai_connection():
    """Teste la connexion à l'API OpenAI"""
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ Clé API non trouvée. Lancez d'abord setup_openai.py")
            return False
        
        print("🧪 Test de connexion à l'API OpenAI...")
        
        client = OpenAI(api_key=api_key)
        
        # Test simple avec GPT-3.5
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("✅ Connexion API réussie!")
        print(f"   Modèle utilisé: {response.model}")
        print(f"   Réponse: {response.choices[0].message.content}")
        return True
        
    except ImportError:
        print("❌ Module openai non installé. Installez avec: pip install openai")
        return False
    except Exception as e:
        print(f"❌ Erreur de connexion API: {e}")
        return False

def main():
    """Fonction principale"""
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_openai_connection()
    else:
        setup_openai_api()

if __name__ == "__main__":
    main() 
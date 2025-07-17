#!/usr/bin/env python3
"""
Script d'extraction de tableaux FlashBack FA utilisant OpenAI GPT-4 Vision
Analyse directement toutes les images de tableaux et retourne des DataFrames structurés
"""

import pandas as pd
import openai
from openai import OpenAI
import base64
import json
import os
import sys
from pathlib import Path
import logging
from typing import List, Dict, Optional, Tuple
import re
from PIL import Image
import io
import shutil

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

# Charger les variables d'environnement depuis .env
load_env_file()

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UniversalTableExtractorAI:
    def __init__(self, images_dir: str = "flashback_images", api_key: Optional[str] = None):
        """
        Extracteur universel de tableaux FlashBack FA utilisant GPT-4 Vision
        
        Args:
            images_dir: Répertoire contenant les images à analyser
            api_key: Clé API OpenAI (optionnel, peut être définie via variable d'environnement)
        """
        self.images_dir = Path(images_dir)
        
        # Configuration OpenAI
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.error("❌ Clé API OpenAI non trouvée!")
            logger.info("💡 Définissez votre clé API avec: export OPENAI_API_KEY=your_api_key")
            logger.info("💡 Ou passez-la en paramètre: UniversalTableExtractorAI(api_key='your_key')")
            sys.exit(1)
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Stockage des DataFrames par type
        self.dataframes = {}

    def encode_image_to_base64(self, image_path: Path) -> str:
        """Encode une image en base64 pour l'API OpenAI"""
        try:
            # Ouvrir et redimensionner l'image si nécessaire
            with Image.open(image_path) as img:
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionner si trop grande (limite OpenAI: 20MB, recommandé: 2048x2048)
                max_size = 2048
                if max(img.width, img.height) > max_size:
                    ratio = max_size / max(img.width, img.height)
                    new_width = int(img.width * ratio)
                    new_height = int(img.height * ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Encoder en base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                buffer.seek(0)
                return base64.b64encode(buffer.read()).decode('utf-8')
                
        except Exception as e:
            logger.error(f"Erreur lors de l'encodage de {image_path}: {e}")
            return None

    def analyze_all_tables_with_vision(self, image_path: Path) -> Tuple[str, List[Dict]]:
        """Analyse tous les tableaux dans une image avec GPT-4 Vision"""
        try:
            logger.info(f"🤖 Analyse IA complète de {image_path.name}")
            
            # Encoder l'image
            base64_image = self.encode_image_to_base64(image_path)
            if not base64_image:
                return None, []
            
            # Prompt universel pour détecter tous les types de tableaux
            system_prompt = """Tu es un expert en analyse de tableaux pour le serveur de jeu FlashBack FA.

            Ton rôle est d'identifier et extraire TOUS les tableaux visibles dans l'image, quel que soit leur type (armes, véhicules, objets, immobilier, emplois, etc.).

            INSTRUCTIONS:
            1. Examine TOUTE l'image pour détecter tous les tableaux de données
            2. Pour chaque tableau trouvé, détermine son TYPE (ex: "armes", "véhicules", "objets", "immobilier", "emplois")  
            3. Extrait TOUTES les données de chaque tableau
            4. Conserve la structure et les colonnes exactes de chaque tableau
            5. Les symboles ✓/✗ ou coches/croix = "autoriser"/"interdit"
            6. Retourne un JSON avec la structure suivante:

            {
              "table_type": "nom_du_type_de_tableau",
              "data": [
                {
                  "colonne1": "valeur1",
                  "colonne2": "valeur2",
                  ...
                }
              ]
            }

            Si plusieurs tableaux sont détectés, retourne une liste de ces objets.
            Si aucun tableau détecté, retourne une liste vide []."""
            
            user_prompt = """Analyse cette image FlashBack FA et extrait TOUS les tableaux visibles.

            Pour chaque tableau trouvé:
            1. Identifie son type (armes, véhicules, objets, etc.)
            2. Extrait toutes les données ligne par ligne
            3. Conserve tous les noms de colonnes exactement comme dans l'image
            4. Convertis les symboles ✓/✗ en "autoriser"/"interdit"

            Retourne UNIQUEMENT un JSON valide avec cette structure:
            [
              {
                "table_type": "type_du_tableau",
                "data": [
                  {"colonne1": "valeur1", "colonne2": "valeur2", ...}
                ]
              }
            ]

            N'ajoute AUCUN texte avant ou après le JSON."""
            
            # Appel à l'API OpenAI GPT-4 Vision
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            # Extraire la réponse
            content = response.choices[0].message.content.strip()
            logger.info(f"🤖 Réponse IA brute: {content[:200]}...")
            
            # Parser le JSON
            try:
                tables = json.loads(content)
                if isinstance(tables, list):
                    logger.info(f"✅ {len(tables)} tableaux détectés par l'IA dans {image_path.name}")
                    return None, tables # Return None for table_type as it's not directly used here
                else:
                    logger.warning(f"⚠️ Réponse IA non valide pour {image_path.name}: pas une liste")
                    return None, []
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Erreur JSON pour {image_path.name}: {e}")
                logger.error(f"Contenu reçu: {content}")
                
                # Tentative de nettoyage du JSON
                cleaned_content = self.clean_json_response(content)
                if cleaned_content:
                    try:
                        tables = json.loads(cleaned_content)
                        if isinstance(tables, list):
                            logger.info(f"✅ JSON nettoyé: {len(tables)} tableaux détectés")
                            return None, tables
                    except:
                        pass
                
                return None, []
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'analyse IA de {image_path}: {e}")
            return None, []

    def clean_json_response(self, content: str) -> Optional[str]:
        """Nettoie la réponse IA pour extraire le JSON valide"""
        try:
            # Chercher le JSON entre crochets (liste)
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json_match.group(0)
            
            # Chercher le JSON entre accolades (objet unique)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return f"[{json_match.group(0)}]"
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage JSON: {e}")
            return None

    def normalize_table_data(self, table_data: List[Dict], table_type: str) -> List[Dict]:
        """Normalise les données d'un tableau selon son type"""
        normalized_data = []
        
        for row in table_data:
            normalized_row = {}
            
            # Normaliser chaque champ
            for key, value in row.items():
                # Nettoyer la clé
                clean_key = str(key).strip()
                clean_value = str(value).strip()
                
                # Normaliser les autorisations
                if any(auth_word in clean_key.lower() for auth_word in ['indépendant', 'pf offi', 'gang', 'orga', 'autorisation']):
                    if any(symbol in clean_value.lower() for symbol in ['✓', 'oui', 'yes', 'autoris', 'allow', 'permit']):
                        clean_value = 'autoriser'
                    elif any(symbol in clean_value.lower() for symbol in ['✗', '❌', 'non', 'no', 'interdit', 'forbid', 'deny']):
                        clean_value = 'interdit'
                
                # Normaliser les prix
                if any(price_word in clean_key.lower() for price_word in ['prix', 'price', 'coût', 'cost', 'revente']):
                    if 'interdit' in clean_value.lower():
                        clean_value = 'INTERDIT'
                    else:
                        price_match = re.search(r'(\d+)', clean_value.replace(' ', '').replace("'", ''))
                        if price_match:
                            price_num = price_match.group(1)
                            if len(price_num) <= 3:
                                clean_value = f"{price_num} 000$"
                            else:
                                clean_value = f"{price_num}$"
                
                # Normaliser les quantités/munitions
                if any(qty_word in clean_key.lower() for qty_word in ['munitions', 'quantité', 'max', 'stock']):
                    qty_match = re.search(r'(\d+)', clean_value)
                    if qty_match:
                        clean_value = qty_match.group(1)
                
                normalized_row[clean_key] = clean_value
            
            if normalized_row:  # Ajouter seulement si on a des données
                normalized_data.append(normalized_row)
        
        return normalized_data

    def process_all_images(self) -> Dict[str, pd.DataFrame]:
        """Traite toutes les images et retourne UN DataFrame par image avec organisation parfaite"""
        logger.info(f"🤖 Analyse IA - UN dataset par image dans {self.images_dir}")
        
        dataframes_by_image = {}
        processed_count = 0
        
        # Traiter chaque image individuellement
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']
        image_files = []
        
        # Collecter toutes les images et les trier
        for ext in image_extensions:
            image_files.extend(self.images_dir.glob(ext))
        
        # Trier les images par nom pour un ordre cohérent
        image_files.sort(key=lambda x: x.name)
        
        for image_index, image_path in enumerate(image_files, 1):
            logger.info(f"📷 Analyse IA de {image_path.name} ({image_index}/{len(image_files)})")
            
            # Analyser avec GPT-4 Vision
            table_type, tables = self.analyze_all_tables_with_vision(image_path)
            
            if tables:
                # Collecter toutes les données de cette image
                all_image_data = []
                
                for table_index, table in enumerate(tables):
                    if isinstance(table, dict):
                        table_data = table.get('data', [])
                        detected_type = table.get('table_type', 'tableau').lower()
                    else:
                        # Si c'est directement une liste
                        table_data = table if isinstance(table, list) else []
                        detected_type = 'tableau'
                    
                    if table_data:
                        # Normaliser les données de ce tableau
                        normalized_data = self.normalize_table_data(table_data, detected_type)
                        
                        if normalized_data:
                            # Ajouter chaque élément avec métadonnées
                            for item in normalized_data:
                                # Nettoyer l'item - garder seulement les colonnes utiles
                                clean_item = {}
                                
                                # Garder seulement les colonnes qui ont des valeurs
                                for key, value in item.items():
                                    if value and str(value).strip():
                                        clean_item[key] = str(value).strip()
                                
                                # Ajouter les métadonnées si l'item a du contenu
                                if clean_item:
                                    clean_item['Table_Type'] = detected_type.capitalize()
                                    clean_item['Source_Image'] = image_path.name
                                    all_image_data.append(clean_item)
                            
                            logger.info(f"  ✅ Tableau '{detected_type}': {len(normalized_data)} éléments")
                
                # Créer un DataFrame pour cette image si on a des données
                if all_image_data:
                    # Nom propre et organisé pour ce dataset
                    dataset_name = f"image_{image_index:02d}"
                    
                    # Supprimer les doublons dans cette image
                    unique_items = []
                    seen_items = set()
                    
                    for item in all_image_data:
                        # Utiliser les premières valeurs significatives comme clé unique
                        key_values = []
                        for key, value in item.items():
                            if key not in ['Table_Type', 'Source_Image'] and value and str(value).strip():
                                key_values.append(str(value).lower().strip())
                                if len(key_values) >= 2:  # Utiliser 2 valeurs pour la clé
                                    break
                        
                        item_key = '|'.join(key_values) if key_values else str(len(unique_items))
                        
                        if item_key not in seen_items:
                            unique_items.append(item)
                            seen_items.add(item_key)
                    
                    if unique_items:
                        # Créer le DataFrame pour cette image
                        df = pd.DataFrame(unique_items)
                        
                        # Réorganiser les colonnes : données importantes d'abord, métadonnées à la fin
                        priority_columns = []
                        regular_columns = []
                        meta_columns = []
                        
                        for col in df.columns:
                            if col in ['Table_Type', 'Source_Image']:
                                meta_columns.append(col)
                            elif any(priority in col.upper() for priority in ['ARME', 'NOM', 'OBJET', 'VEHICULE']):
                                priority_columns.append(col)
                            else:
                                regular_columns.append(col)
                        
                        # Nouvelle organisation des colonnes
                        new_column_order = priority_columns + regular_columns + meta_columns
                        df = df[new_column_order]
                        
                        dataframes_by_image[dataset_name] = df
                        logger.info(f"🎯 Dataset créé '{dataset_name}': {len(df)} éléments uniques")
                
            processed_count += 1
        
        if not dataframes_by_image:
            logger.warning("❌ Aucun dataset créé - aucun tableau détecté")
        else:
            logger.info(f"🎉 {len(dataframes_by_image)} datasets créés (1 par image):")
            for name, df in dataframes_by_image.items():
                logger.info(f"   📊 {name}: {len(df)} éléments")
        
        return dataframes_by_image

    def export_all_dataframes(self, dataframes: Dict[str, pd.DataFrame]):
        """Exporte tous les DataFrames en code Python avec nommage parfait - 1 dataset par image"""
        try:
            # Créer le dossier de sortie
            output_dir = Path("flashback_dataframes")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            
            for dataset_name, df in dataframes.items():
                if not df.empty:
                    # Nom de fichier propre et organisé
                    clean_dataset_name = f"dataset_{dataset_name}"
                    
                    # Export Python code avec nommage parfait
                    py_file = output_dir / f"flashback_{clean_dataset_name}_data.py"
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write("import pandas as pd\n\n")
                        f.write(f"# Dataset FlashBack FA - {dataset_name}\n")
                        f.write(f"# Extrait par IA GPT-4 Vision depuis l'image correspondante\n")
                        f.write(f"# DÉTECTION AUTOMATIQUE PAR INTELLIGENCE ARTIFICIELLE\n")
                        f.write(f"# Timestamp: {timestamp}\n")
                        f.write(f"# Total éléments: {len(df)}\n\n")
                        
                        # Variables avec noms propres et cohérents
                        var_name = f"{clean_dataset_name}_data"
                        df_name = f"{clean_dataset_name}_df"
                        
                        f.write(f"{var_name} = {df_name} = pd.DataFrame([\n")
                        
                        for _, row in df.iterrows():
                            f.write("    {")
                            items = []
                            for col in df.columns:
                                value = row[col] if pd.notna(row[col]) else ""
                                # Échapper les guillemets dans les valeurs
                                escaped_value = str(value).replace('"', '\\"')
                                items.append(f'"{col}": "{escaped_value}"')
                            f.write(", ".join(items))
                            f.write("},\n")
                        
                        f.write("])\n\n")
                        
                        # Ajouter des exemples d'utilisation
                        f.write(f"# Utilisation:\n")
                        f.write(f"# from flashback_dataframes.flashback_{clean_dataset_name}_data import {var_name}, {df_name}\n")
                        f.write(f"# print({df_name}.head())\n")
                        f.write(f"# print(f'{{len({df_name})}} éléments dans ce dataset')\n\n")
                        
                        # Statistiques du dataset
                        f.write(f"# Statistiques du dataset:\n")
                        f.write(f"# - Nombre d'éléments: {len(df)}\n")
                        f.write(f"# - Colonnes: {list(df.columns)}\n")
                        
                        # Types de tableaux détectés
                        if 'Table_Type' in df.columns:
                            table_types = df['Table_Type'].value_counts().to_dict()
                            f.write(f"# - Types détectés: {dict(table_types)}\n")
                    
                    logger.info(f"✅ '{dataset_name}' exporté vers {py_file}")
                    logger.info(f"   📝 Variables: {var_name}, {df_name}")
                    logger.info(f"   📊 {len(df)} éléments dans ce dataset")
            
            logger.info(f"📁 Tous les datasets exportés dans: {output_dir.absolute()}")
            logger.info(f"🎯 Organisation: 1 fichier Python = 1 image analysée")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}")

def clean_output_directory(output_dir: str = "flashback_dataframes"):
    """Nettoie complètement le dossier de sortie avant la nouvelle extraction"""
    output_path = Path(output_dir)
    
    if output_path.exists():
        try:
            # Supprimer tout le dossier et son contenu
            shutil.rmtree(output_path)
            print(f"🗑️ Dossier {output_dir}/ vidé (anciens datasets supprimés)")
        except Exception as e:
            print(f"⚠️ Impossible de vider {output_dir}/: {e}")
    
    # Recréer le dossier vide
    try:
        output_path.mkdir(exist_ok=True)
        print(f"📁 Dossier {output_dir}/ recréé (prêt pour nouveaux datasets)")
    except Exception as e:
        print(f"❌ Impossible de créer {output_dir}/: {e}")

def main():
    """Fonction principale"""
    print("🎮 FLASHBACK FA - EXTRACTEUR IA UNIVERSEL")
    print("🤖 ANALYSE PAR INTELLIGENCE ARTIFICIELLE GPT-4 VISION")
    print("📊 EXTRACTION DE TOUS LES TABLEAUX (armes, véhicules, objets, etc.)")
    print("=" * 70)
    
    # Nettoyer le dossier de sortie avant de commencer
    clean_output_directory()
    
    # Vérifier la clé API
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Clé API OpenAI non trouvée!")
        print()
        print("🔧 Solutions:")
        print("   1. Définir la variable d'environnement: export OPENAI_API_KEY=your_api_key")
        print("   2. Ou créer un fichier .env avec: OPENAI_API_KEY=your_api_key")
        print()
        print("💡 Obtenez votre clé API sur: https://platform.openai.com/api-keys")
        return
    
    print(f"✅ Clé API OpenAI configurée (***{api_key[-6:]})")
    
    # Créer l'extracteur IA
    ai_extractor = UniversalTableExtractorAI("flashback_images")
    
    # Vérifier le dossier d'images
    if not ai_extractor.images_dir.exists():
        print(f"❌ Dossier {ai_extractor.images_dir} non trouvé!")
        print("   Lancez d'abord le scraper pour télécharger les images.")
        return
    
    # Compter les images
    image_count = sum(1 for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp'] 
                     for _ in ai_extractor.images_dir.glob(ext))
    
    if image_count == 0:
        print(f"❌ Aucune image trouvée dans {ai_extractor.images_dir}")
        return
    
    print(f"📷 {image_count} images trouvées pour analyse IA")
    
    # Traiter les images avec l'IA
    print("\n🤖 Analyse par intelligence artificielle...")
    print("🔍 GPT-4 Vision va analyser chaque image et extraire TOUS les tableaux")
    print("📊 Détection automatique: armes, véhicules, objets, immobilier, emplois, etc.")
    dataframes_by_image = ai_extractor.process_all_images()
    
    if dataframes_by_image:
        total_elements = sum(len(df) for df in dataframes_by_image.values())
        print(f"\n📊 {total_elements} éléments détectés par l'IA dans {len(dataframes_by_image)} images!")
        
        print("\n🔤 Aperçu des données extraites par IA:")
        for name, df in dataframes_by_image.items():
            print(f"\n--- {name} ({len(df)} éléments) ---")
            print(df.head(3))  # Afficher 3 premières lignes
        
        # Exporter au format demandé
        ai_extractor.export_all_dataframes(dataframes_by_image)
        print("\n✅ Données IA exportées vers le dossier flashback_dataframes/")
        
        # Statistiques détaillées
        print(f"\n📈 Statistiques complètes:")
        for name, df in dataframes_by_image.items():
            print(f"   📋 {name}: {len(df)} éléments")
            # Afficher les colonnes principales
            main_columns = [col for col in df.columns if not col.startswith('Source_') and col != 'Table_Type']
            print(f"      Colonnes: {', '.join(main_columns[:5])}" + ("..." if len(main_columns) > 5 else ""))
        
        print(f"\n🎯 TOTAL: {total_elements} éléments extraits automatiquement par l'IA!")
        print("🎮 Organisation parfaite: 1 dataset par image analysée!")
        print("📁 Fichiers générés dans flashback_dataframes/ :")
        for name, df in dataframes_by_image.items():
            print(f"   📄 flashback_dataset_{name}_data.py ({len(df)} éléments)")
        
    else:
        print("❌ Aucun tableau détecté par l'IA.")
        print("   Vérifiez que les images contiennent des tableaux de données lisibles.")
        print("   L'IA recherche: armes, véhicules, objets, immobilier, emplois, etc.")

if __name__ == "__main__":
    main() 
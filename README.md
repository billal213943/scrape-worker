# 🎮 FlashBack FA - Extracteur de Données Intelligent

Un système complet d'extraction automatisée de données pour le serveur GTA RP **FlashBack FA**, utilisant le web scraping avancé et l'intelligence artificielle GPT-4 Vision pour analyser et structurer les tableaux d'armes, véhicules et règlements.

## 🚀 Fonctionnalités

### 🕷️ **Web Scraping Intelligent**
- **Crawling automatique** : Parcourt toutes les pages du site FlashBack FA 
- **Détection de navbar** : Trouve automatiquement les sections (GÉNÉRAL, SERVICES PUBLICS, ILLÉGAL, ENTREPRISE)
- **Extraction d'images optimisée** : Filtrage intelligent des tableaux de données
- **Anti-doublons** : Détection par hash MD5 du contenu
- **Parallélisation** : 4-8 requêtes simultanées respectueuses

### 🤖 **Intelligence Artificielle GPT-4 Vision**
- **Analyse automatique** : Reconnaissance des tableaux d'armes, véhicules, règlements
- **Extraction structurée** : Conversion en DataFrames Python propres
- **Types détectés** : Armes de poing, fusils, armes automatiques, armes lourdes, véhicules, actions
- **Validation intelligente** : Normalisation des prix, autorisations, munitions

### 🔄 **Pipeline Automatisé**
- **Workflow complet** : Scraping → Analyse IA → Export données
- **Gestion d'erreurs** : Fallbacks et récupération automatique
- **Configuration guidée** : Setup OpenAI API automatique
- **Rapports détaillés** : Statistiques et progress tracking

## 📊 Résultats Actuels

**59 éléments extraits** répartis en **11 datasets spécialisés** avec des données structurées sur les armes, véhicules et règlements du serveur FlashBack FA.

## 📦 Installation

### 1. Télécharger le projet

```bash
git clone <votre-repo>
cd flashback-ocr-worker
```

### 2. Installation automatique

```bash
python install_dependencies.py
```

Le script installera automatiquement :
- `requests`, `beautifulsoup4`, `aiohttp`, `aiofiles`
- `pandas`, `openai`, `pillow`
- Avec fallbacks en cas d'erreur

### 3. Configuration OpenAI API

```bash
python setup_openai.py
```

Obtenez votre clé API sur : https://platform.openai.com/api-keys

## 🎯 Usage

### 🚀 Pipeline Complet (Recommandé)

```bash
python pipeline_flashback.py
```

**Ce script fait tout automatiquement :**
1. ✅ Vérifie les prérequis (API OpenAI, modules)
2. 🕷️ Lance le scraping du site FlashBack FA
3. 🤖 Analyse toutes les images avec GPT-4 Vision
4. 📊 Génère les datasets Python dans `flashback_dataframes/`
5. 📈 Affiche les statistiques complètes

### 🔧 Usage Manuel

#### Scraping seul :
```bash
python flashback_scraper.py
```

#### Extraction IA seule :
```bash
python image_to_dataframe.py
```

## 📁 Structure du Projet

```
flashback-ocr-worker/
├── 🕷️ flashback_scraper.py      # Scraper spécialisé FlashBack FA
├── 🤖 image_to_dataframe.py     # Extracteur IA GPT-4 Vision
├── 🔄 pipeline_flashback.py     # Pipeline automatisé complet
├── 📦 install_dependencies.py   # Installateur intelligent
├── 🔑 setup_openai.py          # Configuration API OpenAI
├── ⚙️ config.py                # Configurations
├── 📋 requirements.txt         # Dépendances
├── 📷 flashback_images/        # Images téléchargées
└── 📊 flashback_dataframes/    # Datasets générés
    ├── flashback_armes_de_poings_data.py
    ├── flashback_fusil_a_pompe_data.py
    ├── flashback_armes_automatique_data.py
    ├── flashback_armes_lourdes_data.py
    ├── flashback_actions_data.py
    └── ...
```

## ⚙️ Configuration

### Variables d'Environnement

```bash
# .env
OPENAI_API_KEY=sk-your-api-key-here
```

### Personnalisation du Scraper

```python
# Modifier les paramètres dans flashback_scraper.py
scraper = FlashBackScraper(
    max_concurrent=8,           # Requêtes simultanées
    delay_between_requests=0.5, # Délai entre requêtes
    timeout=45                  # Timeout par requête
)
```

## 🤖 IA GPT-4 Vision

Le système utilise **GPT-4o** avec des prompts optimisés pour :

- **Détection automatique** : Reconnaissance des tableaux d'armes/véhicules
- **Extraction précise** : Noms, prix, munitions, autorisations
- **Normalisation** : Conversion `✓/✗` → `autoriser/interdit`
- **Validation** : Vérification de cohérence des données

### Coût Estimé

- **~0.012$ par image** avec GPT-4o (coût réel constaté)
- **Extraction complète (5 images)** : ~0.06$ (6 centimes)
- Extraction de **59 éléments** structurés

⚠️ **Attention :** Les coûts GPT-4 Vision sont plus élevés que prévu ! Comptez environ **1.2 centimes par image**.

## 📈 Statistiques du Projet

- **2,223 lignes de code** au total
- **79.8%** Code source Python (1,774 lignes)
- **9.6%** Datasets IA générés (213 lignes)
- **10.6%** Documentation/Config (236 lignes)

## 🔧 Résolution de Problèmes

### Erreurs Communes

**1. Clé API OpenAI manquante**
```bash
❌ Clé API OpenAI non trouvée!
```
**Solution :** `python setup_openai.py`

**2. Modules manquants**
```bash
❌ Module 'openai' not found
```
**Solution :** `python install_dependencies.py`

**3. Aucune image trouvée**
```bash
❌ Aucune image trouvée dans flashback_images
```
**Solution :** Lancer d'abord `python flashback_scraper.py`

**4. Erreur JSON GPT-4**
```bash
❌ Erreur JSON pour image...
```
**Solution :** L'IA retente automatiquement avec nettoyage JSON

### Logs Détaillés

Pour plus de détails, modifiez le logging :

```python
# Dans image_to_dataframe.py
logging.basicConfig(level=logging.DEBUG)
```

## 🚨 Avertissements

- **Usage responsable** : Respectez les robots.txt et ToS
- **Rate limiting** : Le scraper est configuré pour être respectueux
- **Coûts IA** : GPT-4 Vision a un coût par requête
- **Site officiel uniquement** : Conçu pour le site FlashBack FA officiel

## 🏆 Crédits

Développé pour le serveur **FlashBack FA** - Extraction automatisée des règlements et données d'armes par intelligence artificielle.

**Site analysé :** https://sites.google.com/view/reglement-flashback-fa/ 
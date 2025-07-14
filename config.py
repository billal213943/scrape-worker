"""
Configuration pour le worker de scraping d'images
"""

# Configuration par défaut du scraper
DEFAULT_CONFIG = {
    # URL du site à scraper (à modifier)
    "base_url": "https://example.com",
    
    # Répertoire de sortie pour les images
    "output_dir": "scraped_images",
    
    # Nombre maximum de requêtes simultanées
    "max_concurrent": 15,
    
    # Nombre maximum de pages à crawler
    "max_pages": 1000,
    
    # Délai entre les requêtes (en secondes) - réduire pour plus de vitesse
    "delay_between_requests": 0.05,
    
    # Timeout pour les requêtes HTTP
    "timeout": 30,
    
    # Extensions d'images à rechercher
    "image_extensions": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
    
    # Extensions de fichiers à ignorer lors du crawling
    "ignore_extensions": ['.pdf', '.doc', '.docx', '.zip', '.rar', '.exe', '.dmg'],
    
    # Headers HTTP pour simuler un navigateur
    "user_agents": [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
}

# Configurations prédéfinies pour différents types de sites
SITE_CONFIGS = {
    "ecommerce": {
        "max_concurrent": 20,
        "delay_between_requests": 0.1,
        "max_pages": 2000,
    },
    
    "blog": {
        "max_concurrent": 10,
        "delay_between_requests": 0.2,
        "max_pages": 500,
    },
    
    "gallery": {
        "max_concurrent": 25,
        "delay_between_requests": 0.05,
        "max_pages": 1500,
    },
    
    "social": {
        "max_concurrent": 30,
        "delay_between_requests": 0.02,
        "max_pages": 3000,
    }
}

def get_config(site_type: str = "default") -> dict:
    """
    Retourne la configuration pour un type de site donné
    
    Args:
        site_type: Type de site ('default', 'ecommerce', 'blog', 'gallery', 'social')
    
    Returns:
        dict: Configuration fusionnée
    """
    config = DEFAULT_CONFIG.copy()
    
    if site_type in SITE_CONFIGS:
        config.update(SITE_CONFIGS[site_type])
    
    return config 
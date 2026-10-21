"""
RUANG VISUAL - Franchise Negative Filter
=========================================
Modul untuk menyaring dan memblokir 100% brand waralaba nasional/multinasional
yang keputusan cetak terpusat di kantor pusat Jakarta.

Target: McDonald's, KFC, Starbucks, Mixue, Indomaret, dll harus drop di awal pipa data.
Bebas emoji sesuai aturan operasional RUANG VISUAL.
"""

import re


NATIONAL_FRANCHISE_BLACKLIST = [
    # Fast Food & Restaurant Chains
    "mcdonald", "mcd ", "mcdo", "mekdi",
    "kfc", "kentucky fried chicken",
    "pizza hut", "phd", "pizza hot",
    "burger king", "bk ",
    "domino", "domino's pizza",
    "a&w", "a & w", "a and w",
    "hokben", "hoka hoka bento",
    "richeese", "richeese factory",
    "solaria",
    "mie gacoan", "gacoan",
    "marugame udon", "marugame",
    "subway sandwich",
    "yoshinoya",
    "pepper lunch",
    "wendy's", "wendys",
    "texas chicken",
    "bakmi gm", "bakmi general manager",
    "hisana fried chicken",
    "ayam geprek bensu",
    "geprek bensu",
    
    # Kopi & Minuman Waralaba
    "starbucks", "sbux",
    "janji jiwa",
    "kopi kenangan", "kenangan",
    "fore coffee", "fore",
    "kopi lain hati",
    "point coffee",
    "chatime",
    "xi bo ba", "xiboba",
    "mixue", "mixue ice cream",
    "haus!", "haus",
    "gulu gulu",
    "kopi tuku",
    "kopi soe",
    "onezo",
    "kokumi",
    
    # Retail & Minimarket Chains
    "indomaret",
    "alfamart", "alfa mart",
    "alfamidi", "alfa midi",
    "circle k",
    "lawson",
    "familymart", "family mart",
    
    # Retail Fashion & Lifestyle Chains
    "miniso",
    "mr. diy", "mr diy", "mister diy",
    "guardian", "guardian pharmacy",
    "watsons", "watson",
    "ace hardware",
    "informa",
    "ikea",
    "h&m", "h & m",
    "uniqlo",
    "zara",
    "pull & bear",
    "stradivarius",
    "bershka",
    
    # Bakery & Dessert Chains
    "breadtalk", "bread talk",
    "j.co", "jco", "j co donuts",
    "dunkin donuts", "dunkin", "dunkin'",
    "krispy kreme",
    "the harvest",
    "tous les jours",
    "bread life",
    
    # Hotel & Hospitality Chains
    "maxone", "max one hotel",
    "reddoorz", "red doorz",
    "oyo",
    "airy rooms",
    "pop! hotel",
    
    # Apotik & Farmasi Chains
    "kimia farma",
    "century healthcare",
    "k-24", "k24",
    "viva generik",
    
    # Telco & Tech
    "gojek", "go-jek",
    "grab",
    "tokopedia",
    "shopee",
    "bukalapak",
    "lazada",
]


def is_national_franchise(business_name: str) -> bool:
    """
    Deteksi apakah nama bisnis adalah brand waralaba nasional/multinasional.
    
    Args:
        business_name: Nama bisnis dari Google Maps/platform lain
        
    Returns:
        True jika terdeteksi sebagai franchise (harus diblokir)
        False jika UMKM lokal mandiri (aman untuk prospek)
    """
    if not business_name:
        return False
    
    name_clean = business_name.lower().strip()
    name_clean = re.sub(r'[^a-z0-9\s]', ' ', name_clean)
    name_clean = ' ' + name_clean + ' '
    
    for franchise_brand in NATIONAL_FRANCHISE_BLACKLIST:
        pattern = franchise_brand.replace('!', '').strip()
        if pattern in name_clean:
            return True
    
    return False


def filter_franchise_from_leads(leads: list) -> tuple[list, list]:
    """
    Pisahkan lead UMKM lokal dari franchise nasional.
    
    Args:
        leads: List of lead dictionaries
        
    Returns:
        Tuple (clean_leads, blocked_franchises)
    """
    clean_leads = []
    blocked_franchises = []
    
    for lead in leads:
        nama = lead.get("nama_bisnis", "")
        if is_national_franchise(nama):
            blocked_franchises.append(lead)
        else:
            clean_leads.append(lead)
    
    return clean_leads, blocked_franchises

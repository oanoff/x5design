import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'

EXCEL_FILE = DATA_DIR / 'map.xlsx'
EMPLOYEES_CSV = DATA_DIR / 'employees.csv'
LEADS_ADMINS_CSV = DATA_DIR / 'leads_admins.csv'
RECOMMENDATIONS_CSV = DATA_DIR / 'recommendations.csv'
RESULTS_CSV = DATA_DIR / 'results.csv'

HARD_SHEET = 'Узкоспециализированные (Hard)'
SOFT_SHEET = 'Общепрофессиональные (Soft)'

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения")
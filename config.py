import os

BOT_TOKEN = "ВАШ_ТОКЕН"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

MATRIX_FILE = os.path.join(DATA_DIR, "matrix.xlsx")
EMPLOYEES_FILE = os.path.join(DATA_DIR, "employees.csv")
ADMINS_LEADS_FILE = os.path.join(DATA_DIR, "admins_leads.csv")
RECOMMENDATIONS_FILE = os.path.join(DATA_DIR, "recommendations.csv")
RESULTS_FILE = os.path.join(RESULTS_DIR, "results.csv")

# Убедимся, что папка results существует
os.makedirs(RESULTS_DIR, exist_ok=True)
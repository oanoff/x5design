import pandas as pd
from config import EXCEL_FILE, EMPLOYEES_CSV, LEADS_ADMINS_CSV, RECOMMENDATIONS_CSV, RESULTS_CSV, HARD_SHEET, SOFT_SHEET

def load_skills():
    """Загружает навыки из листов Hard и Soft, возвращает DataFrame с колонками skill, Junior, Middle, Senior, category"""
    def clean_skills(df, category):
        skill_col = df.columns[0]
        junior_col = middle_col = senior_col = None
        for col in df.columns:
            if 'Младший' in col:
                junior_col = col
            elif 'Обычный' in col:
                middle_col = col
            elif 'Ведущий' in col:
                senior_col = col
        if not junior_col or not middle_col or not senior_col:
            raise ValueError("Не найдены столбцы с грейдами в листе")
        df_clean = df[[skill_col, junior_col, middle_col, senior_col]].copy()
        df_clean.columns = ['skill', 'Junior', 'Middle', 'Senior']
        df_clean = df_clean.dropna(subset=['skill'])
        df_clean = df_clean[~df_clean['skill'].str.contains('Легенда', na=False)]
        df_clean = df_clean[df_clean['skill'] != 'Навыки']
        df_clean['category'] = category
        return df_clean

    hard_df = pd.read_excel(EXCEL_FILE, sheet_name=HARD_SHEET, skiprows=4)
    soft_df = pd.read_excel(EXCEL_FILE, sheet_name=SOFT_SHEET, skiprows=4)
    hard = clean_skills(hard_df, 'Hard')
    soft = clean_skills(soft_df, 'Soft')
    return pd.concat([hard, soft], ignore_index=True)

def load_employees():
    return pd.read_csv(EMPLOYEES_CSV)

def load_leads_admins():
    return pd.read_csv(LEADS_ADMINS_CSV)

def load_recommendations():
    return pd.read_csv(RECOMMENDATIONS_CSV)

def load_results():
    if not RESULTS_CSV.exists():
        return pd.DataFrame(columns=['telegram_id', 'name', 'direction', 'date', 'scores',
                                     'avg_hard', 'avg_soft', 'overall_grade', 'recommendation', 'plan'])
    return pd.read_csv(RESULTS_CSV)

def save_result(telegram_id, name, direction, date, scores_json, avg_hard, avg_soft, grade, recommendation, plan):
    df = load_results()
    new_row = pd.DataFrame([[telegram_id, name, direction, date, scores_json,
                             avg_hard, avg_soft, grade, recommendation, plan]],
                           columns=df.columns)
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(RESULTS_CSV, index=False)
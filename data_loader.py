import pandas as pd
from config import MATRIX_FILE, EMPLOYEES_FILE, ADMINS_LEADS_FILE, RECOMMENDATIONS_FILE

def load_employees():
    """Загружает список сотрудников из CSV."""
    return pd.read_csv(EMPLOYEES_FILE, dtype={'telegram_id': str})

def load_admins_leads():
    """Загружает администраторов и лидов."""
    return pd.read_csv(ADMINS_LEADS_FILE, dtype={'telegram_id': str})

def load_recommendations():
    """Загружает рекомендации по уровням."""
    return pd.read_csv(RECOMMENDATIONS_FILE)

def load_matrix():
    """
    Загружает матрицу компетенций из Excel.
    Возвращает словарь:
    {
        'Hard': {'groups': {...}, 'skills': {...}},
        'Research': {...},
        'Soft': {...}
    }
    """
    xls = pd.ExcelFile(MATRIX_FILE)
    matrix = {}
    
    # Определяем, какие листы относятся к каким категориям
    # (можно задать вручную или парсить по названиям)
    sheet_mapping = {
        'Узкоспециализированные (Hard)': 'Hard',
        'Узкоспециализированные Исследов': 'Research',
        'Общепрофессиональные (Soft)': 'Soft'
    }
    
    for sheet_name, category in sheet_mapping.items():
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        # Парсим структуру: группы и навыки
        groups = {}
        skills = {}
        current_group = None
        
        # Находим строку с заголовками (Навыки, Анна, Борис, ...)
        # В каждом листе заголовок в строке 4 (индекс 3), но может отличаться
        # Будем искать ячейку со значением "Навыки"
        header_row = None
        for i in range(10):
            if df.iloc[i, 1] == 'Навыки':
                header_row = i
                break
        if header_row is None:
            continue
        
        # Читаем названия уровней (Младший, Обычный, Ведущий и т.д.)
        # Они находятся в правой части таблицы
        # В листах Hard и Soft есть колонки O, P, Q (индексы 14,15,16)
        # В Research - колонки K, L, M (индексы 10,11,12)
        # Определим индексы для уровней по наличию столбцов с названиями
        # Проще: ищем строки, где есть "Младший", "Обычный", "Ведущий"
        levels_row = None
        for i in range(header_row, header_row + 5):
            row = df.iloc[i].astype(str)
            if 'Младший' in row.values:
                levels_row = i
                break
        if levels_row is None:
            continue
        
        # Определим индексы столбцов уровней
        level_cols = {}
        for idx, val in enumerate(df.iloc[levels_row]):
            if isinstance(val, str) and val in ['Младший', 'Обычный', 'Ведущий']:
                level_cols[val] = idx
        
        # Теперь проходим по строкам, начиная с header_row+1
        for idx in range(header_row+1, len(df)):
            row = df.iloc[idx]
            skill_name = str(row[1]) if pd.notna(row[1]) else ''
            if not skill_name or skill_name == 'nan':
                continue
            # Если строка содержит 'Всего' или 'Картина по команде' - пропускаем
            if 'Всего' in skill_name or 'Картина' in skill_name:
                continue
            # Если это группа (нет отступа в начале) - запоминаем
            # В исходных данных группы имеют более крупный шрифт, но в тексте мы видим, что они идут без отступа
            # Проверим, является ли строка группой: если следующие строки содержат поднавыки
            # Простой эвристический подход: если строка не начинается с пробела и не содержит цифр в ячейке с навыком (оценка)
            # Но лучше использовать структуру: в некоторых листах группы выделены жирным, но мы можем определить по тому, что в строке группы есть формула AVERAGE для всех сотрудников.
            # В данных: строка группы (например, "Информационная архитектура и проектирование интерфейсов") имеет в столбцах C:L формулы =AVERAGE(C6:C9) и т.д.
            # Мы можем проверить, является ли значение в колонке C формулой.
            # В pandas read_excel формулы не вычисляются, мы видим только результаты.
            # Но мы можем посмотреть, что в строке группы в столбце C стоит число, а не формула (но в Excel это формула, но при чтении pandas возвращает вычисленное значение).
            # У нас нет надежного способа отличить группу от поднавыка, кроме как по именам.
            # Я предлагаю использовать предопределенный список групп из вашего файла:
            group_names = [
                'Информационная архитектура и проектирование интерфейсов',
                'Визуальный дизайн',
                'Пользовательские исследования',
                'Продуктовое мышление и аналитика',
                'Редактура',
                'Фронт-енд'
            ]
            # Для Research листа:
            if category == 'Research':
                group_names = [
                    'Разведочные исследования',
                    'Описание пользователей',
                    'Проверка дизайн-решений',
                    'Внедрение результатов исследований',
                    'Ведение проектов',
                    'Продуктовое мышление и аналитика'
                ]
            # Для Soft листа:
            if category == 'Soft':
                group_names = [
                    'Ориентация на достижения',
                    'Коммуникация и командная работа',
                    'Креативное мышление',
                    'Системное мышление'
                ]
            
            if skill_name in group_names:
                current_group = skill_name
                groups[current_group] = []
                continue
            elif current_group is not None:
                # Это навык
                # Проверим, есть ли значения для уровней
                skill_data = {}
                for level, col_idx in level_cols.items():
                    val = row[col_idx] if col_idx < len(row) else None
                    skill_data[level] = float(val) if pd.notna(val) else None
                # Если все значения None, пропускаем
                if all(v is None for v in skill_data.values()):
                    continue
                # Сохраняем навык
                skill_key = skill_name
                skills[skill_key] = {
                    'group': current_group,
                    'levels': skill_data
                }
                groups[current_group].append(skill_key)
        
        matrix[category] = {
            'groups': groups,
            'skills': skills
        }
    
    return matrix
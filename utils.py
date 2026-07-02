import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
from config import RESULTS_FILE
from models import SurveyResult

def calculate_level(scores: dict, skills_matrix: dict) -> str:
    """
    Вычисляет уровень дизайнера на основе его самооценок и эталонов.
    Используется средняя абсолютная ошибка по всем навыкам.
    """
    # Собираем все навыки из матрицы (только те, которые есть в опросе)
    all_skills = []
    for category, data in skills_matrix.items():
        all_skills.extend(data['skills'].values())
    
    # Фильтруем только те навыки, которые есть в scores
    common_skills = [s for s in all_skills if s.name in scores]
    if not common_skills:
        return 'Не определено'
    
    # Для каждого уровня вычисляем среднюю ошибку
    levels = ['Младший', 'Обычный', 'Ведущий']
    errors = {}
    for level in levels:
        errors_level = []
        for skill in common_skills:
            target = skill.levels.get(level)
            if target is not None:
                actual = scores.get(skill.name, 0)
                errors_level.append(abs(actual - target))
        if errors_level:
            errors[level] = np.mean(errors_level)
        else:
            errors[level] = float('inf')
    
    # Выбираем уровень с минимальной ошибкой
    best_level = min(errors, key=errors.get)
    return best_level

def generate_radar_chart(scores: dict, levels: dict, employee_name: str) -> BytesIO:
    """
    Генерирует радарную диаграмму сравнения самооценки с целевыми уровнями.
    """
    # Группируем навыки по группам и усредняем
    groups = {}
    for skill, score in scores.items():
        # Находим группу навыка
        group = None
        for cat in levels.values():
            for s in cat['skills'].values():
                if s.name == skill:
                    group = s.group
                    break
            if group:
                break
        if group:
            if group not in groups:
                groups[group] = []
            groups[group].append(score)
    
    # Усредняем по группам
    group_avg = {g: np.mean(vals) for g, vals in groups.items()}
    group_names = list(group_avg.keys())
    values = list(group_avg.values())
    
    # Для целевого уровня (например, 'Обычный') берем эталоны
    target_level = 'Обычный'  # Можно определить на основе вычисленного уровня
    target_values = []
    for g in group_names:
        # Находим среднее эталонное значение для группы
        group_skills = []
        for cat in levels.values():
            for s in cat['skills'].values():
                if s.group == g:
                    group_skills.append(s.levels.get(target_level, 0))
        if group_skills:
            target_values.append(np.mean(group_skills))
        else:
            target_values.append(0)
    
    # Построение радара
    angles = np.linspace(0, 2 * np.pi, len(group_names), endpoint=False).tolist()
    values += values[:1]
    target_values += target_values[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, 'o-', linewidth=2, label='Самооценка')
    ax.fill(angles, values, alpha=0.25)
    ax.plot(angles, target_values, 'o-', linewidth=2, label=f'Целевой ({target_level})')
    ax.fill(angles, target_values, alpha=0.1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(group_names, size=8)
    ax.set_ylim(0, 4)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    ax.set_title(f'Профиль компетенций: {employee_name}', size=12)
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close()
    return buf

def save_result(result: SurveyResult):
    """Сохраняет результат опроса в CSV."""
    # Проверяем, существует ли файл
    if not pd.io.common.file_exists(RESULTS_FILE):
        df = pd.DataFrame(columns=['telegram_id', 'full_name', 'direction', 'date', 'level', 'average_score'] +
                          list(result.scores.keys()))
    else:
        df = pd.read_csv(RESULTS_FILE)
        # Если пользователь уже проходил опрос, удаляем старую запись (или обновляем)
        df = df[df['telegram_id'] != result.telegram_id]
    
    # Создаем новую запись
    new_row = {
        'telegram_id': result.telegram_id,
        'full_name': result.full_name,
        'direction': result.direction,
        'date': result.date,
        'level': result.level,
        'average_score': result.average_score
    }
    # Добавляем оценки по навыкам
    for skill, score in result.scores.items():
        new_row[skill] = score
    
    # Добавляем строку
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(RESULTS_FILE, index=False)
import json
import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

def calculate_grade(scores, skill_list, benchmark_dict):
    """Определяет грейд как минимальное среднеквадратичное отклонение от эталонов"""
    grades = ['Junior', 'Middle', 'Senior']
    errors = {}
    for grade in grades:
        total = 0
        for i, skill in enumerate(skill_list):
            total += (scores[i] - benchmark_dict[skill][grade]) ** 2
        errors[grade] = total
    return min(errors, key=errors.get)

def generate_radar_chart(scores, skill_list, grade, benchmark_dict):
    """Строит горизонтальную гистограмму сравнения с эталоном"""
    benchmark = [benchmark_dict[skill][grade] for skill in skill_list]
    df = pd.DataFrame({'skill': skill_list, 'user': scores, 'benchmark': benchmark})
    df['diff'] = df['user'] - df['benchmark']
    df = df.sort_values('diff', ascending=False)

    fig, ax = plt.subplots(figsize=(10, 8))
    y = range(len(df))
    ax.barh(y, df['user'], color='skyblue', label='Ваша оценка')
    ax.barh(y, df['benchmark'], color='orange', alpha=0.7, label=f'Эталон ({grade})')
    ax.set_yticks(y)
    ax.set_yticklabels(df['skill'])
    ax.invert_yaxis()
    ax.set_xlabel('Уровень (1–4)')
    ax.set_title(f'Сравнение с эталоном для грейда {grade}')
    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def generate_team_stats(results, employees):
    """Строит круговую диаграмму распределения грейдов"""
    if results.empty:
        return None
    counts = results['overall_grade'].value_counts()
    fig, ax = plt.subplots()
    ax.pie(counts, labels=counts.index, autopct='%1.1f%%')
    ax.set_title('Распределение по грейдам')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf
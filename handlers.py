from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd
from datetime import datetime
from config import *
from data_loader import load_employees, load_admins_leads, load_recommendations, load_matrix
from models import Employee, AdminLead, Skill
from utils import calculate_level, generate_radar_chart, save_result, SurveyResult

# Состояния опроса
class SurveyStates(StatesGroup):
    START = State()
    ASKING_SKILL = State()
    FINISHED = State()

# Глобальные переменные для данных
employees = None
admins_leads = None
recommendations = None
matrix = None

def setup_data():
    global employees, admins_leads, recommendations, matrix
    employees = load_employees()
    admins_leads = load_admins_leads()
    recommendations = load_recommendations()
    matrix = load_matrix()

def get_user_role(telegram_id: str):
    """Определяет роль пользователя: 'employee', 'lead', 'admin'."""
    if telegram_id in admins_leads['telegram_id'].values:
        row = admins_leads[admins_leads['telegram_id'] == telegram_id].iloc[0]
        role = row['role']
        if role == 'admin':
            return 'admin', None
        elif role == 'lead':
            return 'lead', row.get('direction', None)
    elif telegram_id in employees['telegram_id'].values:
        return 'employee', None
    else:
        return 'unknown', None

def get_employee(telegram_id: str):
    """Возвращает объект Employee или None."""
    if telegram_id in employees['telegram_id'].values:
        row = employees[employees['telegram_id'] == telegram_id].iloc[0]
        return Employee(telegram_id=row['telegram_id'], full_name=row['full_name'], direction=row['direction'])
    return None

def get_skills_for_direction(direction: str):
    """Возвращает список навыков для направления."""
    skills = []
    if direction == 'Product':
        for cat in ['Hard', 'Soft']:
            if cat in matrix:
                for skill_name, skill_data in matrix[cat]['skills'].items():
                    skills.append(Skill(name=skill_name, group=skill_data['group'], levels=skill_data['levels']))
    elif direction == 'Research':
        for cat in ['Research', 'Soft']:
            if cat in matrix:
                for skill_name, skill_data in matrix[cat]['skills'].items():
                    skills.append(Skill(name=skill_name, group=skill_data['group'], levels=skill_data['levels']))
    else:
        # По умолчанию все
        for cat in matrix:
            for skill_name, skill_data in matrix[cat]['skills'].items():
                skills.append(Skill(name=skill_name, group=skill_data['group'], levels=skill_data['levels']))
    return skills

# Обработчики команд
async def cmd_start(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    role, direction = get_user_role(telegram_id)
    
    if role == 'unknown':
        await message.answer("Доступ запрещён. Ваш Telegram ID не найден в базе.")
        return
    
    if role == 'employee':
        emp = get_employee(telegram_id)
        if emp:
            await message.answer(f"Добро пожаловать, {emp.full_name}!\nВы зарегистрированы как дизайнер направления '{emp.direction}'. Хотите пройти опрос?")
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("Пройти опрос", callback_data="start_survey"))
            await message.answer("Нажмите кнопку ниже, чтобы начать.", reply_markup=keyboard)
            await state.update_data(employee=emp)
        else:
            await message.answer("Ошибка: данные о сотруднике не найдены.")
    
    elif role == 'lead':
        await message.answer(f"Добро пожаловать, лид направления '{direction}'!\nВы можете просматривать результаты своих дизайнеров.")
        await show_lead_dashboard(message, direction)
    
    elif role == 'admin':
        await message.answer("Добро пожаловать, администратор!\nВы имеете доступ ко всей статистике.")
        await show_admin_dashboard(message)

async def show_lead_dashboard(message: types.Message, direction: str):
    if pd.io.common.file_exists(RESULTS_FILE):
        df_results = pd.read_csv(RESULTS_FILE)
        df_results = df_results[df_results['direction'] == direction]
        if df_results.empty:
            await message.answer("В вашем направлении пока нет завершённых опросов.")
            return
        text = "📊 Результаты дизайнеров вашего направления:\n\n"
        for _, row in df_results.iterrows():
            text += f"👤 {row['full_name']} – Уровень: {row['level']}, Средний балл: {row['average_score']:.2f}\n"
        await message.answer(text)
    else:
        await message.answer("Нет данных о результатах.")

async def show_admin_dashboard(message: types.Message):
    if pd.io.common.file_exists(RESULTS_FILE):
        df_results = pd.read_csv(RESULTS_FILE)
        if df_results.empty:
            await message.answer("Нет данных о результатах.")
            return
        total = len(df_results)
        levels_count = df_results['level'].value_counts().to_dict()
        avg_score = df_results['average_score'].mean()
        
        text = f"📊 Общая статистика по команде:\n\n"
        text += f"Всего дизайнеров прошло опрос: {total}\n"
        text += f"Средний балл по команде: {avg_score:.2f}\n\n"
        text += "Распределение по уровням:\n"
        for level, count in levels_count.items():
            text += f"  {level}: {count} чел.\n"
        await message.answer(text)
        
        dir_counts = df_results['direction'].value_counts()
        text_dir = "По направлениям:\n"
        for dir_name, cnt in dir_counts.items():
            text_dir += f"  {dir_name}: {cnt} чел.\n"
        await message.answer(text_dir)
    else:
        await message.answer("Нет данных о результатах.")

async def start_survey(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    emp = data.get('employee')
    if not emp:
        await callback.message.answer("Ошибка: не удалось определить сотрудника.")
        return
    
    skills = get_skills_for_direction(emp.direction)
    if not skills:
        await callback.message.answer("Для вашего направления нет навыков в матрице.")
        return
    
    await state.update_data(skills=skills, current_index=0, scores={})
    # Теперь вызываем ask_skill, которая сама установит состояние ASKING_SKILL
    await ask_skill(callback.message, state)

async def ask_skill(message: types.Message, state: FSMContext):
    # Устанавливаем состояние, чтобы обработчик process_score мог его перехватить
    await SurveyStates.ASKING_SKILL.set()
    
    data = await state.get_data()
    skills = data['skills']
    index = data.get('current_index', 0)
    scores = data.get('scores', {})
    
    if index >= len(skills):
        # Все вопросы заданы – завершаем
        await finish_survey(message, state)
        return
    
    skill = skills[index]
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = []
    for val in range(5):
        buttons.append(InlineKeyboardButton(str(val), callback_data=f"score_{val}"))
    keyboard.add(*buttons)
    scale_desc = "0 - Нет навыка\n1 - Осведомлённость\n2 - Умение\n3 - Экспертиза\n4 - Лидерство"
    await message.answer(
        f"Вопрос {index+1}/{len(skills)}\nНавык: *{skill.name}*\nГруппа: {skill.group}\n\nОцените свой уровень по шкале:\n{scale_desc}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.update_data(current_index=index, scores=scores)

async def process_score(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    score = int(callback.data.split('_')[1])
    data = await state.get_data()
    skills = data['skills']
    index = data.get('current_index', 0)
    scores = data.get('scores', {})
    
    skill = skills[index]
    scores[skill.name] = score
    await state.update_data(scores=scores, current_index=index+1)
    
    # Переход к следующему вопросу
    await ask_skill(callback.message, state)

async def finish_survey(message: types.Message, state: FSMContext):
    data = await state.get_data()
    emp = data['employee']
    scores = data['scores']
    
    avg_score = sum(scores.values()) / len(scores) if scores else 0
    level = calculate_level(scores, matrix)
    
    result = SurveyResult(
        telegram_id=emp.telegram_id,
        full_name=emp.full_name,
        direction=emp.direction,
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        scores=scores,
        average_score=avg_score,
        level=level
    )
    save_result(result)
    
    rec_df = load_recommendations()
    rec_row = rec_df[rec_df['level'] == level]
    if not rec_row.empty:
        rec_text = rec_row.iloc[0]['recommendations']
        plan_text = rec_row.iloc[0]['development_plan']
    else:
        rec_text = "Рекомендации не найдены."
        plan_text = "План развития не найден."
    
    buf = generate_radar_chart(scores, matrix, emp.full_name)
    
    await message.answer(
        f"✅ Опрос завершён!\n\nВаш уровень: *{level}*\nСредний балл: {avg_score:.2f}\n\nРекомендации:\n{rec_text}\n\nПлан развития:\n{plan_text}",
        parse_mode="Markdown"
    )
    await message.answer_photo(photo=buf, caption="Ваш профиль компетенций (сравнение с целевым уровнем)")
    
    await state.finish()
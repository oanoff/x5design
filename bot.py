import asyncio
import logging
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile

from config import BOT_TOKEN
from data_loader import (load_skills, load_employees, load_leads_admins,
                         load_recommendations, load_results, save_result)
from states import SurveyStates
from utils import calculate_grade, generate_radar_chart, generate_team_stats

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загрузка данных
skills_df = load_skills()
employees = load_employees()
leads_admins = load_leads_admins()
recommendations = load_recommendations()

# Индексы для быстрого доступа
employee_dict = {row['telegram_id']: row for _, row in employees.iterrows()}
lead_admin_dict = {row['telegram_id']: row for _, row in leads_admins.iterrows()}

# Списки навыков
skill_list = skills_df['skill'].tolist()
hard_skills = skills_df[skills_df['category'] == 'Hard']['skill'].tolist()
soft_skills = skills_df[skills_df['category'] == 'Soft']['skill'].tolist()
hard_count = len(hard_skills)

# Эталонный словарь: {skill: {'Junior': val, 'Middle': val, 'Senior': val}}
benchmark_dict = {}
for _, row in skills_df.iterrows():
    benchmark_dict[row['skill']] = {
        'Junior': row['Junior'],
        'Middle': row['Middle'],
        'Senior': row['Senior']
    }

def get_user_role(telegram_id):
    if telegram_id in employee_dict:
        return 'employee'
    if telegram_id in lead_admin_dict:
        return lead_admin_dict[telegram_id]['role']  # 'lead' или 'admin'
    return None

# ---- Хендлеры ----

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    if role is None:
        await message.answer("❌ Вы не зарегистрированы в системе. Обратитесь к администратору.")
        return

    if role == 'employee':
        name = employee_dict[user_id]['name']
        results = load_results()
        user_results = results[results['telegram_id'] == user_id]
        if not user_results.empty:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📊 Мой результат")],
                    [KeyboardButton(text="🔄 Пройти опрос заново")]
                ],
                resize_keyboard=True
            )
            await message.answer(f"Привет, {name}! Ты уже проходил опрос. Выбери действие.", reply_markup=keyboard)
        else:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🚀 Пройти опрос")]],
                resize_keyboard=True
            )
            await message.answer(f"Привет, {name}! Давай оценим твои компетенции. Нажми кнопку, чтобы начать.", reply_markup=keyboard)

    elif role == 'lead':
        direction = lead_admin_dict[user_id]['direction']
        team = employees[employees['direction'] == direction]
        if team.empty:
            await message.answer("В твоём направлении нет дизайнеров.")
            return
        buttons = []
        for _, row in team.iterrows():
            buttons.append([InlineKeyboardButton(text=row['name'], callback_data=f"view_{row['telegram_id']}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Выбери дизайнера для просмотра результатов:", reply_markup=keyboard)

    elif role == 'admin':
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Общая статистика")],
                [KeyboardButton(text="👥 Все дизайнеры")]
            ],
            resize_keyboard=True
        )
        await message.answer("Добро пожаловать, администратор! Выбери действие.", reply_markup=keyboard)

# ---- Опрос ----

@dp.message(lambda m: m.text in ["🚀 Пройти опрос", "🔄 Пройти опрос заново"])
async def start_survey(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in employee_dict:
        await message.answer("Доступно только для дизайнеров.")
        return
    await state.set_state(SurveyStates.answering)
    await state.update_data(current_index=0, answers={})
    await ask_question(message, state)

async def ask_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get('current_index', 0)
    if idx >= len(skill_list):
        await finish_survey(message, state)
        return
    skill = skill_list[idx]
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="1"), KeyboardButton(text="2")],
                  [KeyboardButton(text="3"), KeyboardButton(text="4")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        f"❓ Вопрос {idx+1} из {len(skill_list)}\n"
        f"Навык: *{skill}*\n\n"
        "Оцени свой уровень:\n"
        "1 — Осведомлённость\n"
        "2 — Умение\n"
        "3 — Экспертиза\n"
        "4 — Лидерство\n\n"
        "Введи цифру 1–4:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@dp.message(lambda m: m.text in ['1','2','3','4'])
async def process_answer(message: types.Message, state: FSMContext):
    if await state.get_state() != SurveyStates.answering:
        return
    data = await state.get_data()
    idx = data.get('current_index', 0)
    answers = data.get('answers', {})
    skill = skill_list[idx]
    score = int(message.text)
    answers[skill] = score
    await state.update_data(answers=answers, current_index=idx+1)
    await ask_question(message, state)

@dp.message(lambda m: m.text not in ['1','2','3','4'] and m.text not in ["📊 Мой результат", "🔄 Пройти опрос заново", "🚀 Пройти опрос", "📊 Общая статистика", "👥 Все дизайнеры"])
async def invalid_during_survey(message: types.Message, state: FSMContext):
    if await state.get_state() == SurveyStates.answering:
        await message.answer("Пожалуйста, выбери цифру от 1 до 4.")

async def finish_survey(message: types.Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get('answers', {})
    scores = [answers[skill] for skill in skill_list]
    avg_hard = sum(scores[:hard_count]) / hard_count if hard_count else 0
    avg_soft = sum(scores[hard_count:]) / (len(scores) - hard_count) if (len(scores) - hard_count) else 0
    overall_avg = sum(scores) / len(scores)

    grade = calculate_grade(scores, skill_list, benchmark_dict)

    rec_row = recommendations[recommendations['grade'] == grade]
    if not rec_row.empty:
        rec = rec_row.iloc[0]
        recommendation_text = rec['recommendation']
        plan_text = rec['plan']
    else:
        recommendation_text = "Рекомендации отсутствуют"
        plan_text = "План развития не задан"

    user_id = message.from_user.id
    name = employee_dict[user_id]['name']
    direction = employee_dict[user_id]['direction']
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scores_json = json.dumps(answers)

    save_result(user_id, name, direction, date, scores_json,
                avg_hard, avg_soft, grade, recommendation_text, plan_text)

    # Генерируем график
    chart_buf = generate_radar_chart(scores, skill_list, grade, benchmark_dict)

    await message.answer(
        f"✅ Опрос завершён!\n\n"
        f"🏷 Твой грейд: *{grade}*\n"
        f"📊 Средний балл: {overall_avg:.2f}\n"
        f"📌 Рекомендация: {recommendation_text}\n"
        f"📈 План развития: {plan_text}",
        parse_mode='Markdown'
    )
    await message.answer_photo(InputFile(chart_buf), caption="📊 Твой профиль компетенций")

    await state.clear()
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Мой результат")],
            [KeyboardButton(text="🔄 Пройти опрос заново")]
        ],
        resize_keyboard=True
    )
    await message.answer("Ты можешь посмотреть результат или пройти опрос снова.", reply_markup=keyboard)

# ---- Просмотр своего результата ----

@dp.message(lambda m: m.text == "📊 Мой результат")
async def show_my_result(message: types.Message):
    user_id = message.from_user.id
    results = load_results()
    user_results = results[results['telegram_id'] == user_id]
    if user_results.empty:
        await message.answer("Ты ещё не проходил опрос.")
        return
    latest = user_results.sort_values('date', ascending=False).iloc[0]
    scores = json.loads(latest['scores'])
    grade = latest['overall_grade']
    chart_buf = generate_radar_chart(
        [scores[skill] for skill in skill_list],
        skill_list,
        grade,
        benchmark_dict
    )
    await message.answer(
        f"📊 Твой результат (последний опрос от {latest['date']})\n"
        f"🏷 Грейд: {grade}\n"
        f"📈 Hard: {latest['avg_hard']:.2f} | Soft: {latest['avg_soft']:.2f}\n"
        f"📌 Рекомендация: {latest['recommendation']}\n"
        f"📋 План: {latest['plan']}"
    )
    await message.answer_photo(InputFile(chart_buf), caption="Твой профиль")

# ---- Лиды и админы: просмотр дизайнера ----

@dp.callback_query(lambda c: c.data.startswith('view_'))
async def view_employee_result(callback: types.CallbackQuery):
    target_id = int(callback.data.split('_')[1])
    user_id = callback.from_user.id
    role = get_user_role(user_id)

    if role == 'lead':
        direction = lead_admin_dict[user_id]['direction']
        emp = employees[employees['telegram_id'] == target_id]
        if emp.empty or emp.iloc[0]['direction'] != direction:
            await callback.answer("Нет доступа к этому сотруднику.", show_alert=True)
            return
    elif role != 'admin':
        await callback.answer("У вас недостаточно прав.", show_alert=True)
        return

    results = load_results()
    user_results = results[results['telegram_id'] == target_id]
    if user_results.empty:
        await callback.message.answer("Сотрудник ещё не проходил опрос.")
        await callback.answer()
        return

    latest = user_results.sort_values('date', ascending=False).iloc[0]
    scores = json.loads(latest['scores'])
    grade = latest['overall_grade']
    chart_buf = generate_radar_chart(
        [scores[skill] for skill in skill_list],
        skill_list,
        grade,
        benchmark_dict
    )

    await callback.message.answer(
        f"👤 {latest['name']} ({latest['direction']})\n"
        f"📅 {latest['date']}\n"
        f"🏷 Грейд: {grade}\n"
        f"📈 Hard: {latest['avg_hard']:.2f} | Soft: {latest['avg_soft']:.2f}\n"
        f"📌 Рекомендация: {latest['recommendation']}\n"
        f"📋 План: {latest['plan']}"
    )
    await callback.message.answer_photo(InputFile(chart_buf), caption="Профиль компетенций")
    await callback.answer()

# ---- Админ: общая статистика ----

@dp.message(lambda m: m.text == "📊 Общая статистика")
async def admin_stats(message: types.Message):
    if get_user_role(message.from_user.id) != 'admin':
        await message.answer("Нет прав.")
        return
    results = load_results()
    if results.empty:
        await message.answer("Нет данных для статистики.")
        return

    buf = generate_team_stats(results, employees)
    if buf:
        await message.answer_photo(InputFile(buf), caption="📊 Распределение грейдов в команде")

    grade_counts = results['overall_grade'].value_counts()
    text = "📊 Распределение по грейдам:\n" + "\n".join([f"{g}: {c}" for g, c in grade_counts.items()])
    await message.answer(text)

# ---- Админ: список всех дизайнеров ----

@dp.message(lambda m: m.text == "👥 Все дизайнеры")
async def admin_list_employees(message: types.Message):
    if get_user_role(message.from_user.id) != 'admin':
        await message.answer("Нет прав.")
        return
    buttons = []
    for _, row in employees.iterrows():
        buttons.append([InlineKeyboardButton(text=row['name'], callback_data=f"view_{row['telegram_id']}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выбери дизайнера для просмотра:", reply_markup=keyboard)

# ---- Запуск ----

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
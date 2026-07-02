from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging
from config import BOT_TOKEN
from handlers import setup_data, cmd_start, start_survey, process_score
from handlers import SurveyStates

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Загрузка данных
setup_data()

# Регистрация обработчиков
dp.register_message_handler(cmd_start, commands=['start'])
dp.register_callback_query_handler(start_survey, lambda c: c.data == 'start_survey')
dp.register_callback_query_handler(process_score, lambda c: c.data.startswith('score_'), state=SurveyStates.ASKING_SKILL)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
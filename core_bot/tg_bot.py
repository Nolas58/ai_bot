import logging
import os
import nest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime
from agents.core.combined_script import process_yaml_and_answer, process_yaml_files_and_call_llm
from agents.response_agent import MemoryPathfinderAgent
from prompts.Instructions import memory_pathfinder_prompt
from config import OPEN_API_KEY, MODEL_NAME, TG_TOKEN

# Применение патча для совместимости asyncio
nest_asyncio.apply()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# Хранение данных пользователей
user_data = {}


async def send_split_messages(chat_id: int, full_message: str):
    try:
        # Проверяем наличие "Вопрос:" и разделяем сообщение
        if 'Вопрос:' in full_message:
            parts = full_message.split('Вопрос:', 1)
            parts = [part.strip() for part in parts]

            if parts[0]:
                await bot.send_message(chat_id=chat_id, text=parts[0], parse_mode="Markdown")

            if len(parts) > 1 and parts[1]:
                await bot.send_message(chat_id=chat_id, text=parts[1], parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=chat_id, text=full_message, parse_mode="Markdown")
    except Exception as e:
        logging.error(f'Ошибка при отправке сообщения: {e}')


@dp.message(Command(commands=['start']))
async def start(message: Message):
    # Имитация отправки сообщения "Здравствуйте" от пользователя
    fake_message = Message(
        message_id=message.message_id,
        from_user=message.from_user,
        chat=message.chat,
        date=message.date,
        text="Здравствуйте"
    )
    await chat(fake_message)  # Передаём это сообщение в функцию обработки сообщений


@dp.message()
async def chat(message: Message):
    user_id = message.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {
            'dates': [],
            'memory': []
        }

    message_data = message.text
    logging.info(f"Сообщение от пользователя: {message_data}")
    print(f"Сообщение от пользователя: {message_data}")
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_data[user_id]['dates'].append(current_date)

    memory = user_data[user_id]['memory']
    memory.append(f"user: {message_data}, Отправлено: {current_date}")
    # Получаем путь к директории bot_yaml (на два уровня выше текущего файла)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    yaml_folder = os.path.join(project_root, 'file_salon/file_list')  # Укажите путь к папке с YAML файлами
    try:
        interpreted_agent = MemoryPathfinderAgent(model_name=MODEL_NAME, api_key=OPEN_API_KEY)
        respons_interpreted = interpreted_agent.process_memory_and_answer(message_data, memory_pathfinder_prompt, memory)
        logging.info("Начат поиск подходящего файла...")
        print("Начат поиск подходящего файла...")
        file_name = process_yaml_files_and_call_llm(yaml_folder, respons_interpreted)
        if not file_name:
            raise FileNotFoundError(f"Файл для запроса '{message_data}' не найден")

        response = process_yaml_and_answer(yaml_folder, file_name, message_data, memory, user_id)
        await send_split_messages(user_id, response)

        memory.append(f"assistant: {response}")
    except FileNotFoundError as e:
        error_message = f"Ошибка: {str(e)}"
        logging.error(error_message)
        await send_split_messages(user_id, error_message)
    except Exception as e:
        logging.error(f'Ошибка при обработке сообщения: {e}')

    # Ограничиваем размер памяти
    if len(memory) > 20:
        memory.pop(8)  # Удаляем сообщение из середины


async def remove_webhook():
    # Удаляем существующий вебхук, если он есть
    await bot.delete_webhook(drop_pending_updates=True)

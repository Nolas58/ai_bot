# TODO: сдесь у нас все классы агентов. Агенты находятся тут
import os
import yaml
import re
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import logging

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ResponseAgent:
    def __init__(self, model_name, api_key, temperature=0):
        self.llm = ChatOpenAI(temperature=float(temperature), model=model_name, openai_api_key=api_key)


class PathfinderAgent(ResponseAgent):
    def __init__(self, model_name, api_key, prompts, temperature=0):
        super().__init__(model_name, api_key, temperature)
        self.prompts = prompts

    def route_message(self, message, memory):
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.prompts)] + memory + [("human", message)]
        )
        chain = prompt | self.llm

        try:
            response = chain.invoke({"message": message})
            response_text = response.content.strip().lower()

            return response_text
        except Exception as e:
            logger.error(f"Ошибка при маршрутизации сообщения: {e}")
            return "Ошибка при маршрутизации."


class SpecificInfoAgent(ResponseAgent):
    def __init__(self, model_name, api_key, temperature=0.5):
        super().__init__(model_name, api_key, temperature)

    def process_yaml_and_answer(self, yaml_folder, file_name, original_question, system_prompt, memory):
        file_path = os.path.join(yaml_folder, file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            yaml_content = yaml.safe_load(file)

        formatted_content = "\n".join([
            f"{key}:\n{value}" if isinstance(value, str) else f"{key}:\n{yaml.dump(value, default_flow_style=False, allow_unicode=True)}"
            for key, value in yaml_content.items()
        ])

        user_prompt = """
        Вопрос пользователя: {original_question}

        Содержимое YAML файла для ответа на вопрос:
        ###
        {formatted_content}
        ###

        Пожалуйста, сформулируйте ответ на основе предоставленной информации из YAML файла:
        """

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt)] + memory + [("human", user_prompt)]
        )

        chain = prompt | self.llm
        response = chain.invoke({
            "original_question": original_question,
            "formatted_content": formatted_content
        })

        return response.content if hasattr(response, 'content') else response


class SPINAgent(ResponseAgent):
    def __init__(self, model_name, api_key, temperature=0.5):
        super().__init__(model_name, api_key, temperature)

    def process_yaml_and_answer(self, yaml_folder, file_name, original_question, system_prompt, memory):
        file_path = os.path.join(yaml_folder, file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            yaml_content = yaml.safe_load(file)

        formatted_content = "\n".join([
            f"{key}:\n{value}" if isinstance(value, str) else f"{key}:\n{yaml.dump(value, default_flow_style=False, allow_unicode=True)}"
            for key, value in yaml_content.items()
        ])

        user_prompt = """
        Вопрос пользователя: {original_question}

        Содержимое YAML файла для ответа на вопрос:
        ###
        {formatted_content}
        ###

        Пожалуйста, предоставьте ответ, используя методологию SPIN:
        """

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt)] + memory + [("human", user_prompt)]
        )

        chain = prompt | self.llm
        response = chain.invoke({
            "original_question": original_question,
            "formatted_content": formatted_content
        })

        return response.content if hasattr(response, 'content') else response


class FinalResponseAgent(ResponseAgent):
    def __init__(self, model_name, api_key, temperature=0.5):
        super().__init__(model_name, api_key, temperature)

    def generate_final_response(self, system_prompt, agent_response, user_question, memory):

        user_prompt = """
        Вопрос пользователя: {user_question}

        Ответ агента:
        ###
        {agent_response}
        ###

        Пожалуйста, улучшите ответ агента, убрав лишнюю информацию.
        """

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt)] + memory + [("human", user_prompt)]
        )

        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "user_question": user_question,
                "agent_response": agent_response
            })
            # Логируем полученный ответ от модели
            logger.info(f"Ответ от Финальной модели: {response.content if hasattr(response, 'content') else response}\n")
        except Exception as e:
            # Логируем возможную ошибку
            logger.error(f"Ошибка при вызове модели: {e}")
            response = f"Ошибка при генерации финального ответа: {e}"

        return response.content if hasattr(response, 'content') else response


class MemoryPathfinderAgent(ResponseAgent):
    def __init__(self, model_name, api_key, temperature=0):
        super().__init__(model_name, api_key, temperature)

    def process_memory_and_answer(self, user_message, system_prompt, memory):
        # Формируем запрос пользователя
        user_prompt = """
        Сообщение пользователя: {user_message}

        История чата:
        ### {memory}
        Пожалуйста, предоставьте ответ, основываясь на вышеуказанном контексте:
        """

        # Создаем шаблон для промпта, объединяя системный промпт, память и запрос пользователя
        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt)] + memory + [("human", user_prompt)]
        )

        # Выполнение цепочки и получение ответа
        chain = prompt | self.llm
        response = chain.invoke({
            "user_message": user_message,
            "memory": memory  # Если модель требует конкретной обработки памяти
        })

        logger.info(f"Расшифровка запроса: {response.content if hasattr(response, 'content') else response}")

        # Возвращаем ответ от модели
        return response.content if hasattr(response, 'content') else response


class ChatInfoExtractorAgent(ResponseAgent):
    def __init__(self, model_name, api_key, temperature=0.5):
        super().__init__(model_name, api_key, temperature)

    def initialize_user_json(self, user_id, save_info):
        if not os.path.exists(save_info):
            os.makedirs(save_info)

        json_file_path = os.path.join(save_info, f"user_{user_id}.json")

        if not os.path.exists(json_file_path):
            initial_data = {
                "Имя": "",
                "Опыт": "",
                "Цель покупки": "",
                "Рост": "",
                "Вес": "",
                "Бюджет": "",
                "Стиль катания": ""
            }
            with open(json_file_path, 'w', encoding='utf-8') as file:
                json.dump(initial_data, file, ensure_ascii=False, indent=4)
            logger.info(f"Создан новый JSON файл для пользователя {user_id} по пути {json_file_path}")
        else:
            logger.info(f"JSON файл для пользователя {user_id} уже существует по пути {json_file_path}")

    def update_user_json(self, user_id, response_content, save_info):
        json_file_path = os.path.join(save_info, f"user_{user_id}.json")

        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as file:
                user_data = json.load(file)
        else:
            user_data = {}

        # Предполагается, что response_content - это строка, подобная "Имя: Не указано\nОпыт: Не указано\n..."
        # Преобразуем ее в словарь
        response_data = {}
        for line in response_content.splitlines():
            key, _, value = line.partition(":")
            response_data[key.strip()] = value.strip()

        # Обновляем данные пользователя с новым контентом ответа
        user_data.update(response_data)

        with open(json_file_path, 'w', encoding='utf-8') as file:
            json.dump(user_data, file, ensure_ascii=False, indent=4)

    def process_memory_and_extract_info(self, user_message, system_prompt, memory, user_id, save_info):
        self.initialize_user_json(user_id, save_info)

        user_prompt = """
        Сообщение пользователя: {user_message}

        История чата:
        ### {memory}
        """

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt)] + [("human", user_prompt)]
        )

        chain = prompt | self.llm
        response = chain.invoke({
            "user_message": user_message,
            "memory": memory
        })

        # Получаем текст ответа
        response_content = response.content if hasattr(response, 'content') else response

        # Обновляем JSON файл для пользователя
        self.update_user_json(user_id, response_content, save_info)

        # Логируем JSON
        logger.info(f"Извлеченная информация в формате JSON: {json.dumps(response_content, ensure_ascii=False, indent=4)}\n")

        return response_content

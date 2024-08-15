# TODO: этот файл запускайт основных агентов
import logging
import os
from agents.file_selection import LLMAgent
from agents.response_agent import PathfinderAgent, SpecificInfoAgent, SPINAgent, FinalResponseAgent, ChatInfoExtractorAgent
from prompts.Instructions import *
from config import OPEN_AI_KEY, MODEL_NAME


# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Определение моделей и API ключа
model_name = MODEL_NAME
api_key = OPEN_AI_KEY

# Получаем путь к директории bot_yaml (на два уровня выше текущего файла)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Определяем путь к новой папке user_info в корне проекта
save_info = os.path.join(project_root, 'user_info')


def process_yaml_files_and_call_llm(yaml_folder, question):
    prompt_template = """
    #ЗАДАЧА#
    Выбрать наиболее подходящий файл, который, вероятно, содержит ответ на вопрос пользователя, основываясь на описаниях файлов.

    #ВХОДНЫЕ_ДАННЫЕ#
    1. Описания файлов с описанием содержимого:
    </file_info>
    {file_info}
    <file_info>

    2. Вопрос пользователя:
    </user_question>
    {question}
    <user_question>

    #ИНСТРУКЦИИ#
    1. Внимательно прочитайте вопрос пользователя.
    2. Проанализируйте описания всех предоставленных файлов.
    3. Определите ключевые слова и концепции в вопросе пользователя.
    4. Сопоставьте эти ключевые слова и концепции с описаниями файлов.
    5. Выберите файл, чье описание наиболее точно соответствует вопросу пользователя.

    #ДЕЙСТВИЕ#
    Теперь, пожалуйста, проанализируйте предоставленную информацию и дайте ответ в указанном формате.
    """

    agent = LLMAgent(model_name=model_name, api_key=api_key)
    logger.info(f"Вызов агента для выбора файла с вопросом: {question}")
    selected_file = agent.process_yaml_files_and_call_llm(yaml_folder, question, prompt_template)
    logger.info(f"Файл выбран: {selected_file}")
    return selected_file


def process_yaml_and_answer(yaml_folder, file_name, original_question, memory, user_id):
    pathfinder_agent = PathfinderAgent(model_name, api_key, pathfinder_prompts)

    logger.info(f"Агент Pathfinder получил запрос: {original_question}")
    logger.info("Агент Pathfinder начал обработку запроса")

    route_decision = pathfinder_agent.route_message(original_question, memory)

    if "конкретика" in route_decision.lower():
        logger.info("Агент Pathfinder решил, что запрос должен быть передан агенту Конкретика")
        specific_info_agent = SpecificInfoAgent(model_name, api_key)
        agent_response = specific_info_agent.process_yaml_and_answer(yaml_folder, file_name, original_question, specific_info_prompts, memory)
    else:
        logger.info("Агент Pathfinder решил, что запрос должен быть передан агенту Продажник")
        spin_agent = SPINAgent(model_name, api_key)
        agent_response = spin_agent.process_yaml_and_answer(yaml_folder, file_name, original_question, spin_prompts, memory)

    final_response_agent = FinalResponseAgent(model_name, api_key)
    final_response = final_response_agent.generate_final_response(final_response_prompt, agent_response, original_question, memory)

    # Вызов ChatInfoExtractorAgent после получения финального ответа
    chat_info_agent = ChatInfoExtractorAgent(model_name, api_key)
    extracted_info_json = chat_info_agent.process_memory_and_extract_info(
        user_message=original_question,
        system_prompt=prompt_json,
        memory=memory,
        user_id=user_id,
        save_info=save_info
    )

    return final_response

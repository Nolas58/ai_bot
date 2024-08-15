# TODO: Функции для обработки YAML Файлов
import os
import yaml
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field


class LLMAgent:
    def __init__(self, model_name, api_key, temperature=0):
        self.llm = ChatOpenAI(temperature=temperature, model=model_name, api_key=api_key)

    def read_yaml_descriptions(self, yaml_folder):
        """Читает YAML файлы и возвращает описания."""
        descriptions = {}
        for filename in os.listdir(yaml_folder):
            if filename.endswith('.yaml'):
                file_path = os.path.join(yaml_folder, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        data = yaml.safe_load(file)
                        descriptions[filename] = data.get('description', 'Описание отсутствует')
                except (FileNotFoundError, yaml.YAMLError):
                    descriptions[filename] = "Ошибка при чтении файла"
        return descriptions

    def create_file_selection_class(self, file_list):
        """Создание класса выбора файла на базе предоставленного списка файлов."""

        class FileSelection(BaseModel):
            """Выбор файла."""
            selected_file: str = Field(
                ...,
                description="Выбор имени файла, который наиболее соответствует вопросу пользователя на основе предоставленных описаний файлов.",
                enum=file_list
            )

        return FileSelection

    def prepare_file_info_str(self, file_info):
        """Подготавливает информацию о файлах в виде строки для промпта."""
        return "\n".join([f"{filename}: {description}" for filename, description in file_info.items()])

    def process_yaml_files_and_call_llm(self, yaml_folder, question, prompt_template):
        """Обработка YAML файлов и вызов языковой модели для выбора файла."""
        # Чтение и подготовка описаний файлов
        file_info = self.read_yaml_descriptions(yaml_folder)

        # Создание класса для выбора файла
        FileSelection = self.create_file_selection_class(list(file_info.keys()))

        # Подготовка строки с информацией для промпта
        file_info_str = self.prepare_file_info_str(file_info)

        # Определение промпта
        prompt = ChatPromptTemplate.from_template(prompt_template)

        # Вызов модели для выбора файла
        chain = prompt | self.llm.with_structured_output(FileSelection)
        result = chain.invoke({"file_info": file_info_str, "question": question})

        return result.selected_file

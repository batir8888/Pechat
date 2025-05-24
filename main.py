import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyautogui
import random
import time
import threading
import re
import unicodedata


class TypingSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Симулятор человеческой печати")
        self.root.geometry("900x700")

        # Флаг для остановки печати
        self.stop_typing = False
        self.typing_thread = None

        # Настройки скорости
        self.min_delay = 0.05  # Минимальная задержка между символами
        self.max_delay = 0.15  # Максимальная задержка между символами
        self.word_pause_chance = 0.1  # Шанс паузы после слова
        self.word_pause_duration = (0.2, 0.5)  # Диапазон паузы после слова

        # Словарь для замены проблемных символов из PDF
        self.pdf_replacements = {
            '"': '"',  # Левая кавычка
            '"': '"',  # Правая кавычка
            ''': "'",  # Левый апостроф
            ''': "'",  # Правый апостроф
            '–': '-',  # En dash
            '—': '-',  # Em dash
            '…': '...',  # Многоточие
            '−': '-',  # Minus sign
            '×': '*',  # Multiplication sign
            '÷': '/',  # Division sign
            '≤': '<=',  # Less than or equal
            '≥': '>=',  # Greater than or equal
            '≠': '!=',  # Not equal
            '→': '->',  # Arrow
            '←': '<-',  # Left arrow
            '⇒': '=>',  # Double arrow
            '\xa0': ' ',  # Non-breaking space
            '\u200b': '',  # Zero-width space
            '\u200c': '',  # Zero-width non-joiner
            '\u200d': '',  # Zero-width joiner
            '\ufeff': '',  # Zero-width no-break space
        }

        self.setup_ui()

    def setup_ui(self):
        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Настройка весов для адаптивного размера
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Заголовок
        title_label = ttk.Label(main_frame, text="Вставьте текст для печати:",
                                font=('Arial', 12, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # Текстовое поле с прокруткой
        self.text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD,
                                                   width=80, height=20,
                                                   font=('Consolas', 10))
        self.text_area.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Фрейм для настроек
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки", padding="10")
        settings_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)

        # Режим работы
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(mode_frame, text="Режим:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.mode_var = tk.StringVar(value="normal")
        ttk.Radiobutton(mode_frame, text="Обычный", variable=self.mode_var,
                        value="normal").grid(row=0, column=1, padx=5)
        ttk.Radiobutton(mode_frame, text="C++ код (автоформатирование)",
                        variable=self.mode_var, value="cpp").grid(row=0, column=2, padx=5)

        # Опции форматирования
        format_frame = ttk.LabelFrame(settings_frame, text="Опции форматирования",
                                      padding="5")
        format_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        self.convert_spaces = tk.BooleanVar(value=True)
        ttk.Checkbutton(format_frame, text="Конвертировать 4 пробела в табуляцию",
                        variable=self.convert_spaces).grid(row=0, column=0, sticky=tk.W)

        self.fix_pdf_chars = tk.BooleanVar(value=True)
        ttk.Checkbutton(format_frame, text="Исправить символы из PDF",
                        variable=self.fix_pdf_chars).grid(row=1, column=0, sticky=tk.W)

        self.normalize_whitespace = tk.BooleanVar(value=True)
        ttk.Checkbutton(format_frame, text="Нормализовать пробелы и отступы",
                        variable=self.normalize_whitespace).grid(row=2, column=0, sticky=tk.W)

        self.fix_line_breaks = tk.BooleanVar(value=True)
        ttk.Checkbutton(format_frame, text="Исправить переносы строк",
                        variable=self.fix_line_breaks).grid(row=3, column=0, sticky=tk.W)

        # Настройки скорости
        speed_frame = ttk.Frame(settings_frame)
        speed_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(speed_frame, text="Скорость печати:").grid(row=0, column=0, sticky=tk.W)

        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.5, to=2.0,
                                variable=self.speed_var, orient=tk.HORIZONTAL,
                                length=200)
        speed_scale.grid(row=0, column=1, padx=10)

        self.speed_label = ttk.Label(speed_frame, text="1.0x")
        self.speed_label.grid(row=0, column=2)

        # Обновление метки скорости
        speed_scale.configure(command=self.update_speed_label)

        # Задержка перед началом
        delay_frame = ttk.Frame(settings_frame)
        delay_frame.grid(row=3, column=0, sticky=tk.W, pady=5)

        ttk.Label(delay_frame, text="Задержка перед началом (сек):").grid(row=0, column=0)
        self.start_delay = tk.IntVar(value=3)
        ttk.Spinbox(delay_frame, from_=1, to=10, textvariable=self.start_delay,
                    width=10).grid(row=0, column=1, padx=10)

        # Фрейм для кнопок
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=10)

        # Кнопки
        self.start_button = ttk.Button(button_frame, text="Начать печать",
                                       command=self.start_typing, style='Accent.TButton')
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Остановить",
                                      command=self.stop_typing_process,
                                      state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)

        ttk.Button(button_frame, text="Форматировать",
                   command=self.format_text).grid(row=0, column=2, padx=5)

        ttk.Button(button_frame, text="Очистить",
                   command=self.clear_text).grid(row=0, column=3, padx=5)

        # Статус бар
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E))

    def update_speed_label(self, value):
        self.speed_label.config(text=f"{float(value):.1f}x")

    def replace_pdf_characters(self, text):
        """Заменяет проблемные символы из PDF на стандартные"""
        if not self.fix_pdf_chars.get():
            return text

        for old_char, new_char in self.pdf_replacements.items():
            text = text.replace(old_char, new_char)

        # Нормализация Unicode
        text = unicodedata.normalize('NFKC', text)

        return text

    def normalize_cpp_whitespace(self, text):
        """Нормализует пробелы и отступы для C++ кода"""
        if not self.normalize_whitespace.get():
            return text

        lines = text.split('\n')
        normalized_lines = []

        for line in lines:
            # Удаляем trailing whitespace
            line = line.rstrip()

            # Заменяем множественные пробелы на одинарные (кроме начала строки)
            if line:
                # Сохраняем отступ в начале
                indent_match = re.match(r'^(\s*)', line)
                if indent_match:
                    indent = indent_match.group(1)
                    rest_of_line = line[len(indent):]
                    # В остальной части строки заменяем множественные пробелы
                    rest_of_line = re.sub(r' +', ' ', rest_of_line)
                    line = indent + rest_of_line

            normalized_lines.append(line)

        return '\n'.join(normalized_lines)

    def fix_cpp_line_breaks(self, text):
        """Исправляет проблемы с переносами строк в C++ коде"""
        if not self.fix_line_breaks.get():
            return text

        # Удаляем переносы внутри строковых литералов (часто бывает в PDF)
        # Это упрощенная версия, для более сложных случаев нужен полный парсер
        lines = text.split('\n')
        fixed_lines = []
        in_string = False
        accumulated_line = ""

        for line in lines:
            # Проверяем, находимся ли мы внутри строки
            quote_count = line.count('"') - line.count('\\"')

            if in_string:
                # Если мы внутри строки, добавляем к накопленной строке
                accumulated_line += " " + line.strip()
                if quote_count % 2 == 1:  # Нечетное количество кавычек - строка закрывается
                    in_string = False
                    fixed_lines.append(accumulated_line)
                    accumulated_line = ""
            else:
                if quote_count % 2 == 1:  # Нечетное количество кавычек - строка открывается
                    in_string = True
                    accumulated_line = line
                else:
                    fixed_lines.append(line)

        # Добавляем последнюю накопленную строку, если есть
        if accumulated_line:
            fixed_lines.append(accumulated_line)

        return '\n'.join(fixed_lines)

    def format_cpp_code(self, text):
        """Форматирует C++ код, исправляя типичные проблемы из PDF"""
        # 1. Заменяем проблемные символы
        text = self.replace_pdf_characters(text)

        # 2. Нормализуем пробелы
        text = self.normalize_cpp_whitespace(text)

        # 3. Исправляем переносы строк
        text = self.fix_cpp_line_breaks(text)

        # 4. Конвертируем пробелы в табы
        if self.convert_spaces.get():
            text = re.sub(r'    ', '\t', text)

        # 5. Дополнительные исправления для C++
        # Добавляем пробелы вокруг операторов, если их нет
        text = re.sub(r'(\w)(<|>|<=|>=|==|!=|&&|\|\|)(\w)', r'\1 \2 \3', text)
        text = re.sub(r'(\w)(=)(\w)', r'\1 \2 \3', text)

        # Исправляем слипшиеся include директивы
        text = re.sub(r'#include<', '#include <', text)
        text = re.sub(r'#include"', '#include "', text)

        # Добавляем пробел после запятых, если его нет
        text = re.sub(r',(?!\s)', ', ', text)

        # Исправляем проблемы с точкой с запятой
        text = re.sub(r';\s*\n\s*{', '\n{', text)  # Убираем ; перед {

        return text

    def format_text(self):
        """Форматирует текст в зависимости от выбранного режима"""
        text = self.text_area.get(1.0, tk.END).rstrip()

        if not text:
            self.status_var.set("Нет текста для форматирования")
            return

        if self.mode_var.get() == "cpp":
            formatted_text = self.format_cpp_code(text)
        else:
            # В обычном режиме только конвертация пробелов
            formatted_text = text
            if self.convert_spaces.get():
                formatted_text = re.sub(r'    ', '\t', formatted_text)

        # Обновляем текст в поле
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(1.0, formatted_text)
        self.status_var.set("Текст отформатирован")

    def simulate_human_typing(self, text):
        """Имитирует человеческую печать с вариациями скорости"""
        for char in text:
            if self.stop_typing:
                break

            # Печатаем символ
            pyautogui.write(char)

            # Рассчитываем задержку с учетом множителя скорости
            speed_multiplier = self.speed_var.get()
            base_delay = random.uniform(self.min_delay, self.max_delay)
            delay = base_delay / speed_multiplier

            # Добавляем случайные паузы после слов
            if char == ' ' and random.random() < self.word_pause_chance:
                pause_min, pause_max = self.word_pause_duration
                delay += random.uniform(pause_min, pause_max) / speed_multiplier

            # Небольшая дополнительная задержка после знаков препинания
            if char in '.!?,:;':
                delay += random.uniform(0.1, 0.3) / speed_multiplier

            time.sleep(delay)

    def typing_worker(self):
        """Рабочая функция для потока печати"""
        try:
            # Получаем текст
            text = self.text_area.get(1.0, tk.END).rstrip()

            if not text:
                self.status_var.set("Ошибка: текст не введён")
                return

            # Форматируем текст если нужно
            if self.mode_var.get() == "cpp":
                text = self.format_cpp_code(text)
            elif self.convert_spaces.get():
                text = re.sub(r'    ', '\t', text)

            # Обновляем статус
            self.status_var.set(f"Ожидание {self.start_delay.get()} сек...")

            # Задержка перед началом
            for i in range(self.start_delay.get(), 0, -1):
                if self.stop_typing:
                    return
                self.status_var.set(f"Начало через {i} сек... (Переключитесь на нужное окно)")
                time.sleep(1)

            # Начинаем печать
            self.status_var.set("Печатаем...")
            self.simulate_human_typing(text)

            if not self.stop_typing:
                self.status_var.set("Печать завершена")
            else:
                self.status_var.set("Печать остановлена")

        except Exception as e:
            self.status_var.set(f"Ошибка: {str(e)}")
            messagebox.showerror("Ошибка", f"Произошла ошибка:\n{str(e)}")

        finally:
            # Восстанавливаем состояние кнопок
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.stop_typing = False

    def start_typing(self):
        """Запускает процесс печати в отдельном потоке"""
        if self.typing_thread and self.typing_thread.is_alive():
            messagebox.showwarning("Предупреждение", "Печать уже выполняется!")
            return

        # Меняем состояние кнопок
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Сбрасываем флаг остановки
        self.stop_typing = False

        # Запускаем поток
        self.typing_thread = threading.Thread(target=self.typing_worker, daemon=True)
        self.typing_thread.start()

    def stop_typing_process(self):
        """Останавливает процесс печати"""
        self.stop_typing = True
        self.status_var.set("Остановка...")

    def clear_text(self):
        """Очищает текстовое поле"""
        self.text_area.delete(1.0, tk.END)
        self.status_var.set("Текст очищен")


def main():
    # Настройки PyAutoGUI для безопасности
    pyautogui.FAILSAFE = True  # Перемещение мыши в угол экрана остановит программу
    pyautogui.PAUSE = 0.01  # Минимальная пауза между командами

    root = tk.Tk()
    app = TypingSimulator(root)

    # Стиль для кнопки
    style = ttk.Style()
    style.configure('Accent.TButton', foreground='white', background='#0078d4')

    root.mainloop()


if __name__ == "__main__":
    main()
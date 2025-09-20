import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, scrolledtext, ttk
import os
import webbrowser
import json
import subprocess
import platform
import shutil
from datetime import datetime
import threading
import http.server
import socketserver

# Конфигурация цветов для черной темы
BG_COLOR = "#1E1E1E"
FG_COLOR = "#D4D4D4"
BUTTON_BG = "#007ACC"
BUTTON_FG = "#FFFFFF"
LISTBOX_BG = "#2D2D2D"
LISTBOX_FG = "#D4D4D4"
ENTRY_BG = "#3C3C3C"
ENTRY_FG = "#D4D4D4"
ACCENT_COLOR = "#569CD6"

class WebsiteManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Менеджер веб-проектов")
        self.root.geometry("1000x750")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(800, 600)
        
        self.websites = {}
        self.data_file = "websites.json"
        self.config_file = "config.json"
        self.custom_editor_path = None
        self.server_process = None
        self.current_server = None
        
        self.load_websites()
        self.load_config()

        self.create_styles()
        self.create_widgets()
        self.filter_list_by_search()

        # Создание контекстного меню
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Открыть папку", command=self.open_folder)
        self.context_menu.add_command(label="Открыть в браузере", command=self.open_in_browser)
        self.context_menu.add_command(label="Открыть в редакторе", command=self.open_in_editor)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Добавить/изменить описание", command=self.edit_website_info)
        self.context_menu.add_command(label="Удалить сайт", command=self.delete_website)
        
        self.website_listbox.bind("<Button-3>", self.show_context_menu)
        
    def create_styles(self):
        """Создает и настраивает стили для ttk виджетов."""
        style = ttk.Style()
        style.theme_use('default')

        # Стиль для кнопок
        style.configure("TButton",
                        background=BUTTON_BG,
                        foreground=BUTTON_FG,
                        font=("Segoe UI", 10),
                        padding=8,
                        relief="flat")
        style.map("TButton",
                  background=[('active', ACCENT_COLOR)])

        # Стиль для рамок
        style.configure("TFrame", background=BG_COLOR)

        # Стиль для полей ввода
        style.configure("TEntry",
                        fieldbackground=ENTRY_BG,
                        foreground=ENTRY_FG,
                        relief="flat")

        # Стиль для меток
        style.configure("TLabel",
                        background=BG_COLOR,
                        foreground=FG_COLOR,
                        font=("Segoe UI", 10))

    def create_widgets(self):
        """Создает все элементы графического интерфейса."""
        # --- Главный фрейм для разделения на левую и правую части ---
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=1, padx=20, pady=20)

        # --- Левая панель: управление и список проектов ---
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=0, padx=(0, 20))

        # Фрейм для кнопок управления
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        btn_add = ttk.Button(button_frame, text="Добавить сайт", command=self.add_website)
        btn_add.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=1)

        btn_editor = ttk.Button(button_frame, text="Выбрать редактор", command=self.select_custom_editor)
        btn_editor.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=1)

        # Поле поиска
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        search_label = ttk.Label(search_frame, text="Поиск:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=1)
        self.search_entry.bind("<KeyRelease>", lambda event: self.filter_list_by_search())

        # Фрейм для меток и поля фильтрации по тегам
        filter_frame = ttk.Frame(left_panel)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.tags = self.get_all_tags()
        self.filter_var = tk.StringVar()
        self.filter_var.set("Все теги")
        
        self.filter_menu = tk.OptionMenu(filter_frame, self.filter_var, *self.tags, command=self.filter_list_by_tag)
        self.filter_menu.config(bg=BUTTON_BG, fg=BUTTON_FG, activebackground=ACCENT_COLOR, activeforeground=BUTTON_FG)
        self.filter_menu["menu"].config(bg=BUTTON_BG, fg=BUTTON_FG)
        self.filter_menu.pack(fill=tk.X, expand=1)

        # Список сайтов
        self.website_listbox = tk.Listbox(left_panel, selectmode=tk.SINGLE,
                                          bg=LISTBOX_BG, fg=LISTBOX_FG,
                                          selectbackground=ACCENT_COLOR,
                                          font=("Segoe UI", 11),
                                          bd=0, highlightthickness=0,
                                          height=20)
        self.website_listbox.pack(fill=tk.BOTH, expand=1)
        self.website_listbox.bind("<<ListboxSelect>>", self.on_listbox_select)

        # --- Правая панель: информация о сайте и кнопки действий ---
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)

        self.info_frame = ttk.Frame(right_panel)
        self.info_frame.pack(fill=tk.BOTH, expand=1)
        
        self.title_label = ttk.Label(self.info_frame, text="Выберите сайт из списка",
                                     font=("Segoe UI", 16, "bold"), foreground=ACCENT_COLOR)
        self.title_label.pack(pady=(0, 10))
        
        # Фрейм для информации и структуры
        info_and_tree_frame = ttk.Frame(self.info_frame)
        info_and_tree_frame.pack(fill=tk.BOTH, expand=1, pady=(0, 10))

        # Фрейм для информации о сайте
        info_panel = ttk.Frame(info_and_tree_frame)
        info_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, padx=(0, 10))
        
        info_label = ttk.Label(info_panel, text="Информация о проекте:", font=("Segoe UI", 12))
        info_label.pack(anchor=tk.W, pady=(0, 5))
        self.info_text = scrolledtext.ScrolledText(info_panel, wrap=tk.WORD,
                                                   bg=LISTBOX_BG, fg=LISTBOX_FG,
                                                   font=("Segoe UI", 10),
                                                   bd=0, relief="flat",
                                                   insertbackground=ACCENT_COLOR)
        self.info_text.pack(fill=tk.BOTH, expand=1)
        self.info_text.bind("<KeyPress>", lambda e: "break") # Запрет редактирования

        # Фрейм для структуры папок
        tree_panel = ttk.Frame(info_and_tree_frame)
        tree_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)

        tree_label = ttk.Label(tree_panel, text="Структура папок:", font=("Segoe UI", 12))
        tree_label.pack(anchor=tk.W, pady=(0, 5))
        self.tree_text = scrolledtext.ScrolledText(tree_panel, wrap=tk.WORD,
                                                   bg=LISTBOX_BG, fg=LISTBOX_FG,
                                                   font=("Consolas", 10),
                                                   bd=0, relief="flat",
                                                   insertbackground=ACCENT_COLOR)
        self.tree_text.pack(fill=tk.BOTH, expand=1)
        self.tree_text.bind("<KeyPress>", lambda e: "break") # Запрет редактирования


        # Фрейм для кнопок действий
        action_button_frame = ttk.Frame(right_panel)
        action_button_frame.pack(fill=tk.X, pady=(10, 0))

        btn_open_folder = ttk.Button(action_button_frame, text="Открыть папку", command=self.open_folder)
        btn_open_folder.pack(side=tk.LEFT, fill=tk.X, expand=1, padx=(0, 5))

        btn_open_editor = ttk.Button(action_button_frame, text="Открыть в редакторе", command=self.open_in_editor)
        btn_open_editor.pack(side=tk.LEFT, fill=tk.X, expand=1, padx=5)
        
        btn_open_browser = ttk.Button(action_button_frame, text="Открыть в браузере", command=self.open_in_browser)
        btn_open_browser.pack(side=tk.LEFT, fill=tk.X, expand=1, padx=5)

        btn_start_server = ttk.Button(action_button_frame, text="Запустить сервер", command=self.start_server)
        btn_start_server.pack(side=tk.LEFT, fill=tk.X, expand=1, padx=5)

        btn_stop_server = ttk.Button(action_button_frame, text="Остановить сервер", command=self.stop_server)
        btn_stop_server.pack(side=tk.LEFT, fill=tk.X, expand=1, padx=(5, 0))

        # --- Строка состояния ---
        self.status_bar = tk.Label(self.root, text="Готово", bd=1, relief=tk.SUNKEN, anchor=tk.W,
                                   bg=BG_COLOR, fg=FG_COLOR, font=("Segoe UI", 9))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_context_menu(self, event):
        """Отображает контекстное меню по клику правой кнопкой мыши."""
        try:
            self.website_listbox.selection_clear(0, tk.END)
            self.website_listbox.selection_set(self.website_listbox.nearest(event.y))
            self.on_listbox_select(None)
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def update_listbox(self):
        """Обновляет список сайтов в listbox."""
        self.website_listbox.delete(0, tk.END)
        for name in self.websites:
            self.website_listbox.insert(tk.END, name)

    def on_listbox_select(self, event):
        """Обработчик события выбора элемента в listbox."""
        try:
            selected_index = self.website_listbox.curselection()[0]
            selected_name = self.website_listbox.get(selected_index)
            site_data = self.websites.get(selected_name, {})
            self.display_website_info(site_data)
            self.display_directory_tree(site_data.get("path", ""))
        except IndexError:
            self.display_website_info({})
            self.display_directory_tree("")

    def display_website_info(self, site_data):
        """Отображает информацию о выбранном сайте."""
        self.title_label.config(text=site_data.get("name", "Выберите сайт из списка"))
        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)

        if site_data:
            info = f"Название: {site_data.get('name', 'Не указано')}\n"
            info += f"Путь: {site_data.get('path', 'Не указан')}\n"
            info += f"Основной файл: {site_data.get('main_file', 'Не указан')}\n"
            info += f"Дата добавления: {site_data.get('added_date', 'Неизвестно')}\n"
            info += f"Теги: {', '.join(site_data.get('tags', []))}\n\n"
            info += f"Описание: {site_data.get('description', 'Описание отсутствует.')}"
            self.info_text.insert(tk.END, info)
        else:
            self.info_text.insert(tk.END, "Информация о выбранном сайте появится здесь.")

        self.info_text.configure(state=tk.DISABLED)

    def display_directory_tree(self, path):
        """Отображает структуру папок и файлов проекта."""
        self.tree_text.configure(state=tk.NORMAL)
        self.tree_text.delete("1.0", tk.END)
        
        if not path or not os.path.exists(path):
            self.tree_text.insert(tk.END, "Структура не найдена.")
            self.tree_text.configure(state=tk.DISABLED)
            return

        tree_str = ""
        for root_path, dirs, files in os.walk(path):
            level = root_path.replace(path, '').count(os.sep)
            indent = ' ' * 4 * level
            tree_str += f"{indent}[{os.path.basename(root_path)}/]\n"
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                tree_str += f"{subindent}{f}\n"

        self.tree_text.insert(tk.END, tree_str)
        self.tree_text.configure(state=tk.DISABLED)

    def add_website(self):
        """Добавляет новый сайт в список."""
        folder_path = filedialog.askdirectory(title="Выберите папку с проектом")
        if not folder_path:
            return

        # Запрашиваем название
        name = os.path.basename(folder_path)
        
        # Ручной выбор основного файла
        main_file = filedialog.askopenfilename(
            initialdir=folder_path,
            title="Выберите основной файл (например, index.html)",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        
        if not main_file:
            messagebox.showwarning("Отмена", "Добавление сайта отменено.")
            return

        # Добавление описания
        description = simpledialog.askstring("Описание", f"Введите описание для сайта '{name}':")
        if description is None:
            description = ""

        # Добавление тегов
        tags_str = simpledialog.askstring("Теги", "Введите теги через запятую (например: html, css, js):")
        tags = [tag.strip() for tag in tags_str.split(',')] if tags_str else []

        # Создание объекта с данными о сайте
        website_data = {
            "name": name,
            "path": folder_path,
            "main_file": os.path.relpath(main_file, folder_path),
            "description": description,
            "tags": tags,
            "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.websites[name] = website_data
        self.save_websites()
        self.update_listbox()
        self.filter_menu_update()
        messagebox.showinfo("Успех", f"Сайт '{name}' успешно добавлен.")
        
    def edit_website_info(self):
        """Редактирует информацию о выбранном сайте."""
        try:
            selected_index = self.website_listbox.curselection()[0]
            selected_name = self.website_listbox.get(selected_index)
            current_data = self.websites[selected_name]

            # Редактирование описания
            new_description = simpledialog.askstring(
                "Редактировать описание",
                f"Введите новое описание для '{selected_name}':",
                initialvalue=current_data.get('description', '')
            )
            if new_description is not None:
                current_data['description'] = new_description

            # Редактирование тегов
            current_tags_str = ', '.join(current_data.get('tags', []))
            new_tags_str = simpledialog.askstring(
                "Редактировать теги",
                f"Введите новые теги через запятую для '{selected_name}':",
                initialvalue=current_tags_str
            )
            if new_tags_str is not None:
                current_data['tags'] = [tag.strip() for tag in new_tags_str.split(',')] if new_tags_str else []

            self.save_websites()
            self.display_website_info(current_data)
            self.filter_menu_update()

        except IndexError:
            messagebox.showwarning("Предупреждение", "Выберите сайт из списка для редактирования.")

    def delete_website(self):
        """Удаляет выбранный сайт из списка."""
        try:
            selected_index = self.website_listbox.curselection()[0]
            selected_name = self.website_listbox.get(selected_index)
            if messagebox.askyesno("Удалить сайт", f"Вы уверены, что хотите удалить сайт '{selected_name}'?"):
                del self.websites[selected_name]
                self.save_websites()
                self.update_listbox()
                self.filter_list_by_search()
                self.filter_menu_update()
                self.display_website_info({})
                messagebox.showinfo("Успех", f"Сайт '{selected_name}' успешно удален.")
        except IndexError:
            messagebox.showwarning("Предупреждение", "Выберите сайт из списка.")

    def load_websites(self):
        """Загружает данные о сайтах из файла."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    self.websites = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self.websites = {}
                messagebox.showerror("Ошибка загрузки", "Не удалось загрузить данные о сайтах. Файл поврежден или не найден.")

    def save_websites(self):
        """Сохраняет данные о сайтах в файл."""
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.websites, f, indent=4)
        except IOError:
            messagebox.showerror("Ошибка сохранения", "Не удалось сохранить данные о сайтах.")

    def load_config(self):
        """Загружает конфигурацию из файла."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    self.custom_editor_path = config.get("custom_editor_path")
            except json.JSONDecodeError:
                messagebox.showwarning("Предупреждение", "Не удалось загрузить конфигурацию. Будут использованы настройки по умолчанию.")

    def save_config(self):
        """Сохраняет конфигурацию в файл."""
        config = {"custom_editor_path": self.custom_editor_path}
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=4)
        except IOError:
            messagebox.showerror("Ошибка сохранения", "Не удалось сохранить конфигурацию.")

    def get_all_tags(self):
        """Собирает все уникальные теги из всех сайтов."""
        all_tags = {"Все теги"}
        for site_data in self.websites.values():
            for tag in site_data.get("tags", []):
                all_tags.add(tag)
        return sorted(list(all_tags))

    def filter_menu_update(self):
        """Обновляет содержимое выпадающего меню с тегами."""
        menu = self.filter_menu["menu"]
        menu.delete(0, "end")
        all_tags = self.get_all_tags()
        self.filter_var.set("Все теги")
        for tag in all_tags:
            menu.add_command(label=tag, command=tk._setit(self.filter_var, tag, self.filter_list_by_tag))

    def filter_list_by_search(self, event=None):
        """Фильтрует список сайтов по поисковому запросу."""
        query = self.search_entry.get().lower()
        self.website_listbox.delete(0, tk.END)
        for name, data in self.websites.items():
            if query in name.lower() or query in data.get("description", "").lower():
                self.website_listbox.insert(tk.END, name)

    def filter_list_by_tag(self, tag):
        """Фильтрует список сайтов по тегам."""
        self.website_listbox.delete(0, tk.END)
        if tag == "Все теги":
            for name in self.websites:
                self.website_listbox.insert(tk.END, name)
        else:
            for name, data in self.websites.items():
                if tag in data.get("tags", []):
                    self.website_listbox.insert(tk.END, name)
        
    def open_folder(self):
        """Открывает папку выбранного сайта в проводнике/файндерe."""
        try:
            selected_index = self.website_listbox.curselection()[0]
            selected_name = self.website_listbox.get(selected_index)
            folder_path = self.websites[selected_name]["path"]
            
            if not os.path.exists(folder_path):
                messagebox.showerror("Ошибка", f"Папка '{folder_path}' не найдена.")
                return

            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin": # macOS
                subprocess.run(["open", folder_path])
            else: # Linux
                subprocess.run(["xdg-open", folder_path])
        except IndexError:
            messagebox.showwarning("Предупреждение", "Выберите сайт из списка.")

    def open_in_browser(self):
        """Открывает основной файл сайта в браузере."""
        try:
            selected_index = self.website_listbox.curselection()[0]
            selected_name = self.website_listbox.get(selected_index)
            site_data = self.websites[selected_name]
            
            file_path = os.path.join(site_data["path"], site_data["main_file"])
            
            if not os.path.exists(file_path):
                messagebox.showerror("Ошибка", f"Основной файл '{file_path}' не найден.")
                return

            webbrowser.open(f'file://{os.path.abspath(file_path)}')
        except IndexError:
            messagebox.showwarning("Предупреждение", "Выберите сайт из списка.")

    def open_in_editor(self):
        """Открывает папку выбранного сайта в VS Code или другом настроенном редакторе."""
        try:
            selected_index = self.website_listbox.curselection()[0]
            selected_name = self.website_listbox.get(selected_index)
            folder_path = self.websites[selected_name]["path"]

            if not os.path.exists(folder_path):
                messagebox.showerror("Ошибка", f"Папка '{folder_path}' не найдена.")
                return

            if self.custom_editor_path:
                try:
                    subprocess.run([self.custom_editor_path, folder_path], check=True)
                except FileNotFoundError:
                    messagebox.showerror("Ошибка", f"Исполняемый файл редактора не найден по пути:\\n{self.custom_editor_path}")
            else:
                try:
                    subprocess.run(["code", folder_path], check=True, shell=True)
                except FileNotFoundError:
                    messagebox.showerror("Ошибка", "VS Code не найден. Чтобы использовать другой редактор, нажмите 'Выбрать редактор' и укажите путь к его исполняемому файлу.")

        except IndexError:
            messagebox.showwarning("Предупреждение", "Выберите сайт из списка.")

    def select_custom_editor(self):
        """Позволяет пользователю выбрать исполняемый файл редактора."""
        editor_path = filedialog.askopenfilename(
            title="Выберите исполняемый файл редактора",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")]
        )
        if editor_path:
            self.custom_editor_path = editor_path
            self.save_config()
            messagebox.showinfo("Успех", f"Редактор '{os.path.basename(editor_path)}' успешно установлен.")

    def start_server(self):
        """Запускает простой HTTP-сервер для выбранного сайта."""
        try:
            selected_index = self.website_listbox.curselection()[0]
            selected_name = self.website_listbox.get(selected_index)
            folder_path = self.websites[selected_name]["path"]

            if self.current_server:
                if self.current_server['path'] == folder_path:
                    messagebox.showinfo("Информация", "Сервер для этого проекта уже запущен.")
                    return
                else:
                    self.stop_server()
                    
            if not os.path.exists(folder_path):
                messagebox.showerror("Ошибка", f"Папка '{folder_path}' не найдена.")
                return

            self.status_bar.config(text=f"Запуск сервера для '{selected_name}'...")
            
            os.chdir(folder_path)
            
            # Поиск доступного порта
            port = 8000
            while True:
                with socketserver.TCPServer(("localhost", port), http.server.SimpleHTTPRequestHandler) as httpd:
                    httpd.server_close()
                break
                
            server_thread = threading.Thread(target=self.run_server, args=(port,), daemon=True)
            server_thread.start()
            
            self.current_server = {
                "name": selected_name,
                "path": folder_path,
                "port": port,
                "thread": server_thread
            }
            
            self.root.after(100, lambda: self.status_bar.config(text=f"Сервер запущен на http://localhost:{port}"))
            webbrowser.open(f'http://localhost:{port}')

        except IndexError:
            messagebox.showwarning("Предупреждение", "Выберите сайт из списка.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить сервер: {e}")

    def run_server(self, port):
        """Внутренняя функция для запуска сервера."""
        try:
            Handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", port), Handler) as httpd:
                self.server_process = httpd
                httpd.serve_forever()
        except OSError:
            pass # Сервер уже остановлен

    def stop_server(self):
        """Останавливает запущенный HTTP-сервер."""
        if self.server_process:
            self.server_process.shutdown()
            self.server_process.server_close()
            self.server_process = None
            self.current_server = None
            self.status_bar.config(text="Сервер остановлен")
            messagebox.showinfo("Информация", "Сервер успешно остановлен.")
        else:
            messagebox.showwarning("Предупреждение", "Сервер не запущен.")
            self.status_bar.config(text="Готово")


if __name__ == "__main__":
    root = tk.Tk()
    app = WebsiteManagerApp(root)
    app.root.mainloop()

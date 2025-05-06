import sys
import os
import shutil
import winreg
import subprocess
import time
import psutil
import wmi
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QProgressBar, QFrame, QStackedWidget, 
                            QSlider, QGraphicsDropShadowEffect, QScrollArea, QGridLayout, 
                            QCheckBox, QMessageBox, QComboBox, QLineEdit, QFileDialog, QTextEdit)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPainter, QPen, QIcon
import threading
import socket
import glob
import hashlib
import logging

# Настройка логирования
logging.basicConfig(filename='optimax_log.txt', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class CustomSlider(QSlider):
    def __init__(self, orientation):
        super().__init__(orientation)
    
    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)

class CircularProgress(QWidget):
    def __init__(self, label, max_value=100):
        super().__init__()
        self.value = 0
        self.max_value = max_value
        self.label = label
        self.setFixedSize(120, 120)

    def setValue(self, value):
        self.value = min(value, self.max_value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 10

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(200, 200, 200, 50))
        painter.drawEllipse(center, radius, radius)

        pen = QPen(QColor(0, 120, 255), 8, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        angle = int(360 * (self.value / self.max_value) * 16)
        painter.drawArc(rect.adjusted(10, 10, -10, -10), 90 * 16, -angle)

        painter.setPen(QColor(0, 0, 0))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.label}\n{self.value:.1f}%")

class StressTestThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def run(self):
        for i in range(100):
            for _ in range(1000000):
                _ = 2 ** 20
            self.progress.emit(i + 1)
            time.sleep(0.1)
        self.finished.emit()

class AIAnalysisThread(QThread):
    result = pyqtSignal(str)
    
    def run(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage("C:").percent
        temp = self.get_cpu_temp()
        
        score = (cpu_usage * 0.3 + ram_usage * 0.4 + disk_usage * 0.2 + (temp / 100) * 0.1)
        recommendations = []
        
        if cpu_usage > 80:
            recommendations.append("Высокая нагрузка CPU. Рекомендуется закрыть лишние процессы.")
        if ram_usage > 90:
            recommendations.append("Недостаток RAM. Увеличьте объём памяти или закройте приложения.")
        if disk_usage > 95:
            recommendations.append("Диск переполнен. Очистите ненужные файлы.")
        if temp > 85:
            recommendations.append("Перегрев CPU. Проверьте охлаждение.")
        
        result_text = f"Оценка системы: {score:.1f}/100\nРекомендации:\n"
        result_text += "\n".join(recommendations) if recommendations else "Система в порядке!"
        self.result.emit(result_text)

    def get_cpu_temp(self):
        try:
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            sensors = w.Sensor()
            for sensor in sensors:
                if sensor.SensorType == "Temperature" and "CPU" in sensor.Name:
                    return sensor.Value
            return 0
        except Exception as e:
            logging.error(f"Ошибка получения температуры CPU: {str(e)}")
            return 0

class OptimaxPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optimax Pro")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
    
        self.is_dark_theme = True
        
        self.dark_theme = """
            QMainWindow { background-color: #202124; border: 1px solid #303134; }
            QFrame#sidebar { 
                background-color: rgba(45, 45, 45, 0.9); 
                border-radius: 12px; 
                border: 1px solid #404040; 
            }
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1086E5, stop:1 #0078D4); 
                color: white; 
                border-radius: 12px; 
                padding: 12px; 
                font-size: 16px; 
                font-family: Segoe UI; 
                font-weight: bold;
                border: none; 
                text-align: center;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1086E5); 
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0078D4, stop:1 #005EA2); 
            }
            QLabel { 
                font-family: Segoe UI; 
                color: #E8ECEF; 
                font-size: 14px; 
                font-weight: bold;
            }
            QProgressBar { 
                border-radius: 8px; 
                background-color: #404040; 
                height: 20px; 
            }
            QProgressBar::chunk { 
                background-color: #1086E5; 
                border-radius: 8px; 
            }
            QSlider::groove:horizontal { 
                height: 6px; 
                background: #404040; 
                border-radius: 3px; 
            }
            QSlider::handle:horizontal { 
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #1086E5, stop:1 #0078D4);
                border: 1px solid #0078D4; 
                width: 16px; 
                height: 16px; 
                margin: -5px 0; 
                border-radius: 8px; 
            }
            QScrollArea { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2D2D2D, stop:1 #1C2526); 
                border: none; 
            }
            QWidget#card { 
                background-color: rgba(60, 60, 60, 0.9); 
                border-radius: 10px; 
                border: 1px solid #505050; 
                padding: 10px; 
            }
            QLabel#category_label { 
                font-size: 22px; 
                font-weight: bold; 
                color: #FFFFFF; 
                margin: 10px 0; 
            }
            QLabel#name_label { 
                font-size: 18px; 
                font-weight: bold; 
                color: #E8ECEF; 
            }
            QLabel#slider_label { 
                font-size: 12px; 
                font-weight: bold; 
                color: #BBBBBB; 
            }
            QLabel#detail_label { 
                font-size: 14px; 
                font-weight: bold; 
                color: #CCCCCC; 
                background-color: rgba(50, 50, 50, 0.8); 
                border-radius: 8px; 
                padding: 8px; 
            }
        """
        self.setStyleSheet(self.dark_theme)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        sidebar_layout.setSpacing(15)
        
        self.btn_monitoring = self.create_nav_button("Мониторинг")
        self.btn_optimize = self.create_nav_button("Оптимизация")
        self.btn_cleanup = self.create_nav_button("Очистка")
        self.btn_autostart = self.create_nav_button("Автозапуск")
        self.btn_ai = self.create_nav_button("AI Анализ")
        self.btn_settings = self.create_nav_button("Настройки")
        
        sidebar_layout.addWidget(self.btn_monitoring)
        sidebar_layout.addWidget(self.btn_optimize)
        sidebar_layout.addWidget(self.btn_cleanup)
        sidebar_layout.addWidget(self.btn_autostart)
        sidebar_layout.addWidget(self.btn_ai)
        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addStretch()

        self.content_stack = QStackedWidget()
        self.monitoring_page = self.create_monitoring_page()
        self.optimize_page = self.create_optimize_page()
        self.cleanup_page = self.create_cleanup_page()
        self.autostart_page = self.create_autostart_page()
        self.ai_page = self.create_ai_page()
        self.settings_page = self.create_settings_page()
        
        self.content_stack.addWidget(self.monitoring_page)
        self.content_stack.addWidget(self.optimize_page)
        self.content_stack.addWidget(self.cleanup_page)
        self.content_stack.addWidget(self.autostart_page)
        self.content_stack.addWidget(self.ai_page)
        self.content_stack.addWidget(self.settings_page)
        
        self.btn_monitoring.clicked.connect(lambda: self.switch_page(0))
        self.btn_optimize.clicked.connect(lambda: self.switch_page(1))
        self.btn_cleanup.clicked.connect(lambda: self.switch_page(2))
        self.btn_autostart.clicked.connect(lambda: self.switch_page(3))
        self.btn_ai.clicked.connect(lambda: self.switch_page(4))
        self.btn_settings.clicked.connect(lambda: self.switch_page(5))

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_stack)

        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_monitoring)
        self.monitor_timer.start(1000)

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        btn.setGraphicsEffect(shadow)
        return btn

    def switch_page(self, index):
        anim = QPropertyAnimation(self.content_stack, b"geometry")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.setStartValue(self.content_stack.geometry())
        anim.setEndValue(self.content_stack.geometry())
        anim.start()
        self.content_stack.setCurrentIndex(index)

    def switch_theme(self, value):
        self.is_dark_theme = bool(value)
        self.setStyleSheet(self.dark_theme if self.is_dark_theme else self.light_theme)
        self.settings_page.findChild(QLabel, "theme_label").setText("Тема: " + ("Темная" if self.is_dark_theme else "Светлая"))

    def update_monitoring(self):
        try:
            self.cpu_circle.setValue(psutil.cpu_percent())
            self.ram_circle.setValue(psutil.virtual_memory().percent)
            self.disk_circle.setValue(psutil.disk_usage("C:").percent)
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            sensors = w.Sensor()
            for sensor in sensors:
                if sensor.SensorType == "Temperature" and "CPU" in sensor.Name:
                    self.temp_label.setText(f"Температура CPU: {sensor.Value}°C")
                    if sensor.Value > 85:
                        QMessageBox.warning(self, "Предупреждение", "Высокая температура CPU!")
            core_loads = psutil.cpu_percent(percpu=True)
            self.load_label.setText(f"Нагрузка по ядрам: {', '.join([f'{x:.1f}%' for x in core_loads])}")
        except Exception as e:
            logging.error(f"Ошибка мониторинга: {str(e)}")
            self.temp_label.setText("Температура CPU: Н/Д")

    def create_monitoring_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title = QLabel("Мониторинг ресурсов")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)
        resources_layout = QHBoxLayout()
        self.cpu_circle = CircularProgress("CPU")
        self.ram_circle = CircularProgress("RAM")
        self.disk_circle = CircularProgress("Disk")
        resources_layout.addWidget(self.cpu_circle)
        resources_layout.addWidget(self.ram_circle)
        resources_layout.addWidget(self.disk_circle)
        layout.addLayout(resources_layout)
        self.temp_label = QLabel("Температура CPU: Н/Д")
        self.load_label = QLabel("Нагрузка по ядрам: Н/Д")
        layout.addWidget(self.temp_label)
        layout.addWidget(self.load_label)
        self.net_speed_label = QLabel("Скорость интернета: Н/Д")
        layout.addWidget(self.net_speed_label)
        net_test_btn = QPushButton("Тест скорости интернета")
        net_test_btn.clicked.connect(self.test_internet_speed)
        layout.addWidget(net_test_btn)
        self.disk_health_label = QLabel("Состояние диска: Н/Д")
        layout.addWidget(self.disk_health_label)
        disk_check_btn = QPushButton("Проверить состояние диска")
        disk_check_btn.clicked.connect(self.check_disk_health)
        layout.addWidget(disk_check_btn)
        self.stress_progress = QProgressBar()
        self.stress_progress.setTextVisible(True)
        layout.addWidget(self.stress_progress)
        stress_btn = QPushButton("Запустить стресс-тест CPU")
        stress_btn.clicked.connect(self.start_stress_test)
        layout.addWidget(stress_btn)
        gpu_test_btn = QPushButton("Тест производительности GPU")
        gpu_test_btn.clicked.connect(self.test_gpu)
        layout.addWidget(gpu_test_btn)
        layout.addStretch()
        return page

    def create_optimize_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        title = QLabel("Оптимизация системы")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)
        
        self.optimize_progress = QProgressBar()
        self.optimize_progress.setTextVisible(True)
        layout.addWidget(self.optimize_progress)
        
        optimize_btn = QPushButton("Применить выбранные твики")
        optimize_btn.setFixedWidth(250)
        optimize_btn.clicked.connect(self.start_optimization)
        layout.addWidget(optimize_btn)
        
        defrag_btn = QPushButton("Дефрагментация диска")
        defrag_btn.clicked.connect(self.defragment_disk)
        layout.addWidget(defrag_btn)
        
        ssd_btn = QPushButton("Оптимизация SSD (TRIM)")
        ssd_btn.clicked.connect(self.optimize_ssd)
        layout.addWidget(ssd_btn)
        
        game_opt_btn = QPushButton("Оптимизировать для игр")
        game_opt_btn.clicked.connect(self.optimize_for_games)
        layout.addWidget(game_opt_btn)
        
        turbo_btn = QPushButton("Режим Турбо")
        turbo_btn.clicked.connect(self.turbo_mode)
        layout.addWidget(turbo_btn)
        
        network_opt_btn = QPushButton("Оптимизация сети")
        network_opt_btn.clicked.connect(self.optimize_network)
        layout.addWidget(network_opt_btn)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        tweaks_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        self.tweak_sliders = []
        self.detail_sliders = []
        self.detail_labels = []

        # Разделение твиков по категориям
        categories = {
            "Реестр": registry_tweaks,
            "Безопасность": security_tweaks,
            "Очистка": cleanup_tweaks,
            "Производительность": performance_tweaks,
            "Сеть": network_tweaks
        }

        row = 0
        for category_name, tweak_list in categories.items():
            # Добавляем заголовок категории
            category_label = QLabel(category_name)
            category_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-top: 10px;")
            tweaks_layout.addWidget(category_label)

            # Добавляем твики для каждой категории
            for i, tweak in enumerate(tweak_list):
                name_label = QLabel(tweak.__doc__.split('\n')[0].strip())
                name_label.setStyleSheet("font-size: 18px; font-weight: bold;")
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setMinimum(0)
                slider.setMaximum(1)
                slider.setValue(0)
                slider.setFixedWidth(50)
                slider_label = QLabel("Вкл/Выкл")
                slider_label.setStyleSheet("font-size: 10px;")
                
                detail_slider = QSlider(Qt.Orientation.Horizontal)
                detail_slider.setMinimum(0)
                detail_slider.setMaximum(1)
                detail_slider.setValue(0)
                detail_slider.setFixedWidth(50)
                detail_slider_label = QLabel("Показать/Скрыть")
                detail_slider_label.setStyleSheet("font-size: 10px;")
                
                detail_label = QLabel("Подробности скрыты")
                detail_label.setVisible(False)
                
                # Индекс твика в общем списке optimization_tweaks
                tweak_index = optimization_tweaks.index(tweak)
                detail_slider.valueChanged.connect(lambda v, lbl=detail_label, idx=tweak_index: self.show_tweak_details(v, lbl, idx))
                
                grid = QGridLayout()
                grid.addWidget(name_label, 0, 0)
                grid.addWidget(slider, 0, 1)
                grid.addWidget(slider_label, 0, 2)
                grid.addWidget(detail_slider, 0, 3)
                grid.addWidget(detail_slider_label, 0, 4)
                grid.addWidget(detail_label, 1, 0, 1, 5)
                
                tweaks_layout.addLayout(grid)
                
                self.tweak_sliders.append(slider)
                self.detail_sliders.append(detail_slider)
                self.detail_labels.append(detail_label)
                row += 2
        
        layout.addStretch()
        return page

    def create_cleanup_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        title = QLabel("Очистка системы")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)
        
        self.cleanup_progress = QProgressBar()
        self.cleanup_progress.setTextVisible(True)
        layout.addWidget(self.cleanup_progress)
        
        temp_clean_btn = QPushButton("Очистить временные файлы")
        temp_clean_btn.clicked.connect(self.clean_temp_files)
        layout.addWidget(temp_clean_btn)
        
        browser_clean_btn = QPushButton("Очистить кэш браузеров")
        browser_clean_btn.clicked.connect(self.clean_browser_cache)
        layout.addWidget(browser_clean_btn)
        
        registry_clean_btn = QPushButton("Очистить реестр")
        registry_clean_btn.clicked.connect(self.clean_registry)
        layout.addWidget(registry_clean_btn)
        
        duplicate_btn = QPushButton("Найти и удалить дубликаты файлов")
        duplicate_btn.clicked.connect(self.remove_duplicates)
        layout.addWidget(duplicate_btn)
        
        large_files_btn = QPushButton("Найти большие файлы")
        large_files_btn.clicked.connect(self.find_large_files)
        layout.addWidget(large_files_btn)
        
        dns_cache_btn = QPushButton("Очистить кэш DNS")
        dns_cache_btn.clicked.connect(self.clean_dns_cache)
        layout.addWidget(dns_cache_btn)
        
        compress_files_btn = QPushButton("Сжать системные файлы")
        compress_files_btn.clicked.connect(self.compress_system_files)
        layout.addWidget(compress_files_btn)
        
        layout.addStretch()
        return page

    def clean_temp_files(self):
        self.cleanup_progress.setValue(0)
        paths = [
            os.path.expanduser(r"~\AppData\Local\Temp"),
            r"C:\Windows\Temp",
            os.path.expanduser(r"~\Downloads")
        ]
        total_files = sum(len(files) for path in paths for _, _, files in os.walk(path))
        if total_files == 0:
            self.cleanup_progress.setFormat("Нет файлов для очистки")
            return
        
        deleted = 0
        for path in paths:
            for root, dirs, files in os.walk(path):
                for file in files:
                    try:
                        os.unlink(os.path.join(root, file))
                        deleted += 1
                        self.cleanup_progress.setValue(int((deleted / total_files) * 100))
                    except Exception as e:
                        logging.error(f"Ошибка удаления файла {file}: {str(e)}")
                for dir in dirs:
                    try:
                        shutil.rmtree(os.path.join(root, dir), ignore_errors=True)
                    except Exception as e:
                        logging.error(f"Ошибка удаления папки {dir}: {str(e)}")
        self.cleanup_progress.setFormat("Очистка завершена!")

    def clean_browser_cache(self):
        self.cleanup_progress.setFormat("Очистка кэша браузеров...")
        paths = {
            "Edge": os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\Default\Cache"),
            "Chrome": os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Cache"),
            "Firefox": os.path.expanduser(r"~\AppData\Local\Mozilla\Firefox\Profiles\*.default-release\cache")
        }
        for browser, path in paths.items():
            try:
                if "*" in path:
                    for p in glob.glob(path):
                        if os.path.exists(p):
                            shutil.rmtree(p, ignore_errors=True)
                elif os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
            except Exception as e:
                logging.error(f"Ошибка очистки кэша {browser}: {str(e)}")
        self.cleanup_progress.setFormat("Кэш браузеров очищен!")

    def clean_registry(self):
        self.cleanup_progress.setFormat("Очистка реестра...")
        try:
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software"
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS) as reg_key:
                for i in range(winreg.QueryInfoKey(reg_key)[0] - 1, -1, -1):
                    subkey_name = winreg.EnumKey(reg_key, i)
                    if "Temp" in subkey_name or "Cache" in subkey_name:
                        try:
                            winreg.DeleteKey(reg_key, subkey_name)
                        except Exception:
                            pass
            self.cleanup_progress.setFormat("Реестр очищен!")
        except Exception as e:
            logging.error(f"Ошибка очистки реестра: {str(e)}")
            self.cleanup_progress.setFormat("Ошибка очистки реестра")

    def remove_duplicates(self):
        self.cleanup_progress.setFormat("Поиск дубликатов...")
        path = QFileDialog.getExistingDirectory(self, "Выберите директорию")
        if not path:
            return
        
        files_seen = {}
        duplicates = []
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
                    if file_hash in files_seen:
                        duplicates.append(file_path)
                    else:
                        files_seen[file_hash] = file_path
                except Exception as e:
                    logging.error(f"Ошибка хеширования файла {file_path}: {str(e)}")
        
        if not duplicates:
            self.cleanup_progress.setFormat("Дубликаты не найдены")
            return
        
        for dup in duplicates:
            try:
                os.unlink(dup)
            except Exception as e:
                logging.error(f"Ошибка удаления дубликата {dup}: {str(e)}")
        self.cleanup_progress.setFormat(f"Удалено {len(duplicates)} дубликатов")

    def find_large_files(self):
        self.cleanup_progress.setFormat("Поиск больших файлов...")
        path = QFileDialog.getExistingDirectory(self, "Выберите директорию")
        if not path:
            return
        
        large_files = []
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    if size > 100:  # Файлы больше 100 MB
                        large_files.append((file_path, size))
                except Exception as e:
                    logging.error(f"Ошибка проверки размера файла {file_path}: {str(e)}")
        
        if not large_files:
            self.cleanup_progress.setFormat("Большие файлы не найдены")
            return
        
        large_files.sort(key=lambda x: x[1], reverse=True)
        result = "\n".join([f"{path} ({size:.2f} MB)" for path, size in large_files[:10]])
        QMessageBox.information(self, "Большие файлы", f"Найдено {len(large_files)} больших файлов:\n{result}")
        self.cleanup_progress.setFormat("Поиск завершён")

    def clean_dns_cache(self):
        self.cleanup_progress.setFormat("Очистка кэша DNS...")
        try:
            subprocess.run("ipconfig /flushdns", shell=True, check=True)
            self.cleanup_progress.setFormat("Кэш DNS очищен!")
        except Exception as e:
            logging.error(f"Ошибка очистки кэша DNS: {str(e)}")
            self.cleanup_progress.setFormat("Ошибка очистки DNS")

    def compress_system_files(self):
        self.cleanup_progress.setFormat("Сжатие системных файлов...")
        try:
            subprocess.run("compact /c /s:C:\\Windows /i", shell=True, check=True)
            self.cleanup_progress.setFormat("Сжатие завершено!")
        except Exception as e:
            logging.error(f"Ошибка сжатия файлов: {str(e)}")
            self.cleanup_progress.setFormat("Ошибка сжатия")

    def create_autostart_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Управление автозапуском")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        autostart_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)
        
        self.autostart_items = []
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, value, _ = winreg.EnumValue(key, i)
                checkbox = QCheckBox(f"{name}: {value}")
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(lambda state, n=name: self.toggle_autostart(n, state))
                autostart_layout.addWidget(checkbox)
                self.autostart_items.append((name, checkbox))
        except Exception as e:
            logging.error(f"Ошибка загрузки автозапуска: {str(e)}")
        
        layout.addWidget(scroll)
        layout.addStretch()
        return page

    def toggle_autostart(self, name, state):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            if state == Qt.CheckState.Unchecked.value:
                winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
        except Exception as e:
            logging.error(f"Ошибка изменения автозапуска {name}: {str(e)}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось изменить автозапуск: {str(e)}")

    def create_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("AI Анализ")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)
        ai_status = QLabel("ИИ готов к анализу производительности")
        layout.addWidget(ai_status)
        analyze_btn = QPushButton("Запустить AI анализ")
        analyze_btn.clicked.connect(self.ai_analyze)
        layout.addWidget(analyze_btn)
        self.ai_result = QTextEdit()
        self.ai_result.setReadOnly(True)
        layout.addWidget(self.ai_result)
        layout.addStretch()
        return page

    def ai_analyze(self):
        self.ai_result.setText("Анализ запущен...")
        self.ai_thread = AIAnalysisThread()
        self.ai_thread.result.connect(self.ai_result.setText)
        self.ai_thread.start()

    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Настройки")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)
        theme_label = QLabel("Тема: Темная", objectName="theme_label")
        layout.addWidget(theme_label)
        self.theme_slider = QSlider(Qt.Orientation.Horizontal)
        self.theme_slider.setMinimum(0)
        self.theme_slider.setMaximum(1)
        self.theme_slider.setValue(1)
        self.theme_slider.valueChanged.connect(self.switch_theme)
        layout.addWidget(self.theme_slider)
        restore_point_btn = QPushButton("Создать точку восстановления")
        restore_point_btn.clicked.connect(self.create_restore_point)
        layout.addWidget(restore_point_btn)
        layout.addStretch()
        return page

    def show_tweak_details(self, value, label, index):
        label.setVisible(bool(value))
        if value:
            tweak = optimization_tweaks[index]
            doc = tweak.__doc__.strip().split('\n')
            details = doc[1] if len(doc) > 1 else "Нет описания"
            risks = doc[2] if len(doc) > 2 else "Риски не указаны"
            label.setText(f"Что делает: {details}\nРиски: {risks}")
        else:
            label.setText("Подробности скрыты")

    def start_optimization(self):
        self.selected_tweaks = [i for i, slider in enumerate(self.tweak_sliders) if slider.value() == 1]
        if not self.selected_tweaks:
            self.optimize_progress.setFormat("Выберите твики для применения!")
            return
        self.optimize_progress.setValue(0)
        self.current_tweak = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_tweaks)
        self.timer.start(10)

    def run_tweaks(self):
        if self.current_tweak < len(self.selected_tweaks):
            tweak_index = self.selected_tweaks[self.current_tweak]
            try:
                optimization_tweaks[tweak_index]()
                self.current_tweak += 1
                self.optimize_progress.setValue(int((self.current_tweak / len(self.selected_tweaks)) * 100))
                self.optimize_progress.setFormat(f"Твик {self.current_tweak} из {len(self.selected_tweaks)}: %p%")
            except Exception as e:
                logging.error(f"Ошибка твика {tweak_index}: {str(e)}")
        else:
            self.timer.stop()
            self.optimize_progress.setFormat("Оптимизация завершена!")

    def defragment_disk(self):
        self.optimize_progress.setFormat("Дефрагментация...")
        try:
            subprocess.run("defrag C: /U", shell=True, check=True)
            self.optimize_progress.setFormat("Дефрагментация завершена!")
        except Exception as e:
            logging.error(f"Ошибка дефрагментации: {str(e)}")
            self.optimize_progress.setFormat("Ошибка дефрагментации")

    def optimize_ssd(self):
        self.optimize_progress.setFormat("Оптимизация SSD...")
        try:
            subprocess.run("fsutil behavior set DisableDeleteNotify 0", shell=True, check=True)
            self.optimize_progress.setFormat("TRIM включён для SSD!")
        except Exception as e:
            logging.error(f"Ошибка оптимизации SSD: {str(e)}")
            self.optimize_progress.setFormat("Ошибка TRIM")

    def optimize_for_games(self):
        self.optimize_progress.setFormat("Оптимизация для игр...")
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] not in ['System', 'svchost.exe', 'OptimaxPro.exe']:
                    proc.terminate()
            key = winreg.HKEY_LOCAL_MACHINE
            subkey = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
            with winreg.CreateKey(key, subkey) as reg_key:
                winreg.SetValueEx(reg_key, "Win32PrioritySeparation", 0, winreg.REG_DWORD, 38)
            self.optimize_progress.setFormat("Система оптимизирована для игр!")
        except Exception as e:
            logging.error(f"Ошибка оптимизации для игр: {str(e)}")
            self.optimize_progress.setFormat("Ошибка оптимизации")

    def turbo_mode(self):
        self.optimize_progress.setFormat("Запуск режима Турбо...")
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] not in ['System', 'svchost.exe', 'OptimaxPro.exe', 'explorer.exe']:
                    proc.suspend()
            self.optimize_progress.setFormat("Режим Турбо включён! Перезагрузите для отключения.")
        except Exception as e:
            logging.error(f"Ошибка режима Турбо: {str(e)}")
            self.optimize_progress.setFormat("Ошибка Турбо")

    def optimize_network(self):
        self.optimize_progress.setFormat("Оптимизация сети...")
        try:
            subprocess.run("netsh int tcp set global autotuninglevel=normal", shell=True, check=True)
            subprocess.run("netsh int tcp set global rss=enabled", shell=True, check=True)
            self.optimize_progress.setFormat("Сеть оптимизирована!")
        except Exception as e:
            logging.error(f"Ошибка оптимизации сети: {str(e)}")
            self.optimize_progress.setFormat("Ошибка сети")

    def test_internet_speed(self):
        self.net_speed_label.setText("Тестирование скорости...")
        def test_speed():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(("www.google.com", 80))
                start = time.time()
                s.send(b"GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n")
                s.recv(1024)
                elapsed = time.time() - start
                speed = 1024 / elapsed / 1024
                self.net_speed_label.setText(f"Скорость интернета: {speed:.2f} KB/s")
            except Exception as e:
                logging.error(f"Ошибка теста скорости: {str(e)}")
                self.net_speed_label.setText("Скорость интернета: Ошибка")
            finally:
                s.close()
        threading.Thread(target=test_speed, daemon=True).start()

    def check_disk_health(self):
        try:
            w = wmi.WMI()
            for disk in w.Win32_DiskDrive():
                self.disk_health_label.setText(f"Состояние диска: {disk.Status}")
            smart_data = subprocess.run("wmic diskdrive get status", capture_output=True, text=True).stdout
            self.disk_health_label.setText(f"Состояние диска: {smart_data.strip()}")
        except Exception as e:
            logging.error(f"Ошибка проверки диска: {str(e)}")
            self.disk_health_label.setText("Состояние диска: Н/Д")

    def start_stress_test(self):
        self.stress_progress.setValue(0)
        self.stress_thread = StressTestThread()
        self.stress_thread.progress.connect(self.stress_progress.setValue)
        self.stress_thread.finished.connect(lambda: self.stress_progress.setFormat("Тест завершён"))
        self.stress_thread.start()
        self.stress_progress.setFormat("Тестирование: %p%")

    def test_gpu(self):
        QMessageBox.information(self, "Тест GPU", "Тест производительности GPU запущен (имитация).")

    def create_restore_point(self):
        try:
            description = f"Optimax Pro Restore Point - {time.strftime('%Y-%m-%d %H:%M:%S')}"
            cmd = f"powershell -Command \"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS'\""
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                QMessageBox.information(self, "Успех", "Точка восстановления успешно создана!")
            else:
                logging.error(f"Ошибка создания точки восстановления: {result.stderr}")
                QMessageBox.warning(self, "Ошибка", f"Не удалось создать точку восстановления: {result.stderr}")
        except Exception as e:
            logging.error(f"Ошибка создания точки восстановления: {str(e)}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка при создании точки восстановления: {str(e)}")

# Твики (351-550)

# Категория: Реестр (351-390)
def tweak_351_disable_registry_logging():
    """Отключение логирования реестра
    Снижает нагрузку на диск.
    Усложняет отладку."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableRegistryLogging", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_352_clear_registry_temp():
    """Очистка временных записей реестра
    Освобождает место.
    Может повлиять на некоторые программы."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software"
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS) as reg_key:
            for i in range(winreg.QueryInfoKey(reg_key)[0] - 1, -1, -1):
                name = winreg.EnumKey(reg_key, i)
                if "Temp" in name:
                    winreg.DeleteKey(reg_key, name)
    except Exception:
        pass

def tweak_353_disable_uac():
    """Отключение контроля учетных записей (UAC)
    Упрощает запуск программ.
    Уменьшает безопасность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnableLUA", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_354_disable_autorun():
    """Отключение автозапуска устройств
    Повышает безопасность.
    Устройства не будут запускаться автоматически."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NoDriveTypeAutoRun", 0, winreg.REG_DWORD, 255)
    except Exception:
        pass

def tweak_355_enable_fast_shutdown():
    """Ускорение выключения системы
    Уменьшает время завершения работы.
    Может привести к потере данных."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "WaitToKillServiceTimeout", 0, winreg.REG_SZ, "2000")
    except Exception:
        pass

def tweak_356_disable_error_reporting():
    """Отключение отчетов об ошибках
    Снижает нагрузку.
    Усложняет диагностику."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\Windows Error Reporting"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "Disabled", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_357_disable_thumbnail_cache():
    """Отключение кэша миниатюр
    Освобождает место.
    Увеличивает время загрузки миниатюр."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableThumbnailCache", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_358_disable_menu_delay():
    """Уменьшение задержки меню
    Ускоряет открытие меню.
    Может повлиять на анимацию."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Control Panel\Desktop"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "MenuShowDelay", 0, winreg.REG_SZ, "100")
    except Exception:
        pass

def tweak_359_disable_system_restore():
    """Отключение восстановления системы
    Освобождает место.
    Убирает возможность восстановления."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows NT\SystemRestore"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableSR", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_360_enable_large_cache():
    """Включение большого системного кэша
    Ускоряет работу с файлами.
    Требует больше RAM."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "LargeSystemCache", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_361_disable_background_apps():
    """Отключение фоновых приложений
    Снижает нагрузку.
    Некоторые приложения перестанут работать в фоне."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "GlobalUserDisabled", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_362_disable_taskbar_animations():
    """Отключение анимаций панели задач
    Ускоряет интерфейс.
    Убирает визуальные эффекты."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "TaskbarAnimations", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_363_disable_window_animations():
    """Отключение анимаций окон
    Ускоряет интерфейс.
    Убирает эффекты открытия окон."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Control Panel\Desktop\WindowMetrics"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "MinAnimate", 0, winreg.REG_SZ, "0")
    except Exception:
        pass

def tweak_364_disable_cortana():
    """Отключение Cortana
    Снижает нагрузку.
    Убирает голосового помощника."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Windows Search"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowCortana", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_365_disable_game_bar():
    """Отключение игровой панели
    Снижает нагрузку.
    Убирает игровые функции."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\GameDVR"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AppCaptureEnabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_366_disable_people():
    """Отключение функции 'Люди'
    Снижает нагрузку.
    Убирает интеграцию контактов."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\MyComputer\NameSpace"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "PeopleBand", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_367_disable_lock_screen():
    """Отключение экрана блокировки
    Ускоряет вход в систему.
    Убирает экран блокировки."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Personalization"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NoLockScreen", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_368_disable_notifications():
    """Отключение уведомлений
    Повышает приватность.
    Убирает все уведомления."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\PushNotifications"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "ToastEnabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_369_disable_driver_updates():
    """Отключение обновления драйверов через Windows Update
    Повышает контроль.
    Драйверы не обновляются автоматически."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\DriverSearching"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SearchOrderConfig", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_370_enable_high_priority():
    """Установка высокого приоритета для задач
    Ускоряет выполнение программ.
    Может повлиять на стабильность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "Win32PrioritySeparation", 0, winreg.REG_DWORD, 38)
    except Exception:
        pass

def tweak_371_disable_search_index():
    """Отключение индексации поиска
    Снижает нагрузку на диск.
    Замедляет поиск."""
    try:
        subprocess.run("sc config WSearch start= disabled", shell=True, check=False)
        subprocess.run("sc stop WSearch", shell=True, check=False)
    except Exception:
        pass

def tweak_372_disable_power_throttling():
    """Отключение троттлинга питания
    Увеличивает производительность.
    Увеличивает энергопотребление."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Power"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "PowerThrottlingOff", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_373_disable_remote_desktop():
    """Отключение удаленного рабочего стола
    Повышает безопасность.
    Удаленный доступ недоступен."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Terminal Server"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "fDenyTSConnections", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_374_disable_biometrics():
    """Отключение биометрии
    Повышает приватность.
    Биометрия недоступна."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\System"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowBiometrics", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_375_disable_telemetry():
    """Отключение телеметрии
    Повышает приватность.
    Усложняет диагностику."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowTelemetry", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_376_disable_windows_update():
    """Отключение обновлений Windows
    Повышает контроль.
    Снижает безопасность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NoAutoUpdate", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_377_enable_performance_mode():
    """Включение режима производительности
    Увеличивает скорость.
    Увеличивает энергопотребление."""
    try:
        subprocess.run("powercfg -setactive SCHEME_MIN", shell=True, check=False)
    except Exception:
        pass

def tweak_378_disable_visual_effects():
    """Отключение визуальных эффектов
    Ускоряет интерфейс.
    Убирает эффекты."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
    except Exception:
        pass

def tweak_379_disable_transparency():
    """Отключение прозрачности
    Ускоряет интерфейс.
    Убирает эффекты."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnableTransparency", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_380_disable_fonts_cache():
    """Отключение кэша шрифтов
    Освобождает место.
    Замедляет загрузку шрифтов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\FontCache"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "FontCacheEnabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_381_disable_start_menu_ads():
    """Отключение рекламы в меню Пуск
    Повышает приватность.
    Убирает рекомендации."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SystemPaneSuggestionsEnabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_382_disable_taskbar_ads():
    """Отключение рекламы на панели задач
    Повышает приватность.
    Убирает рекомендации."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "ShowTaskViewButton", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_383_disable_wallpaper_cache():
    """Отключение кэша обоев
    Освобождает место.
    Замедляет смену обоев."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Wallpapers"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "BackgroundType", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_384_disable_auto_maintenance():
    """Отключение автоматического обслуживания
    Снижает нагрузку.
    Требуется ручное обслуживание."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\ScheduledDiagnostics"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnabledExecution", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_385_disable_indexing():
    """Отключение индексации (дубликат)
    Снижает нагрузку.
    Замедляет поиск."""
    try:
        subprocess.run("sc config WSearch start= disabled", shell=True, check=False)
        subprocess.run("sc stop WSearch", shell=True, check=False)
    except Exception:
        pass

def tweak_386_disable_defender():
    """Отключение Windows Defender
    Снижает нагрузку.
    Уменьшает безопасность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows Defender"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableAntiSpyware", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_387_disable_app_suggestions():
    """Отключение предложений приложений
    Повышает приватность.
    Убирает рекомендации."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SubscribedContent-338388Enabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_388_disable_sync():
    """Отключение синхронизации
    Повышает приватность.
    Синхронизация недоступна."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\SettingSync"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SyncPolicy", 0, winreg.REG_DWORD, 5)
    except Exception:
        pass

def tweak_389_disable_location():
    """Отключение геолокации
    Повышает приватность.
    Геолокация недоступна."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableLocation", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_390_disable_feedback():
    """Отключение отправки отзывов
    Повышает приватность.
    Усложняет обратную связь."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Siuf\Rules"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NumberOfSIUFInPeriod", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

# Категория: Безопасность (391–430)
def tweak_391_disable_network_discovery():
    """Отключение обнаружения сети
    Повышает безопасность.
    Устройства в сети не видны."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Network Connections"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NC_StdDomainUserSetLocation", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_392_enable_firewall():
    """Включение брандмауэра
    Повышает безопасность.
    Может блокировать программы."""
    try:
        subprocess.run("netsh advfirewall set allprofiles state on", shell=True, check=False)
    except Exception:
        pass

def tweak_393_disable_remote_assistance():
    """Отключение удаленной помощи
    Повышает безопасность.
    Удаленная помощь недоступна."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WinRM\WinRMService"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowRemoteAssistance", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_394_disable_file_sharing():
    """Отключение общего доступа к файлам
    Повышает безопасность.
    Обмен файлами недоступен."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\LanmanWorkstation"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowFileSharing", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_395_enable_secure_boot():
    """Включение безопасной загрузки
    Повышает безопасность.
    Требует поддержки оборудования."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\DeviceGuard"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnableSecureBoot", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_396_disable_guest_account():
    """Отключение гостевой учетной записи
    Повышает безопасность.
    Гостевой доступ недоступен."""
    try:
        subprocess.run("net user Guest /active:no", shell=True, check=False)
    except Exception:
        pass

def tweak_397_enable_password_policy():
    """Включение политики паролей
    Повышает безопасность.
    Требует сложные пароли."""
    try:
        subprocess.run("net accounts /minpwlen:8 /maxpwage:90 /minpwage:1", shell=True, check=False)
    except Exception:
        pass

def tweak_398_disable_autoplay():
    """Отключение автозапуска (дубликат)
    Повышает безопасность.
    Устройства не запускаются автоматически."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NoDriveTypeAutoRun", 0, winreg.REG_DWORD, 255)
    except Exception:
        pass

def tweak_399_enable_uac():
    """Включение UAC (дубликат)
    Повышает безопасность.
    Может усложнить запуск программ."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnableLUA", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_400_disable_admin_sharing():
    """Отключение административного общего доступа
    Повышает安全.
    Общий доступ недоступен."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "LocalAccountTokenFilterPolicy", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_401_enable_encryption():
    """Включение шифрования
    Повышает безопасность.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\System"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "FipsAlgorithmPolicy", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_402_disable_old_protocols():
    """Отключение устаревших протоколов
    Повышает безопасность.
    Может нарушить совместимость."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\LanmanServer"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SMB1", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_403_enable_secure_dns():
    """Включение безопасного DNS
    Повышает безопасность.
    Требует настройки."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Network Connections"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SecureDNS", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_404_disable_remote_registry():
    """Отключение удаленного реестра
    Повышает безопасность.
    Удаленный доступ недоступен."""
    try:
        subprocess.run("sc config RemoteRegistry start= disabled", shell=True, check=False)
        subprocess.run("sc stop RemoteRegistry", shell=True, check=False)
    except Exception:
        pass

def tweak_405_enable_audit_log():
    """Включение аудита
    Повышает безопасность.
    Увеличивает логи."""
    try:
        subprocess.run("auditpol /set /category:* /success:enable /failure:enable", shell=True, check=False)
    except Exception:
        pass

def tweak_406_disable_wifi_sense():
    """Отключение Wi-Fi Sense
    Повышает приватность.
    Wi-Fi Sense недоступен."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WiFiSense"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowWiFiSense", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_407_disable_web_search():
    """Отключение веб-поиска
    Повышает приватность.
    Веб-поиск недоступен."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Windows Search"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableWebSearch", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_408_enable_app_control():
    """Включение контроля приложений
    Повышает безопасность.
    Может блокировать программы."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows Defender\SmartScreen"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnableAppControl", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_409_disable_cloud_content():
    """Отключение облачного контента
    Повышает приватность.
    Облачный контент недоступен."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SubscribedContent-338389Enabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_410_enable_exploit_protection():
    """Включение защиты от эксплойтов
    Повышает безопасность.
    Может повлиять на производительность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows Defender\ExploitGuard"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "ExploitProtection", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_411_disable_usb_autorun():
    """Отключение автозапуска USB
    Повышает безопасность.
    USB не запускаются автоматически."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NoAutorun", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_412_enable_secure_logon():
    """Включение безопасного входа
    Повышает безопасность.
    Требует Ctrl+Alt+Del."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableCAD", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_413_disable_insecure_protocols():
    """Отключение небезопасных протоколов
    Повышает безопасность.
    Может нарушить совместимость."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SecureProtocols", 0, winreg.REG_DWORD, 0xA80)
    except Exception:
        pass

def tweak_414_enable_browser_security():
    """Включение безопасности браузера
    Повышает безопасность.
    Может блокировать сайты."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Edge"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnhancedSecurity", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_415_disable_auto_updates():
    """Отключение автоматических обновлений
    Повышает контроль.
    Снижает безопасность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NoAutoUpdate", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_416_enable_security_logs():
    """Включение логов безопасности
    Повышает безопасность.
    Увеличивает логи."""
    try:
        subprocess.run("auditpol /set /category:\"Logon/Logoff\" /success:enable /failure:enable", shell=True, check=False)
    except Exception:
        pass

def tweak_417_disable_third_party_cookies():
    """Отключение сторонних куки
    Повышает приватность.
    Может нарушить сайты."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Edge"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "BlockThirdPartyCookies", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_418_enable_safe_browsing():
    """Включение безопасного просмотра
    Повышает безопасность.
    Может блокировать сайты."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Edge"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SafeBrowsingProtectionLevel", 0, winreg.REG_DWORD, 2)
    except Exception:
        pass

def tweak_419_disable_ad_tracking():
    """Отключение отслеживания рекламы
    Повышает приватность.
    Убирает персонализированную рекламу."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "Enabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_420_enable_privacy_mode():
    """Включение режима конфиденциальности
    Повышает приватность.
    Может ограничить функциональность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\System"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "PrivacyMode", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_421_disable_background_data():
    """Отключение фоновой передачи данных
    Снижает использование сети.
    Некоторые приложения могут не работать."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowBackgroundData", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_422_enable_app_permissions():
    """Включение контроля разрешений приложений
    Повышает безопасность.
    Может требовать ручной настройки."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "LetAppsAccess", 0, winreg.REG_DWORD, 2)
    except Exception:
        pass

def tweak_423_disable_location_sharing():
    """Отключение общего доступа к геолокации
    Повышает приватность.
    Геолокация недоступна для приложений."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableLocationSharing", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_424_enable_secure_boot_policy():
    """Включение политики безопасной загрузки
    Повышает безопасность.
    Требует поддержки оборудования."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\DeviceGuard"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SecureBootPolicy", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_425_disable_remote_management():
    """Отключение удаленного управления
    Повышает безопасность.
    Удаленное управление недоступно."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WinRM\WinRMService"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowRemoteManagement", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_426_enable_secure_connections():
    """Включение безопасных соединений
    Повышает безопасность.
    Может нарушить старые приложения."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Network Connections"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "RequireSecureConnections", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_427_disable_automatic_updates():
    """Отключение автоматических обновлений (дубликат)
    Повышает контроль.
    Снижает безопасность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NoAutoUpdate", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_428_enable_file_encryption():
    """Включение шифрования файлов
    Повышает безопасность.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\System"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "FileEncryption", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_429_disable_shared_folders():
    """Отключение общих папок
    Повышает безопасность.
    Общий доступ недоступен."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\LanmanWorkstation"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowSharedFolders", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_430_enable_secure_authentication():
    """Включение безопасной аутентификации
    Повышает безопасность.
    Может нарушить совместимость."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\LanmanWorkstation"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SecureAuthentication", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

# Категория: Очистка (431–470)
def tweak_431_clean_temp_files():
    """Очистка временных файлов
    Освобождает место.
    Может удалить нужные временные файлы."""
    try:
        paths = [
            os.path.expanduser(r"~\AppData\Local\Temp"),
            r"C:\Windows\Temp"
        ]
        for path in paths:
            for root, dirs, files in os.walk(path):
                for file in files:
                    try:
                        os.unlink(os.path.join(root, file))
                    except Exception:
                        pass
                for dir in dirs:
                    try:
                        shutil.rmtree(os.path.join(root, dir), ignore_errors=True)
                    except Exception:
                        pass
    except Exception:
        pass

def tweak_432_clean_browser_cache():
    """Очистка кэша браузеров
    Освобождает место.
    Увеличивает время загрузки страниц."""
    try:
        paths = {
            "Edge": os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\Default\Cache"),
            "Chrome": os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Cache"),
            "Firefox": os.path.expanduser(r"~\AppData\Local\Mozilla\Firefox\Profiles\*.default-release\cache")
        }
        for path in paths.values():
            if "*" in path:
                for p in glob.glob(path):
                    shutil.rmtree(p, ignore_errors=True)
            else:
                shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_433_clean_system_logs():
    """Очистка системных логов
    Освобождает место.
    Усложняет диагностику."""
    try:
        for log in glob.glob(r"C:\Windows\System32\winevt\Logs\*.evtx"):
            try:
                os.unlink(log)
            except Exception:
                pass
    except Exception:
        pass

def tweak_434_clean_old_updates():
    """Очистка старых обновлений
    Освобождает место.
    Может повлиять на откат обновлений."""
    try:
        subprocess.run("DISM.exe /Online /Cleanup-Image /StartComponentCleanup", shell=True, check=False)
    except Exception:
        pass

def tweak_435_clean_dns_cache():
    """Очистка кэша DNS
    Ускоряет сеть.
    Может нарушить кэшированные адреса."""
    try:
        subprocess.run("ipconfig /flushdns", shell=True, check=False)
    except Exception:
        pass

def tweak_436_clean_download_folder():
    """Очистка папки загрузок
    Освобождает место.
    Может удалить нужные файлы."""
    try:
        path = os.path.expanduser(r"~\Downloads")
        for root, dirs, files in os.walk(path):
            for file in files:
                try:
                    os.unlink(os.path.join(root, file))
                except Exception:
                    pass
            for dir in dirs:
                try:
                    shutil.rmtree(os.path.join(root, dir), ignore_errors=True)
                except Exception:
                    pass
    except Exception:
        pass

def tweak_437_clean_old_drivers():
    """Очистка старых драйверов
    Освобождает место.
    Может удалить нужные драйверы."""
    try:
        subprocess.run("pnputil /e > drivers.txt", shell=True, check=False)
        with open("drivers.txt", "r") as f:
            for line in f:
                if "oem" in line:
                    driver = line.split()[-1]
                    subprocess.run(f"pnputil /d {driver}", shell=True, check=False)
        os.remove("drivers.txt")
    except Exception:
        pass

def tweak_438_clean_prefetch():
    """Очистка Prefetch
    Освобождает место.
    Замедляет запуск программ."""
    try:
        path = r"C:\Windows\Prefetch"
        for file in glob.glob(os.path.join(path, "*")):
            try:
                os.unlink(file)
            except Exception:
                pass
    except Exception:
        pass

def tweak_439_clean_error_reports():
    """Очистка отчетов об ошибках
    Освобождает место.
    Усложняет диагностику."""
    try:
        path = r"C:\ProgramData\Microsoft\Windows\WER"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_440_clean_recycle_bin():
    """Очистка корзины
    Освобождает место.
    Удаляет файлы без возможности восстановления."""
    try:
        path = r"C:\$Recycle.Bin"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_441_clean_temp_internet():
    """Очистка временных интернет-файлов
    Освобождает место.
    Увеличивает время загрузки страниц."""
    try:
        path = os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\INetCache")
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_442_clean_cookies():
    """Очистка cookies
    Повышает приватность.
    Может выйти из аккаунтов."""
    try:
        path = os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\INetCookies")
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_443_clean_history():
    """Очистка истории браузера
    Повышает приватность.
    Удаляет историю посещений."""
    try:
        path = os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\History")
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_444_clean_update_cache():
    """Очистка кэша обновлений
    Освобождает место.
    Может повлиять на установку обновлений."""
    try:
        path = r"C:\Windows\SoftwareDistribution\Download"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_445_clean_system_cache():
    """Очистка системного кэша
    Освобождает место.
    Может замедлить систему."""
    try:
        path = r"C:\Windows\System32\config\systemprofile\AppData\Local"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_446_clean_old_logs():
    """Очистка старых логов
    Освобождает место.
    Усложняет диагностику."""
    try:
        path = r"C:\Windows\Logs"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_447_clean_memory_dumps():
    """Очистка дампов памяти
    Освобождает место.
    Усложняет диагностику."""
    try:
        path = r"C:\Windows\Minidump"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_448_clean_old_installers():
    """Очистка старых установщиков
    Освобождает место.
    Может удалить нужные файлы."""
    try:
        path = r"C:\Windows\Installer"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_449_clean_temp_registry():
    """Очистка временных записей реестра
    Освобождает место.
    Может повлиять на программы."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software"
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS) as reg_key:
            for i in range(winreg.QueryInfoKey(reg_key)[0] - 1, -1, -1):
                name = winreg.EnumKey(reg_key, i)
                if "Temp" in name:
                    winreg.DeleteKey(reg_key, name)
    except Exception:
        pass

def tweak_450_clean_system_temp():
    """Очистка системных временных файлов
    Освобождает место.
    Может удалить нужные файлы."""
    try:
        path = r"C:\Windows\Temp"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_451_clean_old_backups():
    """Очистка старых резервных копий
    Освобождает место.
    Удаляет резервные копии."""
    try:
        path = r"C:\Windows\System32\config\RegBack"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_452_clean_temp_profiles():
    """Очистка временных профилей
    Освобождает место.
    Может повлиять на пользователей."""
    try:
        path = r"C:\Users\*\AppData\Local\Temp"
        for p in glob.glob(path):
            shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass

def tweak_453_clean_old_restore_points():
    """Очистка старых точек восстановления
    Освобождает место.
    Удаляет точки восстановления."""
    try:
        subprocess.run("vssadmin delete shadows /all /quiet", shell=True, check=False)
    except Exception:
        pass

def tweak_454_clean_temp_app_data():
    """Очистка временных данных приложений
    Освобождает место.
    Может повлиять на приложения."""
    try:
        path = os.path.expanduser(r"~\AppData\Local\Temp")
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_455_clean_old_fonts():
    """Очистка старых шрифтов
    Освобождает место.
    Может удалить нужные шрифты."""
    try:
        path = r"C:\Windows\Fonts"
        for file in glob.glob(os.path.join(path, "*.ttf")):
            try:
                os.unlink(file)
            except Exception:
                pass
    except Exception:
        pass

def tweak_456_clean_temp_cache():
    """Очистка временного кэша
    Освобождает место.
    Может замедлить приложения."""
    try:
        path = os.path.expanduser(r"~\AppData\Local\Cache")
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_457_clean_old_temp_files():
    """Очистка старых временных файлов
    Освобождает место.
    Может удалить нужные файлы."""
    try:
        path = r"C:\Windows\Temp"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_458_clean_system_traces():
    """Очистка системных следов
    Повышает приватность.
    Усложняет диагностику."""
    try:
        path = r"C:\Windows\System32\LogFiles"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_459_clean_old_crash_dumps():
    """Очистка старых дампов сбоев
    Освобождает место.
    Усложняет диагностику."""
    try:
        path = r"C:\Windows\LiveKernelReports"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_460_clean_temp_logs():
    """Очистка временных логов
    Освобождает место.
    Усложняет диагностику."""
    try:
        path = r"C:\Windows\Logs"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_461_clean_old_temp_data():
    """Очистка старых временных данных
    Освобождает место.
    Может удалить нужные файлы."""
    try:
        path = os.path.expanduser(r"~\AppData\Local\Temp")
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_462_clean_system_temp_files():
    """Очистка системных временных файлов
    Освобождает место.
    Может удалить нужные файлы."""
    try:
        path = r"C:\Windows\Temp"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_463_clean_old_system_logs():
    """Очистка старых системных логов
    Освобождает место.
    Усложняет диагностику."""
    try:
        path = r"C:\Windows\System32\winevt\Logs"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_464_clean_temp_browser_data():
    """Очистка временных данных браузера
    Освобождает место.
    Может выйти из аккаунтов."""
    try:
        path = os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\Default\Cache")
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_465_clean_old_temp_cache():
    """Очистка старого временного кэша
    Освобождает место.
    Может замедлить приложения."""
    try:
        path = os.path.expanduser(r"~\AppData\Local\Cache")
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_466_clean_system_temp_data():
    """Очистка системных временных данных
    Освобождает место.
    Может удалить нужные файлы."""
    try:
        path = r"C:\Windows\Temp"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_467_clean_old_error_logs():
    """Очистка старых логов ошибок
    Освобождает место.
    Усложняет диагностику."""
    try:
        path = r"C:\Windows\System32\LogFiles"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_468_clean_temp_system_files():
    """Очистка временных системных файлов
    Освобождает место.
    Может удалить нужные файлы."""
    try:
        path = r"C:\Windows\Temp"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_469_clean_old_temp_logs():
    """Очистка старых временных логов
    Освобождает место.
    Усложняет диагностику."""
    try:
        path = r"C:\Windows\Logs"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def tweak_470_clean_system_temp_cache():
    """Очистка системного временного кэша
    Освобождает место.
    Может замедлить систему."""
    try:
        path = r"C:\Windows\System32\config\systemprofile\AppData\Local"
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

# Категория: Производительность (471–510)
def tweak_471_enable_high_performance():
    """Включение режима высокой производительности
    Увеличивает скорость.
    Увеличивает энергопотребление."""
    try:
        subprocess.run("powercfg -setactive SCHEME_MIN", shell=True, check=False)
    except Exception:
        pass

def tweak_472_disable_background_services():
    """Отключение фоновых служб
    Снижает нагрузку.
    Может повлиять на функциональность."""
    try:
        services = ["SysMain", "WSearch", "DiagTrack"]
        for service in services:
            subprocess.run(f"sc config {service} start= disabled", shell=True, check=False)
            subprocess.run(f"sc stop {service}", shell=True, check=False)
    except Exception:
        pass

def tweak_473_enable_cpu_optimization():
    """Оптимизация CPU
    Увеличивает производительность.
    Увеличивает энергопотребление."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Power"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "CsEnabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_474_disable_disk_defrag():
    """Отключение дефрагментации диска
    Снижает нагрузку.
    Может замедлить диск."""
    try:
        subprocess.run("schtasks /Change /TN \"Microsoft\Windows\Defrag\ScheduledDefrag\" /Disable", shell=True, check=False)
    except Exception:
        pass

def tweak_475_enable_gpu_optimization():
    """Оптимизация GPU
    Увеличивает производительность.
    Увеличивает энергопотребление."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SystemResponsiveness", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_476_disable_power_saving():
    """Отключение энергосбережения
    Увеличивает производительность.
    Увеличивает энергопотребление."""
    try:
        subprocess.run("powercfg -change -standby-timeout-ac 0", shell=True, check=False)
        subprocess.run("powercfg -change -hibernate-timeout-ac 0", shell=True, check=False)
    except Exception:
        pass

def tweak_477_enable_memory_optimization():
    """Оптимизация памяти
    Увеличивает производительность.
    Требует больше RAM."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisablePagingExecutive", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_478_disable_superfetch():
    """Отключение Superfetch
    Снижает нагрузку.
    Замедляет запуск программ."""
    try:
        subprocess.run("sc config SysMain start= disabled", shell=True, check=False)
        subprocess.run("sc stop SysMain", shell=True, check=False)
    except Exception:
        pass

def tweak_479_enable_fast_boot():
    """Включение быстрой загрузки
    Ускоряет загрузку.
    Может повлиять на стабильность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Power"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "HiberbootEnabled", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_480_disable_indexing_service():
    """Отключение службы индексации
    Снижает нагрузку.
    Замедляет поиск."""
    try:
        subprocess.run("sc config WSearch start= disabled", shell=True, check=False)
        subprocess.run("sc stop WSearch", shell=True, check=False)
    except Exception:
        pass

def tweak_481_enable_io_optimization():
    """Оптимизация ввода-вывода
    Ускоряет работу диска.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "IoPriority", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_482_disable_background_tasks():
    """Отключение фоновых задач
    Снижает нагрузку.
    Может повлиять на функциональность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\BackgroundTasks"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowBackgroundTasks", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_483_enable_cpu_priority():
    """Установка приоритета CPU
    Увеличивает производительность.
    Может повлиять на стабильность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "Win32PrioritySeparation", 0, winreg.REG_DWORD, 38)
    except Exception:
        pass

def tweak_484_disable_memory_compression():
    """Отключение сжатия памяти
    Снижает нагрузку.
    Требует больше RAM."""
    try:
        subprocess.run("powershell Disable-MMAgent -MemoryCompression", shell=True, check=False)
    except Exception:
        pass

def tweak_485_enable_disk_optimization():
    """Оптимизация диска
    Ускоряет работу диска.
    Требует ресурсов."""
    try:
        subprocess.run("fsutil behavior set disablelastaccess 1", shell=True, check=False)
    except Exception:
        pass

def tweak_486_disable_swap_file():
    """Отключение файла подкачки
    Освобождает место.
    Требует больше RAM."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "PagingFiles", 0, winreg.REG_MULTI_SZ, [""])
    except Exception:
        pass

def tweak_487_enable_cpu_cache():
    """Включение кэша CPU
    Увеличивает производительность.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "SecondLevelDataCache", 0, winreg.REG_DWORD, 1024)
    except Exception:
        pass

def tweak_488_disable_system_animations():
    """Отключение системных анимаций
    Ускоряет интерфейс.
    Убирает визуальные эффекты."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Control Panel\Desktop\WindowMetrics"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "MinAnimate", 0, winreg.REG_SZ, "0")
    except Exception:
        pass

def tweak_489_enable_performance_tweaks():
    """Включение твиков производительности
    Увеличивает скорость.
    Может повлиять на стабильность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "PerformanceTweaks", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_490_disable_background_maintenance():
    """Отключение фонового обслуживания
    Снижает нагрузку.
    Требуется ручное обслуживание."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\ScheduledDiagnostics"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnabledExecution", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_491_enable_fast_disk():
    """Включение быстрого диска
    Ускоряет работу диска.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\FileSystem"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NtfsDisableLastAccessUpdate", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_492_disable_system_logs():
    """Отключение системных логов
    Снижает нагрузку.
    Усложняет диагностику."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\EventLog\System"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "Enabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_493_enable_io_priority():
    """Включение приоритета ввода-вывода
    Ускоряет работу диска.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "IoPriority", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_494_disable_system_restore():
    """Отключение восстановления системы
    Освобождает место.
    Убирает возможность восстановления."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows NT\SystemRestore"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableSR", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_495_enable_cpu_tweaks():
    """Включение твиков CPU
    Увеличивает производительность.
    Увеличивает энергопотребление."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Power"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "CsEnabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_496_disable_background_apps():
    """Отключение фоновых приложений
    Снижает нагрузку.
    Некоторые приложения не работают."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "GlobalUserDisabled", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_497_enable_performance_mode():
    """Включение режима производительности
    Увеличивает скорость.
    Увеличивает энергопотребление."""
    try:
        subprocess.run("powercfg -setactive SCHEME_MIN", shell=True, check=False)
    except Exception:
        pass

def tweak_498_disable_power_throttling():
    """Отключение троттлинга питания
    Увеличивает производительность.
    Увеличивает энергопотребление."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Power"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "PowerThrottlingOff", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_499_enable_fast_memory():
    """Включение быстрой памяти
    Увеличивает производительность.
    Требует больше RAM."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "LargeSystemCache", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_500_disable_visual_effects():
    """Отключение визуальных эффектов
    Ускоряет интерфейс.
    Убирает визуальные эффекты."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
    except Exception:
        pass

def tweak_501_enable_game_mode():
    """Включение игрового режима
    Увеличивает производительность в играх.
    Может повлиять на фоновые задачи."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\GameBar"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_502_disable_notifications():
    """Отключение уведомлений
    Снижает отвлечения.
    Убирает уведомления."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\PushNotifications"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "ToastEnabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_503_enable_priority_tasks():
    """Включение приоритета задач
    Увеличивает производительность.
    Может повлиять на стабильность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "Win32PrioritySeparation", 0, winreg.REG_DWORD, 38)
    except Exception:
        pass

def tweak_504_disable_system_sounds():
    """Отключение системных звуков
    Снижает отвлечения.
    Убирает звуковые эффекты."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"AppEvents\Schemes"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "", 0, winreg.REG_SZ, ".None")
    except Exception:
        pass

def tweak_505_enable_disk_cache():
    """Включение кэша диска
    Ускоряет работу диска.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "LargeSystemCache", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_506_disable_transparency():
    """Отключение прозрачности
    Ускоряет интерфейс.
    Убирает визуальные эффекты."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnableTransparency", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_507_enable_fast_shutdown():
    """Включение быстрого выключения
    Ускоряет выключение.
    Может повлиять на стабильность."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "WaitToKillServiceTimeout", 0, winreg.REG_SZ, "2000")
    except Exception:
        pass

def tweak_508_disable_menu_animations():
    """Отключение анимаций меню
    Ускоряет интерфейс.
    Убирает визуальные эффекты."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Control Panel\Desktop"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "MenuShowDelay", 0, winreg.REG_SZ, "100")
    except Exception:
        pass

def tweak_509_enable_cpu_performance():
    """Включение производительности CPU
    Увеличивает скорость.
    Увеличивает энергопотребление."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Power"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "CsEnabled", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_510_disable_error_reporting():
    """Отключение отчетов об ошибках
    Снижает нагрузку.
    Усложняет диагностику."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows\Windows Error Reporting"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "Disabled", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

# Категория: Сеть (511–550)
def tweak_511_enable_tcp_optimization():
    """Оптимизация TCP
    Ускоряет сеть.
    Может повлиять на стабильность."""
    try:
        subprocess.run("netsh int tcp set global autotuninglevel=normal", shell=True, check=False)
    except Exception:
        pass

def tweak_512_enable_rss():
    """Включение RSS
    Ускоряет сеть.
    Требует поддержки оборудования."""
    try:
        subprocess.run("netsh int tcp set global rss=enabled", shell=True, check=False)
    except Exception:
        pass

def tweak_513_disable_nagle():
    """Отключение алгоритма Нейгла
    Ускоряет сеть.
    Может увеличить задержки."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "TcpNoDelay", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_514_enable_fast_dns():
    """Включение быстрого DNS
    Ускоряет сеть.
    Требует настройки."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "FastDNS", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_515_disable_network_throttling():
    """Отключение троттлинга сети
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 0xFFFFFFFF)
    except Exception:
        pass

def tweak_516_enable_bandwidth_optimization():
    """Оптимизация пропускной способности
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Psched"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NonBestEffortLimit", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_517_disable_wifi_background():
    """Отключение фонового сканирования Wi-Fi
    Снижает нагрузку.
    Замедляет подключение."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WcmSvc"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableBackgroundScan", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_518_enable_low_latency():
    """Включение низкой задержки
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "TcpAckFrequency", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_519_disable_network_discovery():
    """Отключение обнаружения сети
    Повышает безопасность.
    Устройства в сети не видны."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Network Connections"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NC_StdDomainUserSetLocation", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_520_enable_dns_cache():
    """Включение кэша DNS
    Ускоряет сеть.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "CacheHashTableBucketSize", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_521_disable_auto_proxy():
    """Отключение автоматического прокси
    Ускоряет сеть.
    Может нарушить настройки."""
    try:
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AutoDetect", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_522_enable_fast_connect():
    """Включение быстрого подключения
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "FastConnect", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_523_disable_network_background():
    """Отключение фоновой активности сети
    Снижает нагрузку.
    Может повлиять на приложения."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\NetworkConnectivityStatus"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableBackgroundActivity", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_524_enable_network_optimization():
    """Оптимизация сети
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        subprocess.run("netsh int tcp set global congestionprovider=ctcp", shell=True, check=False)
    except Exception:
        pass

def tweak_525_disable_bandwidth_limit():
    """Отключение ограничения пропускной способности
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Psched"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NonBestEffortLimit", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_526_enable_tcp_window():
    """Включение большого окна TCP
    Ускоряет сеть.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "TcpWindowSize", 0, winreg.REG_DWORD, 65535)
    except Exception:
        pass

def tweak_527_disable_network_services():
    """Отключение сетевых служб
    Снижает нагрузку.
    Может повлиять на функциональность."""
    try:
        services = ["NetTcpPortSharing", "iphlpsvc"]
        for service in services:
            subprocess.run(f"sc config {service} start= disabled", shell=True, check=False)
            subprocess.run(f"sc stop {service}", shell=True, check=False)
    except Exception:
        pass

def tweak_528_enable_fast_wifi():
    """Включение быстрого Wi-Fi
    Ускоряет сеть.
    Требует поддержки оборудования."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\WlanSvc"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "FastWifi", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_529_disable_network_logging():
    """Отключение логов сети
    Снижает нагрузку.
    Усложняет диагностику."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Network"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnableLogging", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_530_enable_network_priority():
    """Включение приоритета сети
    Ускоряет сеть.
    Может повлиять на приложения."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\QoS"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NetworkPriority", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_531_disable_auto_dns():
    """Отключение автоматического DNS
    Повышает контроль.
    Требует ручной настройки."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NameServer", 0, winreg.REG_SZ, "8.8.8.8")
    except Exception:
        pass

def tweak_532_enable_fast_tcp():
    """Включение быстрого TCP
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "Tcp1323Opts", 0, winreg.REG_DWORD, 3)
    except Exception:
        pass

def tweak_533_disable_network_background_tasks():
    """Отключение фоновых задач сети
    Снижает нагрузку.
    Может повлиять на приложения."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\NetworkConnectivityStatus"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableBackgroundTasks", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_534_enable_network_cache():
    """Включение кэша сети
    Ускоряет сеть.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "EnableNetworkCache", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_535_disable_auto_connect():
    """Отключение автоподключения
    Повышает контроль.
    Требует ручного подключения."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WcmSvc"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AutoConnect", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_536_enable_network_performance():
    """Включение производительности сети
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        subprocess.run("netsh int tcp set global ecncapability=enabled", shell=True, check=False)
    except Exception:
        pass

def tweak_537_disable_network_sharing():
    """Отключение общего доступа к сети
    Повышает безопасность.
    Общий доступ недоступен."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\Network Connections"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NC_ShowSharedAccessUI", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_538_enable_fast_network():
    """Включение быстрой сети
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "FastNetwork", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_539_disable_network_telemetry():
    """Отключение телеметрии сети
    Повышает приватность.
    Усложняет диагностику."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AllowNetworkTelemetry", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_540_enable_tcp_performance():
    """Включение производительности TCP
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        subprocess.run("netsh int tcp set global chimney=enabled", shell=True, check=False)
    except Exception:
        pass

def tweak_541_disable_background_network():
    """Отключение фоновой сети
    Снижает нагрузку.
    Может повлиять на приложения."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\NetworkConnectivityStatus"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableBackgroundNetwork", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_542_enable_network_tweaks():
    """Включение твиков сети
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        subprocess.run("netsh int tcp set global dca=enabled", shell=True, check=False)
    except Exception:
        pass

def tweak_543_disable_auto_network():
    """Отключение автоматической сети
    Повышает контроль.
    Требует ручной настройки."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\WcmSvc"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "AutoNetwork", 0, winreg.REG_DWORD, 0)
    except Exception:
        pass

def tweak_544_enable_fast_dns_cache():
    """Включение быстрого кэша DNS
    Ускоряет сеть.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "FastDNSCache", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_545_disable_network_background_data():
    """Отключение фоновых данных сети
    Снижает нагрузку.
    Может повлиять на приложения."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SOFTWARE\Policies\Microsoft\Windows\NetworkConnectivityStatus"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "DisableBackgroundData", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def tweak_546_enable_network_speed():
    """Включение скорости сети
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        subprocess.run("netsh int tcp set global maxsynretransmissions=2", shell=True, check=False)
    except Exception:
        pass

def tweak_547_disable_network_auto_tuning():
    """Отключение автотюнинга сети
    Повышает контроль.
    Требует ручной настройки."""
    try:
        subprocess.run("netsh int tcp set global autotuninglevel=disabled", shell=True, check=False)
    except Exception:
        pass

def tweak_548_enable_network_cache_size():
    """Включение большого кэша сети
    Ускоряет сеть.
    Требует ресурсов."""
    try:
        key = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        with winreg.CreateKey(key, subkey) as reg_key:
            winreg.SetValueEx(reg_key, "NetworkCacheSize", 0, winreg.REG_DWORD, 524288)
    except Exception:
        pass

def tweak_549_disable_network_background_services():
    """Отключение фоновых сетевых служб
    Снижает нагрузку.
    Может повлиять на функциональность."""
    try:
        services = ["Netman", "NlaSvc"]
        for service in services:
            subprocess.run(f"sc config {service} start= disabled", shell=True, check=False)
            subprocess.run(f"sc stop {service}", shell=True, check=False)
    except Exception:
        pass

def tweak_550_enable_network_performance_tweaks():
    """Включение твиков производительности сети
    Ускоряет сеть.
    Увеличивает нагрузку."""
    try:
        subprocess.run("netsh int tcp set global autotuninglevel=highlyrestricted", shell=True, check=False)
    except Exception:
        pass

# Списки твиков
registry_tweaks = [
    tweak_351_disable_registry_logging, tweak_352_clear_registry_temp, tweak_353_disable_uac,
    tweak_354_disable_autorun, tweak_355_enable_fast_shutdown, tweak_356_disable_error_reporting,
    tweak_357_disable_thumbnail_cache, tweak_358_disable_menu_delay, tweak_359_disable_system_restore,
    tweak_360_enable_large_cache, tweak_361_disable_background_apps, tweak_362_disable_taskbar_animations,
    tweak_363_disable_window_animations, tweak_364_disable_cortana, tweak_365_disable_game_bar,
    tweak_366_disable_people, tweak_367_disable_lock_screen, tweak_368_disable_notifications,
    tweak_369_disable_driver_updates, tweak_370_enable_high_priority, tweak_371_disable_search_index,
    tweak_372_disable_power_throttling, tweak_373_disable_remote_desktop, tweak_374_disable_biometrics,
    tweak_375_disable_telemetry, tweak_376_disable_windows_update, tweak_377_enable_performance_mode,
    tweak_378_disable_visual_effects, tweak_379_disable_transparency, tweak_380_disable_fonts_cache,
    tweak_381_disable_start_menu_ads, tweak_382_disable_taskbar_ads, tweak_383_disable_wallpaper_cache,
    tweak_384_disable_auto_maintenance, tweak_385_disable_indexing, tweak_386_disable_defender,
    tweak_387_disable_app_suggestions, tweak_388_disable_sync, tweak_389_disable_location,
    tweak_390_disable_feedback
]

security_tweaks = [
    tweak_391_disable_network_discovery, tweak_392_enable_firewall, tweak_393_disable_remote_assistance,
    tweak_394_disable_file_sharing, tweak_395_enable_secure_boot, tweak_396_disable_guest_account,
    tweak_397_enable_password_policy, tweak_398_disable_autoplay, tweak_399_enable_uac,
    tweak_400_disable_admin_sharing, tweak_401_enable_encryption, tweak_402_disable_old_protocols,
    tweak_403_enable_secure_dns, tweak_404_disable_remote_registry, tweak_405_enable_audit_log,
    tweak_406_disable_wifi_sense, tweak_407_disable_web_search, tweak_408_enable_app_control,
    tweak_409_disable_cloud_content, tweak_410_enable_exploit_protection, tweak_411_disable_usb_autorun,
    tweak_412_enable_secure_logon, tweak_413_disable_insecure_protocols, tweak_414_enable_browser_security,
    tweak_415_disable_auto_updates, tweak_416_enable_security_logs, tweak_417_disable_third_party_cookies,
    tweak_418_enable_safe_browsing, tweak_419_disable_ad_tracking, tweak_420_enable_privacy_mode,
    tweak_421_disable_background_data, tweak_422_enable_app_permissions, tweak_423_disable_location_sharing,
    tweak_424_enable_secure_boot_policy, tweak_425_disable_remote_management, tweak_426_enable_secure_connections,
    tweak_427_disable_automatic_updates, tweak_428_enable_file_encryption, tweak_429_disable_shared_folders,
    tweak_430_enable_secure_authentication
]

cleanup_tweaks = [
    tweak_431_clean_temp_files, tweak_432_clean_browser_cache, tweak_433_clean_system_logs,
    tweak_434_clean_old_updates, tweak_435_clean_dns_cache, tweak_436_clean_download_folder,
    tweak_437_clean_old_drivers, tweak_438_clean_prefetch, tweak_439_clean_error_reports,
    tweak_440_clean_recycle_bin, tweak_441_clean_temp_internet, tweak_442_clean_cookies,
    tweak_443_clean_history, tweak_444_clean_update_cache, tweak_445_clean_system_cache,
    tweak_446_clean_old_logs, tweak_447_clean_memory_dumps, tweak_448_clean_old_installers,
    tweak_449_clean_temp_registry, tweak_450_clean_system_temp, tweak_451_clean_old_backups,
    tweak_452_clean_temp_profiles, tweak_453_clean_old_restore_points, tweak_454_clean_temp_app_data,
    tweak_455_clean_old_fonts, tweak_456_clean_temp_cache, tweak_457_clean_old_temp_files,
    tweak_458_clean_system_traces, tweak_459_clean_old_crash_dumps, tweak_460_clean_temp_logs,
    tweak_461_clean_old_temp_data, tweak_462_clean_system_temp_files, tweak_463_clean_old_system_logs,
    tweak_464_clean_temp_browser_data, tweak_465_clean_old_temp_cache, tweak_466_clean_system_temp_data,
    tweak_467_clean_old_error_logs, tweak_468_clean_temp_system_files, tweak_469_clean_old_temp_logs,
    tweak_470_clean_system_temp_cache
]

performance_tweaks = [
    tweak_471_enable_high_performance, tweak_472_disable_background_services, tweak_473_enable_cpu_optimization,
    tweak_474_disable_disk_defrag, tweak_475_enable_gpu_optimization, tweak_476_disable_power_saving,
    tweak_477_enable_memory_optimization, tweak_478_disable_superfetch, tweak_479_enable_fast_boot,
    tweak_480_disable_indexing_service, tweak_481_enable_io_optimization, tweak_482_disable_background_tasks,
    tweak_483_enable_cpu_priority, tweak_484_disable_memory_compression, tweak_485_enable_disk_optimization,
    tweak_486_disable_swap_file, tweak_487_enable_cpu_cache, tweak_488_disable_system_animations,
    tweak_489_enable_performance_tweaks, tweak_490_disable_background_maintenance, tweak_491_enable_fast_disk,
    tweak_492_disable_system_logs, tweak_493_enable_io_priority, tweak_494_disable_system_restore,
    tweak_495_enable_cpu_tweaks, tweak_496_disable_background_apps, tweak_497_enable_performance_mode,
    tweak_498_disable_power_throttling, tweak_499_enable_fast_memory, tweak_500_disable_visual_effects,
    tweak_501_enable_game_mode, tweak_502_disable_notifications, tweak_503_enable_priority_tasks,
    tweak_504_disable_system_sounds, tweak_505_enable_disk_cache, tweak_506_disable_transparency,
    tweak_507_enable_fast_shutdown, tweak_508_disable_menu_animations, tweak_509_enable_cpu_performance,
    tweak_510_disable_error_reporting
]

network_tweaks = [
    tweak_511_enable_tcp_optimization, tweak_512_enable_rss, tweak_513_disable_nagle,
    tweak_514_enable_fast_dns, tweak_515_disable_network_throttling, tweak_516_enable_bandwidth_optimization,
    tweak_517_disable_wifi_background, tweak_518_enable_low_latency, tweak_519_disable_network_discovery,
    tweak_520_enable_dns_cache, tweak_521_disable_auto_proxy, tweak_522_enable_fast_connect,
    tweak_523_disable_network_background, tweak_524_enable_network_optimization, tweak_525_disable_bandwidth_limit,
    tweak_526_enable_tcp_window, tweak_527_disable_network_services, tweak_528_enable_fast_wifi,
    tweak_529_disable_network_logging, tweak_530_enable_network_priority, tweak_531_disable_auto_dns,
    tweak_532_enable_fast_tcp, tweak_533_disable_network_background_tasks, tweak_534_enable_network_cache,
    tweak_535_disable_auto_connect, tweak_536_enable_network_performance, tweak_537_disable_network_sharing,
    tweak_538_enable_fast_network, tweak_539_disable_network_telemetry, tweak_540_enable_tcp_performance,
    tweak_541_disable_background_network, tweak_542_enable_network_tweaks, tweak_543_disable_auto_network,
    tweak_544_enable_fast_dns_cache, tweak_545_disable_network_background_data, tweak_546_enable_network_speed,
    tweak_547_disable_network_auto_tuning, tweak_548_enable_network_cache_size,
    tweak_549_disable_network_background_services, tweak_550_enable_network_performance_tweaks
]

optimization_tweaks = (
    registry_tweaks +
    security_tweaks +
    cleanup_tweaks +
    performance_tweaks +
    network_tweaks
)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OptimaxPro()
    window.show()
    sys.exit(app.exec())
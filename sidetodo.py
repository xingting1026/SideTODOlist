import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTextEdit, 
                            QLabel, QPushButton, QListWidget, QListWidgetItem,
                            QHBoxLayout, QCheckBox, QFrame)
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize
from PyQt5.QtGui import QFont, QIcon, QScreen, QCursor, QColor
import winreg as reg  # 用於設置開機自啟動

class TodoSidebar(QWidget):
    def __init__(self):
        super().__init__()
        
        # 設置窗口無邊框、置頂和透明度
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 無邊框
            Qt.WindowStaysOnTopHint | # 置頂
            Qt.Tool                   # 不在任務欄顯示
        )
        
        # 設置透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 初始化界面
        self.init_ui()
        
        # 設置鼠標追蹤和顯示/隱藏計時器
        self.check_mouse_timer = QTimer(self)
        self.check_mouse_timer.timeout.connect(self.check_mouse_position)
        self.check_mouse_timer.start(100)  # 每100毫秒檢查一次
        
        # 是否正在顯示
        self.is_visible = False
        
        # 設置觸發區域寬度（增加感應範圍）
        self.trigger_width = 20
        
        # 添加用於追蹤勾選項目的字典和計時器
        self.checked_items = {}  # 儲存已勾選項目的ID和計時器
        
        # 初始隱藏
        self.hide()
        
        # 加載已保存的任務
        self.load_tasks()
        
    def init_ui(self):
        # 獲取屏幕尺寸
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        
        # 設置窗口位置和大小（右側邊欄）
        sidebar_width = 300
        self.setGeometry(
            self.screen_width - sidebar_width, 0, 
            sidebar_width, self.screen_height
        )
        
        # 設置佈局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 20, 10, 20)
        main_layout.setSpacing(10)
        
        # 標題容器 - 使用米白色半透明背景
        title_container = QFrame()
        title_container.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(5, 5, 5, 5)
        
        # 標題
        title = QLabel("待辦事項")
        title.setFont(QFont("微軟正黑體", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: black;")
        title_layout.addWidget(title)
        
        main_layout.addWidget(title_container)
        
        # 中間部分 - 顯示圖片背景和任務列表
        middle_container = QFrame()
        middle_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        middle_layout = QVBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        
        # 任務列表
        self.todo_list = QListWidget()
        self.todo_list.setDragDropMode(QListWidget.InternalMove)  # 啟用拖拽重排功能
        self.todo_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: black;
                padding: 5px;
                font-family: 微軟正黑體;
                font-size: 14px;
                outline: none;  /* 移除焦點輪廓 */
            }
            QListWidget::item {
                background-color: rgba(255, 255, 255, 200);
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 5px;
                height: 30px;
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 200);  /* 保持與正常背景相同 */
                color: black;  /* 保持與正常文字顏色相同 */
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 200);  /* 保持與正常背景相同 */
            }
            QListWidget::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        middle_layout.addWidget(self.todo_list)
        
        # 連接勾選狀態改變的信號
        self.todo_list.itemChanged.connect(self.on_item_checked)
        # 連接重繪信號，確保項目樣式保持一致
        self.todo_list.model().rowsRemoved.connect(self.refresh_list_style)
        self.todo_list.model().rowsMoved.connect(self.refresh_list_style)
        self.todo_list.selectionModel().selectionChanged.connect(self.selection_changed)  # 選擇變化時強制刷新樣式
        
        # 連接拖拽完成後的信號
        self.todo_list.dropEvent = self.custom_drop_event
        
        main_layout.addWidget(middle_container)
        
        # 下半部分 - 使用米白色半透明背景
        bottom_container = QFrame()
        bottom_container.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(8)
        
        # 添加新任務的輸入框
        self.new_task_input = QTextEdit()
        self.new_task_input.setPlaceholderText("輸入新的待辦事項...")
        self.new_task_input.setMaximumHeight(80)
        self.new_task_input.setFont(QFont("微軟正黑體", 12))
        self.new_task_input.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 180);
                border: 1px solid #cccccc;
                border-radius: 5px;
                color: black;
                padding: 5px;
            }
        """)
        bottom_layout.addWidget(self.new_task_input)
        
        # 直接添加重要性勾選框，不使用額外的容器框架
        self.important_checkbox = QCheckBox("標記為重要")
        self.important_checkbox.setFont(QFont("微軟正黑體", 12))
        self.important_checkbox.setStyleSheet("""
            QCheckBox {
                color: black;
                background-color: transparent;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        bottom_layout.addWidget(self.important_checkbox)
        
        # 按鈕布局
        buttons_layout = QHBoxLayout()
        
        # 添加按鈕
        add_button = QPushButton("添加任務")
        add_button.clicked.connect(self.add_task)
        add_button.setFont(QFont("微軟正黑體", 12))
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #00599f;
            }
        """)
        buttons_layout.addWidget(add_button)
        
        # 刪除按鈕
        delete_button = QPushButton("刪除已勾選")
        delete_button.clicked.connect(self.remove_checked)
        delete_button.setFont(QFont("微軟正黑體", 12))
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        buttons_layout.addWidget(delete_button)
        
        bottom_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(bottom_container)
        
        # 設置整體窗口樣式 - 只為中間部分設置背景圖像
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 20, 180);
                border-radius: 15px;
            }
        """)
        
        # 使用絕對路徑設置背景圖片
        # 獲取程序所在目錄
        app_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(app_dir, 'image.png')
        
        # 檢查圖片是否存在
        if os.path.exists(image_path):
            # 將路徑中的反斜杠替換為正斜杠，避免CSS解析問題
            image_path = image_path.replace('\\', '/')
            middle_container.setStyleSheet(f"""
                QFrame {{
                    background-image: url('{image_path}');
                    background-position: center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    border: none;
                }}
            """)
        else:
            # 圖片不存在時使用純色背景
            print(f"警告: 背景圖片不存在 - {image_path}")
            middle_container.setStyleSheet("""
                QFrame {
                    background-color: rgba(230, 230, 230, 100);
                    border: none;
                }
            """)
        
        # 設定部分比例
        main_layout.setStretch(0, 0)  # 標題
        main_layout.setStretch(1, 3)  # 中間部分
        main_layout.setStretch(2, 1)  # 下半部分
        
        self.setLayout(main_layout)
    
    def selection_changed(self, selected, deselected):
        """當選中狀態改變時，強制刷新樣式來防止項目變藍"""
        self.refresh_list_style()
    
    def custom_drop_event(self, event):
        # 調用原始的 dropEvent 方法
        QListWidget.dropEvent(self.todo_list, event)
        # 在拖放操作後刷新樣式
        QTimer.singleShot(50, self.refresh_list_style)
        # 保存最新的任務順序
        self.save_tasks()
        
    def refresh_list_style(self):
        """刷新所有列表項目的樣式"""
        # 強制列表重新應用樣式
        current_style = self.todo_list.styleSheet()
        self.todo_list.setStyleSheet("/* 臨時樣式變更 */")
        self.todo_list.setStyleSheet(current_style)
        
        # 重新應用每個項目的樣式
        for i in range(self.todo_list.count()):
            item = self.todo_list.item(i)
            if not item:
                continue
                
            # 確保重要標記的任務保持紅色文字
            task_type = item.data(Qt.UserRole + 1)
            if task_type == "important":
                item.setForeground(QColor(200, 0, 0))
        
        # 強制更新視圖
        self.todo_list.repaint()
        
    def check_mouse_position(self):
        # 獲取鼠標位置
        cursor_x = QCursor.pos().x()
        cursor_y = QCursor.pos().y()
        
        # 定義觸發區域（屏幕右側邊緣）
        trigger_area = QRect(
            self.screen_width - self.trigger_width, 
            0, 
            self.trigger_width, 
            self.screen_height
        )
        
        # 獲取側邊欄的區域
        sidebar_area = self.geometry()
        
        # 如果鼠標在觸發區域內且側邊欄未顯示，則顯示側邊欄
        if trigger_area.contains(cursor_x, cursor_y) and not self.is_visible:
            self.show()
            self.is_visible = True
            # 顯示時更新樣式
            QTimer.singleShot(100, self.refresh_list_style)
            
        # 如果鼠標不在側邊欄區域內且側邊欄正在顯示，則隱藏側邊欄
        elif self.is_visible and not sidebar_area.contains(cursor_x, cursor_y):
            self.hide()
            self.is_visible = False
            
    def add_task(self):
        task_text = self.new_task_input.toPlainText().strip()
        if task_text:
            item = QListWidgetItem(task_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            item.setCheckState(Qt.Unchecked)
            
            # 為項目設置唯一ID
            item.setData(Qt.UserRole, id(item))
            
            # 如果標記為重要，設置文本顏色為紅色
            if self.important_checkbox.isChecked():
                item.setForeground(QColor(200, 0, 0))
                # 為重要任務設置樣式
                item.setData(Qt.UserRole + 1, "important")
            else:
                item.setData(Qt.UserRole + 1, "normal")
            
            self.todo_list.addItem(item)
            self.new_task_input.clear()
            self.important_checkbox.setChecked(False)
            
            # 刷新列表樣式
            QTimer.singleShot(50, self.refresh_list_style)
            
            # 保存到文件
            self.save_tasks()
    
    def remove_checked(self):
        """刪除所有已勾選的項目"""
        for i in range(self.todo_list.count() - 1, -1, -1):
            item = self.todo_list.item(i)
            if item and item.checkState() == Qt.Checked:
                # 如果有計時器，停止並刪除
                item_id = item.data(Qt.UserRole)
                if item_id in self.checked_items:
                    self.checked_items[item_id].stop()
                    del self.checked_items[item_id]
                self.todo_list.takeItem(i)
                
        # 刷新列表樣式        
        QTimer.singleShot(50, self.refresh_list_style)
                
        # 保存到文件
        self.save_tasks()
            
    def save_tasks(self):
        """保存任務到文件"""
        save_path = os.path.join(os.path.expanduser("~"), "todo_sidebar_tasks.txt")
        with open(save_path, "w", encoding="utf-8") as f:
            for i in range(self.todo_list.count()):
                item = self.todo_list.item(i)
                if not item:
                    continue
                checked = "1" if item.checkState() == Qt.Checked else "0"
                # 保存任務類型（重要或普通）
                task_type = item.data(Qt.UserRole + 1) or "normal"
                f.write(f"{checked}||{task_type}||{item.text()}\n")
                
    def load_tasks(self):
        """從文件加載任務"""
        save_path = os.path.join(os.path.expanduser("~"), "todo_sidebar_tasks.txt")
        if os.path.exists(save_path):
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            parts = line.split("||", 2)
                            if len(parts) == 3:
                                checked, task_type, text = parts
                                item = QListWidgetItem(text)
                                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
                                item.setCheckState(Qt.Checked if checked == "1" else Qt.Unchecked)
                                
                                # 設置唯一ID
                                item.setData(Qt.UserRole, id(item))
                                
                                # 設置任務類型
                                item.setData(Qt.UserRole + 1, task_type)
                                
                                # 設置重要任務的顏色
                                if task_type == "important":
                                    item.setForeground(QColor(200, 0, 0))
                                    
                                self.todo_list.addItem(item)
                
                # 確保所有項目樣式正確
                QTimer.singleShot(100, self.refresh_list_style)
                
            except Exception as e:
                print(f"加載任務時出錯: {e}")
                
    def on_item_checked(self, item):
        """當項目勾選狀態變化時調用"""
        # 使用項目的唯一ID作為字典鍵
        item_id = item.data(Qt.UserRole)
        
        if item.checkState() == Qt.Checked:
            # 如果項目已經在字典中有計時器，先清除舊計時器
            if item_id in self.checked_items:
                self.checked_items[item_id].stop()
                
            # 創建新計時器，3秒後刪除該項目
            timer = QTimer(self)
            timer.setSingleShot(True)  # 單次觸發
            timer.timeout.connect(lambda item_id=item_id: self.remove_checked_item(item_id))
            timer.start(3000)  # 3000毫秒 = 3秒
            
            # 將計時器保存到字典中
            self.checked_items[item_id] = timer
        elif item_id in self.checked_items:
            # 如果取消勾選，停止計時器並從字典中移除
            self.checked_items[item_id].stop()
            del self.checked_items[item_id]
            
        # 保存到文件
        self.save_tasks()
            
    def remove_checked_item(self, item_id):
        """刪除已勾選的項目"""
        # 通過ID查找項目
        for i in range(self.todo_list.count()):
            item = self.todo_list.item(i)
            if item and item.data(Qt.UserRole) == item_id:
                self.todo_list.takeItem(i)
                # 從字典中移除
                if item_id in self.checked_items:
                    del self.checked_items[item_id]
                # 保存到文件
                self.save_tasks()
                # 刷新列表樣式
                QTimer.singleShot(50, self.refresh_list_style)
                break

def set_autostart():
    """設置開機自啟動"""
    # 獲取當前腳本的路徑
    script_path = os.path.abspath(sys.argv[0])
    
    # 設置註冊表項
    key = reg.HKEY_CURRENT_USER
    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        # 打開註冊表鍵
        key_handle = reg.OpenKey(key, key_path, 0, reg.KEY_WRITE)
        # 添加程序到啟動項
        reg.SetValueEx(key_handle, "TodoSidebar", 0, reg.REG_SZ, f'"{sys.executable}" "{script_path}"')
        reg.CloseKey(key_handle)
        print("已設置開機自啟動")
    except Exception as e:
        print(f"設置開機自啟動失敗: {e}")

if __name__ == "__main__":
    # 設置開機自啟動
    set_autostart()
    
    app = QApplication(sys.argv)
    
    # 設置應用程序圖標（如果有的話）
    # app.setWindowIcon(QIcon("icon.png"))
    
    sidebar = TodoSidebar()
    
    sys.exit(app.exec_())
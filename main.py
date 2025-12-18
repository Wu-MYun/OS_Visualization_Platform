# main.py
# 应用启动入口

import sys
import os

# 🌟 关键修正：在任何其他导入之前，强制添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)
    print(f"Added project root to Python path: {project_root}")


from PyQt6.QtWidgets import QApplication

# 现在可以正常导入 qt_frontend 和 visuals/src 等顶层包
from qt_frontend.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        main_window = MainWindow()
        main_window.show()
    except ImportError as e:
        print(f"Import Error: {e}")
        print("致命错误：请检查主窗口类和所有依赖文件的导入路径。")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

    sys.exit(app.exec())

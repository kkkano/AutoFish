# pip install pyautogui pynput pystray Pillow pywebview
import tkinter as tk
from tkinter import ttk
import threading
import datetime
import os
import sys
import ctypes
from pynput import keyboard
import pystray
from PIL import Image, ImageDraw
from .config import load_config
from .modules.browser import BrowserModule
from .modules.mouse import MouseModule
from .modules.salary import SalaryModule
from .utils import app_root, resource_path

class MouseMoverApp(MouseModule, SalaryModule, BrowserModule):
    def __init__(self, root):
        self.root = root
        self.root.title("智能办公助手(自用工具箱)")
        
        # 初始化变量
        self.is_running = False
        self.exit_event = threading.Event()
        self.listener = None
        self.start_time = None
        self.total_seconds = 0
        self.salary_enabled = tk.BooleanVar(value=False)
        self.detail_mode = tk.BooleanVar(value=False)  # 详细模式
        self.monthly_salary = tk.StringVar(value="10000")
        self.work_days = tk.StringVar(value="22")
        self.earnings_var = tk.StringVar(value="¥0.00")
        self.net_salary_var = tk.StringVar(value="税后: --")
        
        # 五险一金 (2026标准) - 使用 StringVar 方便 Entry 绑定
        self.social_base = tk.StringVar(value="10000")
        
        self.rate_pension = tk.StringVar(value="8.0")
        self.val_pension = tk.StringVar(value="800.00")
        
        self.rate_medical = tk.StringVar(value="2.0")
        self.val_medical = tk.StringVar(value="200.00")
        
        self.rate_unemploy = tk.StringVar(value="0.5")
        self.val_unemploy = tk.StringVar(value="50.00")
        
        self.rate_housing = tk.StringVar(value="8.0")
        self.val_housing = tk.StringVar(value="800.00")
        
        self.custom_deduction = tk.StringVar(value="0") # 专项附加扣除
        
        # 初始化同步标记
        for v in [self.rate_pension, self.val_pension, self.rate_medical, self.val_medical, 
                 self.rate_unemploy, self.val_unemploy, self.rate_housing, self.val_housing]:
            v._syncing = False
        
        # 老板键相关
        self.is_hidden = False
        self.tray_icon = None
        self.pressed_keys = set()  # 跟踪当前按下的键

        # 光标信息（实时 XY / RGB）
        self.cursor_info_enabled = tk.BooleanVar(value=False)
        self.cursor_xy_var = tk.StringVar(value="XY: --")
        self.cursor_rgb_var = tk.StringVar(value="RGB: --")
        self.cursor_hex_var = tk.StringVar(value="HEX: --")
        self._cursor_info_after_id = None
        self._cursor_color_swatch = None

        # 无边框模式辅助（自动撑开 + 可拖拽拉伸）
        self._borderless_prev_geometry = None
        self._borderless_prev_minsize = None
        self._resize_grip = None
        self._resize_active = False
        self._resize_start = None
        
        # UI隐蔽性控制
        self.opacity_var = tk.DoubleVar(value=100)  # 透明度 0-100%
        self.topmost_var = tk.BooleanVar(value=False)  # 窗口置顶
        self.borderless_var = tk.BooleanVar(value=False)  # 无边框模式
        config = load_config()
        self.title_presets = list(config.get("title_presets", []))
        if not self.title_presets:
            self.title_presets = ["智能办公助手 [F9/Ctrl+Alt+H 隐藏]"]
        self.current_title = tk.StringVar(value=self.title_presets[0])
        
        # 背景主题色预设（代码风格 - 使用代码高亮配色）
        # 颜色说明：bg=背景, fg=普通文字, accent=强调色(按钮等), 
        # 颜色说明：bg=背景, fg=普通文字, accent=强调色(按钮等), 
        #          keyword=关键字蓝, string=字符串橙, comment=注释绿
        #          style='normal' (正常UI) 或 'code' (代码风格)
        self.theme_presets = config.get("theme_presets", {})
        if "默认" not in self.theme_presets:
            self.theme_presets["默认"] = {
                "bg": "#F0F0F0",
                "fg": "#000000",
                "entry_bg": "#FFFFFF",
                "accent": "#0078D4",
                "keyword": "#0000FF",
                "string": "#A31515",
                "comment": "#008000",
                "style": "normal",
            }

        self.current_theme = tk.StringVar(value="VS Code Dark")  # 默认深色主题
        
        # 字体预设（用于浏览器CSS注入）
        self.font_presets = config.get("font_presets", {})
        if "VS Code 默认" not in self.font_presets:
            self.font_presets["VS Code 默认"] = "Consolas, 'Courier New', monospace"
        self.current_font = tk.StringVar(value="VS Code 默认")
        self.current_font.trace_add("write", lambda *args: self.apply_theme())
        
        # 尝试注册本地字体文件 (如果用户把 ttf 放在了程序目录下的 fonts 文件夹)
        self._scan_and_register_local_fonts()
        
        # 常用网站配置
        self.websites = [tuple(item) for item in config.get("websites", [])]
        if not self.websites:
            self.websites = [("GitHub", "https://github.com")]
        
        # 代码字体
        self.code_font = ('Consolas', 10)
        self.code_font_bold = ('Consolas', 10, 'bold')

        # 创建界面组件
        self.create_widgets()
        
        # 应用默认主题（代码风格）
        self.apply_theme()
        
        # 初始化键盘监听
        self.init_keyboard_listener()
        # 启动工作倒计时
        self.update_work_timer()

        # 初次启动时，按内容智能撑开窗口，避免右侧控件被裁切
        self.root.after(50, self._ensure_window_fits_content)

        # 如果用户默认开启了光标信息，启动刷新
        if self.cursor_info_enabled.get():
            self.toggle_cursor_info()

    def _register_font_resource(self, font_path):
        """在 Windows 上注册字体文件，使当前进程可用"""
        try:
            if not os.path.exists(font_path): return False
            FR_PRIVATE = 0x10
            # 使用 AddFontResourceExW 注册
            res = ctypes.windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
            if res > 0:
                # 广播字体更改消息 (有些控件可能需要刷新)
                ctypes.windll.user32.PostMessageW(0xFFFF, 0x001D, 0, 0)
                return True
        except Exception as e:
            print(f"Font registration failed: {e}")
        return False

    def _scan_and_register_local_fonts(self):
        """扫描程序根目录或 fonts 文件夹下的 ttf/otf 并注册"""
        base_dir = app_root()
        font_dirs = [base_dir, os.path.join(base_dir, "fonts")]
        package_dir = os.path.dirname(os.path.abspath(__file__))
        if package_dir not in font_dirs:
            font_dirs.extend([package_dir, os.path.join(package_dir, "fonts")])
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            if exe_dir not in font_dirs:
                font_dirs.extend([exe_dir, os.path.join(exe_dir, "fonts")])
        
        for d in font_dirs:
            if not os.path.exists(d): continue
            for f in os.listdir(d):
                if f.lower().endswith(('.ttf', '.otf')):
                    fpath = os.path.join(d, f)
                    if self._register_font_resource(fpath):
                        print(f"Registered local font: {f}")

    def _update_check_label(self, lbl):
        """更新复选框标签文本"""
        is_code = getattr(lbl, 'is_code_style', True)
        if is_code:
            icon = "[x]" if lbl.variable.get() else "[ ]"
            lbl.config(text=f"{icon} {lbl.code_text}")
        else:
            # 正常模式使用 Unicode 复选框图标
            icon = "☑" if lbl.variable.get() else "☐"
            lbl.config(text=f"{icon} {lbl.normal_text}")

    def create_code_label(self, parent, code_text, normal_text=None, code_type="comment", **grid_args):
        text = code_text # 默认
        lbl = tk.Label(parent, text=text)
        lbl.code_type = code_type
        lbl.code_text = code_text
        lbl.normal_text = normal_text if normal_text else code_text.replace("=", ":").replace("#", "").strip()
        lbl.grid(**grid_args)
        return lbl

    def create_code_entry(self, parent, variable, width=10, **grid_args):
        entry = tk.Entry(parent, textvariable=variable, width=width,
                        bd=0, highlightthickness=0, relief='flat')
        entry.code_type = 'entry'
        entry.grid(**grid_args)
        
        # 保存 grid 参数以便 normal 模式下使用
        entry.grid_args = grid_args
        
        # 添加底部下划线模拟 (仅代码模式)
        if 'row' in grid_args and 'column' in grid_args:
            underline = tk.Frame(parent, height=1)
            underline.code_type = 'underline'
            underline.grid(row=grid_args['row'], column=grid_args['column'], 
                         sticky='swe', padx=grid_args.get('padx', 0))
            entry.underline_widget = underline
        return entry

    def create_code_button(self, parent, code_text, normal_text, command, width=None, **grid_args):
        btn = tk.Label(parent, text=f"[{code_text}]", cursor="hand2")
        btn.code_type = 'button'
        btn.code_text = code_text
        btn.normal_text = normal_text
        btn.bind("<Button-1>", lambda e: command())
        if width: btn.config(width=width)
        btn.grid(**grid_args)
        return btn
        
    def create_code_check(self, parent, code_text, normal_text, variable, command=None, **grid_args):
        lbl = tk.Label(parent, cursor="hand2")
        lbl.code_type = 'checkbox'
        lbl.code_text = code_text
        lbl.normal_text = normal_text
        lbl.variable = variable
        lbl.command = command
        lbl.is_code_style = True # 默认状态
        
        def toggle(e):
            variable.set(not variable.get())
            self._update_check_label(lbl)
            if command: command()
            
        lbl.bind("<Button-1>", toggle)
        lbl.grid(**grid_args)
        self._update_check_label(lbl)
        return lbl
        
    def create_menu_button(self, parent, variable, options, command=None, width=15, **grid_args):
        """模拟下拉菜单"""
        frame = tk.Frame(parent)
        frame.code_type = 'menubutton'
        frame.grid(**grid_args)
        
        lbl = tk.Label(frame, text=variable.get(), cursor="hand2", width=width, anchor="w")
        lbl.code_type = 'string'
        lbl.pack(side="left", fill="x", expand=True)
        
        arrow = tk.Label(frame, text="▼", cursor="hand2")
        arrow.code_type = 'keyword'
        arrow.pack(side="right")
        
        menu = tk.Menu(frame, tearoff=0)
        
        def update_label(*args):
             lbl.config(text=variable.get())
             
        variable.trace_add("write", update_label)
        
        def show_menu(e):
            menu.delete(0, tk.END)
            for opt in options:
                menu.add_command(label=opt, command=lambda v=opt: [variable.set(v), command(v) if command else None])
            menu.post(e.x_root, e.y_root)
            
        lbl.bind("<Button-1>", show_menu)
        arrow.bind("<Button-1>", show_menu)
        
        # Store for referencing
        frame.lbl = lbl
        frame.arrow = arrow
        return frame

    def create_section(self, parent, code_title, normal_title, row=None):
        """创建可折叠的代码块区域 (使用 pack 布局)"""
        # Container
        container = tk.Frame(parent)
        container.code_type = 'bg'
        # 使用 pack 替代 grid，避免布局冲突，且无需手动管理 row
        container.pack(fill="x", pady=2, anchor="n")
        
        # Header
        header = tk.Frame(container)
        header.code_type = 'bg'
        header.pack(fill="x", anchor="w")
        
        # Content
        content = tk.Frame(container)
        content.code_type = 'bg'
        content.pack(fill="x", padx=20, anchor="w")
        
        # State
        is_expanded = tk.BooleanVar(value=True)
        
        # Icon Label
        icon_lbl = tk.Label(header, cursor="hand2", width=3)
        icon_lbl.code_type = 'fold_icon'
        icon_lbl.is_expanded = is_expanded
        icon_lbl.pack(side="left")
        
        # Title
        title_lbl = tk.Label(header, text=code_title, cursor="hand2")
        title_lbl.code_type = 'comment'
        title_lbl.code_text = code_title
        title_lbl.normal_text = normal_title
        title_lbl.pack(side="left")
        
        def toggle(e=None):
            if is_expanded.get():
                content.pack_forget()
                is_expanded.set(False)
            else:
                content.pack(fill="x", padx=20, anchor="w")
                is_expanded.set(True)
            self._update_section_icon(icon_lbl)
            
        icon_lbl.bind("<Button-1>", toggle)
        title_lbl.bind("<Button-1>", toggle)
        
        self._update_section_icon(icon_lbl)
        return content

    def _update_section_icon(self, lbl):
        """更新折叠图标样式"""
        if not hasattr(lbl, 'is_expanded'): return
        
        theme_name = self.current_theme.get()
        style = self.theme_presets.get(theme_name, {}).get("style", "code")
        expanded = lbl.is_expanded.get()
        
        if style == "code":
            txt = " [-] " if expanded else " [+] "
        else:
            txt = "▼" if expanded else "▶"
        lbl.config(text=txt)

    def create_widgets(self):
        # 使用 Frame 替代 LabelFrame
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)
        self.main_container.code_type = 'bg'
        
        current_row = 0 # Deprecated but kept for compatibility with inner grids
        
        # ====== 1. Work Time ======
        time_content = self.create_section(self.main_container, "# 工作时间设置", "【工作时间设置】")
        current_row += 1
        
        time_frame = tk.Frame(time_content)
        time_frame.code_type = 'bg'
        time_frame.pack(fill="x", pady=5)
        
        self.create_code_label(time_frame, "start_time =", "上班时间:", "fg", row=0, column=0)
        self.work_start_var_input = tk.StringVar(value="09:00")
        self.work_start_input = self.create_code_entry(time_frame, self.work_start_var_input, width=6, row=0, column=1, padx=5)

        self.create_code_label(time_frame, "end_time =", "下班时间:", "fg", row=0, column=2, padx=(15, 0))
        self.work_end_var_input = tk.StringVar(value="18:00")
        self.work_end_input = self.create_code_entry(time_frame, self.work_end_var_input, width=6, row=0, column=3, padx=5)
        
        self.work_start_var = tk.StringVar(value="今日上班: --:--")
        self.work_end_var = tk.StringVar(value="距离下班: --:--")
        
        status_frame = tk.Frame(time_content)
        status_frame.code_type = 'bg'
        status_frame.pack(fill="x", pady=(0, 5))
        
        sl1 = tk.Label(status_frame, textvariable=self.work_start_var)
        sl1.grid(row=0, column=0, sticky="w")
        self.status_label1 = sl1
        self.status_label1.code_type = "comment"
        self.status_label1.code_text = ""
        
        sl2 = tk.Label(status_frame, textvariable=self.work_end_var)
        sl2.grid(row=0, column=1, padx=20, sticky="w")
        self.status_label2 = sl2
        self.status_label2.code_type = "string"
        
        # ====== 2. Stealth ======
        stealth_content = self.create_section(self.main_container, "# 隐蔽模式配置", "【隐蔽模式配置】")
        current_row += 1
        
        stealth_frame = tk.Frame(stealth_content)
        stealth_frame.code_type = 'bg'
        stealth_frame.pack(fill="x", pady=5)
        
        self.create_code_label(stealth_frame, "window_opacity =", "透明度:", "fg", row=0, column=0)
        self.opacity_scale = tk.Scale(stealth_frame, from_=30, to=100, variable=self.opacity_var,
                                     orient="horizontal", length=100, bd=0, highlightthickness=0, showvalue=0)
        self.opacity_scale.code_type = 'scale'
        self.opacity_scale.configure(command=self.update_opacity)
        self.opacity_scale.grid(row=0, column=1, padx=5)
        
        self.opacity_label = self.create_code_label(stealth_frame, "100%", "100%", "string", row=0, column=2)
        
        self.topmost_check = self.create_code_check(stealth_frame, "always_on_top", "窗口置顶", self.topmost_var, self.toggle_topmost, row=0, column=3, padx=15)
        self.borderless_check = self.create_code_check(stealth_frame, "borderless", "无边框", self.borderless_var, self.toggle_borderless, row=0, column=4, padx=5)
        
        self.create_code_label(stealth_frame, "window_title =", "伪装标题:", "fg", row=1, column=0, pady=5)
        self.create_menu_button(stealth_frame, self.current_title, self.title_presets, self.change_title, row=1, column=1, columnspan=2, sticky="ew")
        
        self.create_code_label(stealth_frame, "ui_theme =", "主题风格:", "fg", row=2, column=0, pady=5)
        self.create_menu_button(stealth_frame, self.current_theme, list(self.theme_presets.keys()), self.apply_theme, row=2, column=1, columnspan=2, sticky="ew")
        
        self.create_code_label(stealth_frame, "code_font =", "代码字体:", "fg", row=3, column=0, pady=5)
        self.create_menu_button(stealth_frame, self.current_font, list(self.font_presets.keys()), None, row=3, column=1, columnspan=2, sticky="ew")
        
        # ====== 3. Mouse Mover ======
        self.build_mouse_section(self.main_container)
        current_row += 1

        # ====== 3b. Cursor Info ======
        self.build_cursor_section(self.main_container)
        current_row += 1

        # ====== 4. Salary ======
        self.build_salary_section(self.main_container)
        current_row += 1

        # ====== 5. Web Shortcuts ======
        self.build_browser_section(self.main_container)
        current_row += 1

        # Apply theme
        self.apply_theme()


    def update_opacity(self, val):
        opacity = float(val) / 100
        self.root.attributes('-alpha', opacity)
        self.opacity_label.config(text=f"{int(float(val))}%")
    
    def toggle_topmost(self):
        self._update_check_label(self.topmost_check)
        self.root.attributes('-topmost', self.topmost_var.get())
        
    def toggle_borderless(self):
        self._update_check_label(self.borderless_check)
        if self.borderless_var.get():
            # 记录切换前的尺寸/最小尺寸，退出无边框时可恢复
            try:
                self._borderless_prev_geometry = self.root.geometry()
                self._borderless_prev_minsize = self.root.minsize()
            except Exception:
                self._borderless_prev_geometry = None
                self._borderless_prev_minsize = None

            self.root.overrideredirect(True)
            # 先按内容撑开，再做无边框安全边距兜底
            self._ensure_window_fits_content(force=True)
            self._ensure_borderless_geometry()
            self._create_resize_grip()

            # 使用 bind_all 并在 handler 里过滤
            self._drag_enabled = True
            self.root.bind('<Button-1>', self._start_drag)
            self.root.bind('<B1-Motion>', self._do_drag)
        else:
            self.root.overrideredirect(False)
            self._drag_enabled = False
            self.root.unbind('<Button-1>')
            self.root.unbind('<B1-Motion>')

            self._destroy_resize_grip()
            self._restore_borderless_geometry()

    def _ensure_borderless_geometry(self):
        """无边框模式下，按内容所需尺寸自动撑开，避免控件被裁切。"""
        try:
            self.root.update_idletasks()

            # 当前尺寸
            cur_w = self.root.winfo_width()
            cur_h = self.root.winfo_height()
            if cur_w <= 1 or cur_h <= 1:
                # 若窗口尚未稳定，使用 geometry 解析兜底
                geo = self.root.geometry()
                size_part = geo.split('+', 1)[0]
                if 'x' in size_part:
                    cur_w, cur_h = (int(x) for x in size_part.split('x', 1))

            # 内容所需尺寸（requested size）
            # 优先用主容器计算（更贴近实际布局）
            if hasattr(self, 'main_container'):
                req_w = self.main_container.winfo_reqwidth()
                req_h = self.main_container.winfo_reqheight()
            else:
                req_w = self.root.winfo_reqwidth()
                req_h = self.root.winfo_reqheight()

            # Windows 无边框偶发裁切：加一点“安全边距”
            margin_w = 40
            margin_h = 20
            target_w = max(cur_w, req_w + margin_w)
            target_h = max(cur_h, req_h + margin_h)

            # 最小尺寸至少满足内容
            self.root.minsize(req_w, req_h)

            x = self.root.winfo_x()
            y = self.root.winfo_y()
            self.root.geometry(f"{target_w}x{target_h}+{x}+{y}")
        except Exception:
            # 不让 UI 因尺寸测量失败而崩溃
            return

    def _ensure_window_fits_content(self, force=False):
        """普通窗口也按内容智能撑开，确保右侧控件（如 borderless）可见。"""
        try:
            self.root.update_idletasks()

            # 以主容器为准（它包含所有 section）
            if not hasattr(self, 'main_container'):
                return

            req_w = self.main_container.winfo_reqwidth()
            req_h = self.main_container.winfo_reqheight()

            # 考虑 main_container pack 的 padx=20*2 和额外边距
            margin_w = 80
            margin_h = 40
            desired_w = int(req_w + margin_w)
            desired_h = int(req_h + margin_h)

            cur_w = self.root.winfo_width()
            cur_h = self.root.winfo_height()

            # 更新最小尺寸：不影响用户拉大，只防止过窄导致裁切
            try:
                min_w, min_h = self.root.minsize()
            except Exception:
                min_w, min_h = (0, 0)
            self.root.minsize(max(int(min_w), desired_w), max(int(min_h), desired_h))

            if force or cur_w < desired_w or cur_h < desired_h:
                x = self.root.winfo_x()
                y = self.root.winfo_y()
                new_w = max(int(cur_w), desired_w)
                new_h = max(int(cur_h), desired_h)
                self.root.geometry(f"{new_w}x{new_h}+{x}+{y}")
        except Exception:
            return

    def _restore_borderless_geometry(self):
        """退出无边框后恢复之前的尺寸/最小尺寸。"""
        try:
            if self._borderless_prev_minsize and isinstance(self._borderless_prev_minsize, tuple):
                self.root.minsize(*self._borderless_prev_minsize)
        except Exception:
            pass
        try:
            if self._borderless_prev_geometry:
                self.root.geometry(self._borderless_prev_geometry)
        except Exception:
            pass

    def _create_resize_grip(self):
        """无边框模式下提供右下角拉伸手柄，保持用户可拉伸窗口。"""
        if self._resize_grip is not None:
            return

        grip = tk.Label(self.root, text="◢", cursor="size_nw_se")
        grip.code_type = 'resize_grip'
        grip.is_resize_grip = True

        # 右下角悬浮，不干扰现有 pack/grid
        grip.place(relx=1.0, rely=1.0, anchor='se', x=-2, y=-2)

        grip.bind('<Button-1>', self._start_resize)
        grip.bind('<B1-Motion>', self._do_resize)
        grip.bind('<ButtonRelease-1>', self._end_resize)

        self._resize_grip = grip
        # 切换主题后保证可见
        try:
            self.apply_theme()
        except Exception:
            pass

    def _destroy_resize_grip(self):
        if self._resize_grip is None:
            return
        try:
            self._resize_grip.destroy()
        except Exception:
            pass
        self._resize_grip = None
        self._resize_active = False
        self._resize_start = None

    def _start_resize(self, event):
        try:
            self._resize_active = True
            self._resize_start = {
                'x': event.x_root,
                'y': event.y_root,
                'w': self.root.winfo_width(),
                'h': self.root.winfo_height(),
            }
        except Exception:
            self._resize_active = False
            self._resize_start = None

    def _do_resize(self, event):
        if not self._resize_active or not self._resize_start:
            return
        try:
            dx = event.x_root - self._resize_start['x']
            dy = event.y_root - self._resize_start['y']

            min_w, min_h = self.root.minsize()
            new_w = max(int(self._resize_start['w'] + dx), int(min_w))
            new_h = max(int(self._resize_start['h'] + dy), int(min_h))

            x = self.root.winfo_x()
            y = self.root.winfo_y()
            self.root.geometry(f"{new_w}x{new_h}+{x}+{y}")
        except Exception:
            return

    def _end_resize(self, event):
        self._resize_active = False
        self._resize_start = None

    def _start_drag(self, event):
        # 排除交互控件（Scale, Entry, Label with cursor=hand2 等）
        widget = event.widget
        self._drag_active = False

        # 无边框拉伸手柄：不触发拖动
        if getattr(widget, 'is_resize_grip', False):
            return
        
        if isinstance(widget, (tk.Scale, tk.Entry, tk.Button, tk.Checkbutton)):
            return
            
        # 检查是否是可点击的标签（按钮/复选框）
        if isinstance(widget, tk.Label):
            cursor = str(widget.cget('cursor'))
            if cursor == 'hand2':
                return  # 这是可点击的按钮，不拖动
                
        self._drag_active = True
        self._drag_x = event.x_root
        self._drag_y = event.y_root
        self._initial_x = self.root.winfo_x()
        self._initial_y = self.root.winfo_y()
    
    def _do_drag(self, event):
        if not getattr(self, '_drag_active', False):
            return
            
        dx = event.x_root - self._drag_x
        dy = event.y_root - self._drag_y
        x = self._initial_x + dx
        y = self._initial_y + dy
        self.root.geometry(f"+{x}+{y}")
    
    def show_custom_message(self, title, message):
        """显示自定义暗色弹窗"""
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("300x150")
        dlg.resizable(False, False)
        
        # 获取当前主题颜色
        theme_name = self.current_theme.get()
        theme = self.theme_presets.get(theme_name, self.theme_presets["默认"])
        bg = theme["bg"]
        fg = theme["fg"]
        accent = theme.get("accent", "#569CD6")
        
        dlg.configure(bg=bg)
        
        # 居中显示
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        dlg.geometry(f"+{x}+{y}")
        
        # 内容
        msg_label = tk.Label(dlg, text=message, bg=bg, fg=fg, 
                           font=self.code_font if theme.get("style")=="code" else ("Microsoft YaHei UI", 9),
                           wraplength=260)
        msg_label.pack(expand=True, pady=20)
        
        # 按钮
        btn = tk.Button(dlg, text="确定", command=dlg.destroy,
                       bg="#333333" if bg=="#1E1E1E" else "#E1E1E1",
                       fg=fg, relief="flat" if theme.get("style")=="code" else "raised",
                       activebackground=accent, activeforeground="#FFFFFF")
        btn.pack(pady=10)
        
        # 模态
        dlg.transient(self.root)
        dlg.grab_set()
        self.root.wait_window(dlg)

    def change_title(self, new_title=None):
        if not new_title:
             new_title = self.current_title.get()
        self.root.title(new_title)
    
    def apply_theme(self, event=None):
        """应用主题（支持正常/代码双模式）并更新字体"""
        # 更新代码模式下的字体
        try:
            font_full = self.font_presets.get(self.current_font.get(), "Consolas")
            # 提取第一个字体族名称用于 Tkinter (去引号)
            primary_font = font_full.split(',')[0].strip().strip("'").strip('"')
            self.code_font = (primary_font, 10)
            self.code_font_bold = (primary_font, 10, 'bold')
        except Exception:
            self.code_font = ('Consolas', 10)
            self.code_font_bold = ('Consolas', 10, 'bold')

        theme_name = self.current_theme.get()
        if theme_name in self.theme_presets:
            try:
                theme = self.theme_presets[theme_name]
                bg = theme["bg"]
                fg = theme["fg"]
                entry_bg = theme.get("entry_bg", bg)
                accent = theme.get("accent", "#569CD6")
                keyword = theme.get("keyword", "#569CD6")
                string_color = theme.get("string", "#CE9178")
                comment = theme.get("comment", "#6A9955")
                
                style_mode = theme.get("style", "code")
                self.current_style_mode = style_mode # save for checkbutton update
                
                self.root.configure(bg=bg)
                
                # 递归更新所有控件
                self._update_widget_colors(self.root, bg, fg, entry_bg, comment, keyword, string_color, accent, style_mode)

                # 主题切换可能改变字体/控件宽度，自动调一次窗口尺寸
                self.root.after(0, self._ensure_window_fits_content)
            except Exception as e:
                print(f"Theme error: {e}")

    def _update_widget_colors(self, parent, bg, fg, entry_bg, comment, keyword, string_color, accent, style_mode):
        """递归更新所有控件颜色和样式"""
        is_normal = (style_mode == 'normal')
        
        # 字体设定
        font_main = ('Microsoft YaHei UI', 9) if is_normal else self.code_font
        font_bold = ('Microsoft YaHei UI', 9, 'bold') if is_normal else self.code_font_bold
        
        for widget in parent.winfo_children():
            try:
                ctype = getattr(widget, 'code_type', None)
                
                # 通用背景
                if ctype == 'bg' or isinstance(widget, tk.Frame) or isinstance(widget, tk.LabelFrame):
                    widget.configure(bg=bg, bd=0, highlightthickness=0)

                # 右下角拉伸手柄（无边框模式）
                elif ctype == 'resize_grip':
                    if is_normal:
                        widget.configure(bg=bg, fg=accent, font=font_bold)
                    else:
                        widget.configure(bg=bg, fg=keyword, font=font_bold)
                    
                # 1. 标签 (Label)
                elif ctype in ('comment', 'fg', 'keyword', 'string'):
                    # 文本切换
                    text_display = getattr(widget, 'normal_text', None) if is_normal else getattr(widget, 'code_text', None)
                    if text_display:
                        widget.config(text=text_display)
                    
                    # 样式切换
                    if is_normal:
                        widget.configure(bg=bg, fg=fg, font=font_main)
                    else:
                        # 代码模式保留特定高亮
                        c_fg = {'comment': comment, 'fg': fg, 'keyword': keyword, 'string': string_color}.get(ctype, fg)
                        c_font = font_bold if ctype == 'keyword' else font_main
                        widget.configure(bg=bg, fg=c_fg, font=c_font)

                # 1b. 数值标签 (Variable Label)
                elif ctype == 'string_val':
                     if is_normal:
                         widget.configure(bg=bg, fg=accent, font=font_bold)
                     else:
                         widget.configure(bg=bg, fg=string_color, font=font_main)

                # 2. 输入框 (Entry)
                elif ctype == 'entry':
                    # 样式切换
                    if is_normal:
                        widget.configure(background=entry_bg, foreground=fg, 
                                       insertbackground=fg, font=font_main,
                                       disabledbackground="#E1E1E1", disabledforeground="#888888",
                                       relief='sunken', bd=1) 
                    else:
                        widget.configure(background=entry_bg, foreground=string_color, 
                                       insertbackground=fg, font=font_main,
                                       disabledbackground=entry_bg, disabledforeground=comment,
                                       relief='flat', bd=0)
                    
                    # 下划线控制
                    underline = getattr(widget, 'underline_widget', None)
                    if underline:
                        if is_normal:
                            underline.grid_remove()
                        else:
                            # 确保下划线显示，位置可能需要 grid_args
                            args = getattr(widget, 'grid_args', {})
                            if args:
                                underline.grid()
                                underline.configure(bg=comment)

                # 3. 复选框 (Label模拟)
                elif ctype == 'checkbox':
                    widget.is_code_style = not is_normal
                    self._update_check_label(widget)
                    if is_normal:
                        widget.configure(bg=bg, fg=fg, font=font_main)
                    else:
                        widget.configure(bg=bg, fg=keyword, font=font_main)
                        
                # 4. 折叠图标
                elif ctype == 'fold_icon':
                     widget.configure(bg=bg, fg=keyword if not is_normal else fg, 
                                    font=font_main)
                     self._update_section_icon(widget)


                # 4. 按钮 (Label模拟)
                elif ctype == 'button':
                    # 文本
                    code_txt = getattr(widget, 'code_text', "")
                    norm_txt = getattr(widget, 'normal_text', code_txt)
                    
                    if is_normal:
                        widget.config(text=f" {norm_txt} ") # 正常模式不带方括号
                        widget.configure(bg="#E1E1E1" if bg=="#F0F0F0" else entry_bg, # 简易按钮背景
                                       fg=fg, font=font_main, relief='raised', bd=1)
                    else:
                        widget.config(text=f"[{code_txt}]")
                        widget.configure(bg=bg, fg=string_color, font=font_main, relief='flat', bd=0)

                # 5. 为了 Menu Button 特殊处理
                elif ctype == 'menubutton':
                    if is_normal:
                         # 正常模式下显示像个按钮/下拉框
                         widget.configure(bg=bg, bd=1, relief='raised', highlightthickness=0)
                    else:
                         widget.configure(bg=bg, bd=0, relief='flat')
                
                # 6. Scale
                elif ctype == 'scale':
                    widget.configure(bg=bg, troughcolor=entry_bg, activebackground=accent, highlightthickness=0, bd=0)
                    
                # 7. Underline
                elif ctype == 'underline':
                    pass # handled in entry
                
                # 递归
                if isinstance(widget, (tk.Frame, tk.LabelFrame, tk.Toplevel)):
                     self._update_widget_colors(widget, bg, fg, entry_bg, comment, keyword, string_color, accent, style_mode)
                     
            except tk.TclError:
                pass
    
    def parse_time_input(self, time_str, default_hour, default_minute):
        """解析 HH:MM 格式的时间字符串"""
        try:
            parts = time_str.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
        except (ValueError, IndexError):
            pass
        return default_hour, default_minute
    
    def calculate_work_time(self):
        now = datetime.datetime.now()
        
        # 从用户输入获取上下班时间
        start_h, start_m = self.parse_time_input(self.work_start_input.get(), 9, 0)
        end_h, end_m = self.parse_time_input(self.work_end_input.get(), 18, 0)
        
        work_start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        work_end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        
        if now > work_end:
            work_start += datetime.timedelta(days=1)
            work_end += datetime.timedelta(days=1)
        elif now < work_start:
            work_end = work_end
        return work_start, work_end

    def update_work_timer(self):
        start_time, end_time = self.calculate_work_time()
        now = datetime.datetime.now()
        self.work_start_var.set(start_time.strftime("%Y-%m-%d %H:%M"))
        if now < end_time:
            delta = end_time - now
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.work_end_var.set(f"{hours:02d}时{minutes:02d}分{seconds:02d}秒")
        else:
            self.work_end_var.set("已下班")
        self.calculate_earnings()
        self.root.after(1000, self.update_work_timer)

    def init_keyboard_listener(self):
        def on_press(key):
            # ESC 停止鼠标模拟
            if key == keyboard.Key.esc and self.is_running:
                self.stop_program()
            
            # 跟踪组合键
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.pressed_keys.add('ctrl')
            elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                self.pressed_keys.add('alt')
            elif hasattr(key, 'char') and key.char:
                # 老板键: Ctrl+Alt+H
                if key.char.lower() == 'h' and 'ctrl' in self.pressed_keys and 'alt' in self.pressed_keys:
                    self.root.after(0, self.toggle_hide)
                # F9 也可以作为老板键
            elif key == keyboard.Key.f9:
                self.root.after(0, self.toggle_hide)
        
        def on_release(key):
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.pressed_keys.discard('ctrl')
            elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                self.pressed_keys.discard('alt')
        
        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()
    
    def toggle_hide(self):
        """切换窗口显示/隐藏状态"""
        if self.is_hidden:
            self.show_window()
        else:
            self.hide_to_tray()
    
    def create_tray_icon_image(self):
        """创建系统托盘图标"""
        # 尝试加载 fish.ico，否则创建简单图标
        icon_path = resource_path("fish.ico")
        if os.path.exists(icon_path):
            try:
                return Image.open(icon_path)
            except:
                pass
        
        # 创建简单的鱼形图标
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # 画一个简单的鱼形
        draw.ellipse([10, 15, 50, 50], fill='#4FC3F7')  # 鱼身
        draw.polygon([(50, 32), (62, 20), (62, 44)], fill='#4FC3F7')  # 鱼尾
        draw.ellipse([15, 25, 22, 32], fill='white')  # 鱼眼
        draw.ellipse([17, 27, 20, 30], fill='black')  # 眷孔
        return image
    
    def hide_to_tray(self):
        """隐藏窗口到系统托盘"""
        if self.is_hidden:
            return
        
        self.is_hidden = True
        self.root.withdraw()  # 隐藏窗口
        
        # 创建系统托盘图标
        menu = pystray.Menu(
            pystray.MenuItem("🐟 显示窗口 (F9)", self.show_window_from_tray),
            pystray.MenuItem("❌ 退出", self.quit_from_tray)
        )
        
        self.tray_icon = pystray.Icon(
            "AutoFish",
            self.create_tray_icon_image(),
            "摸鱼助手 - 已隐藏 (F9 恢复)",
            menu
        )
        
        # 在后台线程中运行托盘图标
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_window_from_tray(self, icon=None, item=None):
        """从托盘恢复窗口（供菜单调用）"""
        self.root.after(0, self.show_window)
    
    def show_window(self):
        """显示窗口"""
        if not self.is_hidden:
            return
        
        self.is_hidden = False
        
        # 停止托盘图标
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        
        self.root.deiconify()  # 显示窗口
        self.root.lift()  # 置顶
        self.root.focus_force()  # 获取焦点
    
    def quit_from_tray(self, icon=None, item=None):
        """从托盘退出程序"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.cleanup_and_quit)

    def cleanup_and_quit(self):
        """清理资源并退出程序"""
        self.is_running = False
        self.stop_program()
        
        # 终止浏览器进程
        if getattr(self, 'browser_process', None):
            try:
                self.browser_process.terminate()
            except:
                pass
                
        if self.listener:
            self.listener.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()


def main():
    root = tk.Tk()

    # 应用主题美化
    style = ttk.Style()
    available_themes = style.theme_names()
    # 优先使用现代主题
    for theme in ['clam', 'alt', 'vista', 'xpnative']:
        if theme in available_themes:
            style.theme_use(theme)
            break

    # 自定义样式
    style.configure('TLabelframe', padding=5)
    style.configure('TLabelframe.Label', font=('Microsoft YaHei UI', 9, 'bold'))
    style.configure('TButton', padding=3)
    style.configure('TCheckbutton', padding=2)

    root.geometry("480x580")
    root.resizable(True, True)
    root.minsize(400, 500)

    app = MouseMoverApp(root)

    root.protocol("WM_DELETE_WINDOW", app.cleanup_and_quit)
    root.mainloop()


if __name__ == "__main__":
    main()

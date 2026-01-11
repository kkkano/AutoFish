import random
import threading
import time
import tkinter as tk
from tkinter import messagebox

import pyautogui


class MouseModule:
    def build_mouse_section(self, parent):
        mouse_content = self.create_section(parent, "# 鼠标自动运行配置", "【鼠标自动运行配置】")

        mouse_frame = tk.Frame(mouse_content)
        mouse_frame.code_type = 'bg'
        mouse_frame.pack(fill="x", pady=5)

        self.create_code_label(mouse_frame, "run_duration =", "运行时长:", "fg", row=0, column=0)
        self.hours = self.create_code_entry(mouse_frame, tk.StringVar(), width=3, row=0, column=1)
        self.create_code_label(mouse_frame, "h", "时", "comment", row=0, column=2)
        self.minutes = self.create_code_entry(mouse_frame, tk.StringVar(), width=3, row=0, column=3)
        self.create_code_label(mouse_frame, "m", "分", "comment", row=0, column=4)
        self.seconds = self.create_code_entry(mouse_frame, tk.StringVar(), width=3, row=0, column=5)
        self.create_code_label(mouse_frame, "s", "秒", "comment", row=0, column=6)

        self.create_code_label(mouse_frame, "interval_sec =", "移动间隔:", "fg", row=1, column=0, pady=5)
        self.interval = self.create_code_entry(
            mouse_frame,
            tk.StringVar(value="10"),
            width=5,
            row=1,
            column=1,
        )

        # 必须显式保存 start_btn 引用
        # 必须显式保存 start_btn 引用
        self.start_btn = self.create_code_button(
            mouse_frame,
            "RUN_SCRIPT",
            "开始运行",
            self.toggle_run,
            row=2,
            column=0,
            columnspan=3, # 缩短 columnspan
            pady=10,
        )

        # 紧急停止按钮 (Visible "Panic Button")
        self.stop_btn_ui = self.create_code_button(
             mouse_frame,
             "STOP",
             "停止 (ESC)",
             self.stop_program,
             row=2,
             column=3,
             columnspan=4,
             pady=10,
        )
        
        # 提示标签
        self.create_code_label(mouse_frame, "# Tip: Press ESC to stop", "提示: 鼠标失控请按 ESC", "comment", row=3, column=0, columnspan=7)

        # 倒计时显示
        self.time_left_var = tk.StringVar()
        self.timer_label = tk.Label(mouse_frame, textvariable=self.time_left_var)
        self.timer_label.code_type = 'comment'
        self.timer_label.grid(row=4, column=0, columnspan=7, pady=(0, 5))

        return mouse_content

    def build_cursor_section(self, parent):
        cursor_content = self.create_section(parent, "# 光标信息 (实时XY/RGB)", "【光标信息】")

        cursor_frame = tk.Frame(cursor_content)
        cursor_frame.code_type = 'bg'
        cursor_frame.pack(fill="x", pady=5)

        # 开关
        self.cursor_info_check = self.create_code_check(
            cursor_frame,
            "show_cursor_info",
            "显示光标信息",
            self.cursor_info_enabled,
            self.toggle_cursor_info,
            row=0,
            column=0,
            padx=(0, 10),
        )

        # 显示区域
        self.create_code_label(cursor_frame, "cursor_xy =", "坐标:", "fg", row=1, column=0, pady=4)
        xy_val = tk.Label(cursor_frame, textvariable=self.cursor_xy_var)
        xy_val.code_type = 'string_val'
        xy_val.grid(row=1, column=1, sticky="w", padx=5)

        self.create_code_label(cursor_frame, "cursor_rgb =", "颜色:", "fg", row=2, column=0, pady=4)
        rgb_val = tk.Label(cursor_frame, textvariable=self.cursor_rgb_var)
        rgb_val.code_type = 'string_val'
        rgb_val.grid(row=2, column=1, sticky="w", padx=5)

        self.create_code_label(cursor_frame, "cursor_hex =", "HEX:", "fg", row=3, column=0, pady=4)
        hex_val = tk.Label(cursor_frame, textvariable=self.cursor_hex_var)
        hex_val.code_type = 'string_val'
        hex_val.grid(row=3, column=1, sticky="w", padx=5)

        # 色块（跟随当前像素颜色）
        swatch = tk.Frame(cursor_frame, width=26, height=16, bg="#000000")
        swatch.code_type = 'bg'
        swatch.grid(row=1, column=2, rowspan=3, sticky="w", padx=(10, 0))
        swatch.grid_propagate(False)
        self._cursor_color_swatch = swatch

        return cursor_content

    def toggle_cursor_info(self):
        """切换光标信息实时显示"""
        # 若有 UI 复选框（Label模拟），刷新其文本
        try:
            if hasattr(self, 'cursor_info_check'):
                self._update_check_label(self.cursor_info_check)
        except Exception:
            pass

        # 关闭：取消after
        if not self.cursor_info_enabled.get():
            try:
                if self._cursor_info_after_id is not None:
                    self.root.after_cancel(self._cursor_info_after_id)
            except Exception:
                pass
            self._cursor_info_after_id = None
            return

        # 开启：立即刷新一次
        self._cursor_info_loop()

    def _cursor_info_loop(self):
        """循环刷新光标信息（不要直接调用，使用 toggle_cursor_info 开关）"""
        if not self.cursor_info_enabled.get():
            self._cursor_info_after_id = None
            return

        try:
            pos = pyautogui.position()
            x, y = int(pos.x), int(pos.y)
            self.cursor_xy_var.set(f"XY: {x}, {y}")

            # 获取像素颜色
            try:
                r, g, b = pyautogui.pixel(x, y)
                self.cursor_rgb_var.set(f"RGB: {r}, {g}, {b}")
                hex_color = f"#{r:02X}{g:02X}{b:02X}"
                self.cursor_hex_var.set(f"HEX: {hex_color}")
                if self._cursor_color_swatch is not None:
                    self._cursor_color_swatch.configure(bg=hex_color)
            except Exception:
                self.cursor_rgb_var.set("RGB: --")
                self.cursor_hex_var.set("HEX: --")
        except Exception:
            # 采样失败不影响主程序
            pass

        # 刷新频率：150ms
        try:
            self._cursor_info_after_id = self.root.after(150, self._cursor_info_loop)
        except Exception:
            self._cursor_info_after_id = None

    def toggle_run(self):
        if not self.is_running:
            if self.validate_input():
                self.start_program()
        else:
            self.stop_program()

    def stop_program(self):
        self.is_running = False
        self.exit_event.set()
        self.start_btn.config(text="开始运行")
        for entry in [self.hours, self.minutes, self.seconds, self.interval]:
            entry.config(state="normal")
        # self.show_custom_message("程序已停止", "鼠标模拟运行已终止")

    def validate_input(self):
        try:
            h = int(self.hours.get() or 0)
            m = int(self.minutes.get() or 0)
            s = int(self.seconds.get() or 0)
            if any(n < 0 for n in (h, m, s)):
                raise ValueError("时间不能为负数")
            self.total_seconds = h * 3600 + m * 60 + s
            if self.total_seconds <= 0:
                raise ValueError("总时间必须大于0")
            interval = int(self.interval.get())
            if interval <= 0:
                raise ValueError("移动间隔必须大于0")
            return True
        except ValueError as e:
            messagebox.showerror("输入错误", f"无效输入: {str(e)}")
            self.interval.delete(0, tk.END)
            self.interval.insert(0, "10")
            return False

    def start_program(self):
        self.is_running = True
        self.start_btn.config(text="停止运行")
        self.exit_event.clear()
        self.start_time = time.time()
        for entry in [self.hours, self.minutes, self.seconds, self.interval]:
            entry.config(state="disabled")
        threading.Thread(target=self.mouse_movement_thread, daemon=True).start()
        self.update_timer()

    def mouse_movement_thread(self):
        screen_width, screen_height = pyautogui.size()
        safe_margin = 100
        interval = int(self.interval.get())
        while not self.exit_event.is_set() and (time.time() - self.start_time < self.total_seconds):
            target_x = random.randint(safe_margin, screen_width - safe_margin)
            target_y = random.randint(safe_margin, screen_height - safe_margin)
            pyautogui.moveTo(
                target_x,
                target_y,
                duration=1,
                tween=pyautogui.easeInOutQuad,
            )
            # 使用百分比波动，避免小间隔时产生负数
            # 间隔范围：50% ~ 150%，最小 0.5 秒
            min_sleep = max(interval * 0.5, 0.5)
            max_sleep = interval * 1.5
            time.sleep(random.uniform(min_sleep, max_sleep))

    def update_timer(self):
        if self.is_running:
            elapsed = time.time() - self.start_time
            remaining = max(self.total_seconds - elapsed, 0)
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            self.time_left_var.set(f"剩余时间: {hours:02d}:{minutes:02d}:{seconds:02d}")
            if remaining <= 0:
                self.stop_program()
                messagebox.showinfo("运行完成", "鼠标模拟运行已完成！")
            else:
                self.root.after(1000, self.update_timer)
        else:
            self.time_left_var.set("剩余时间: 00:00:00")

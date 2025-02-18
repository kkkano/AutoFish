# pip install pyautogui pynput
import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
import random
import time
import threading
import datetime
from pynput import keyboard

class MouseMoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能办公助手(自用摸鱼神器)")
        
        # 初始化变量
        self.is_running = False
        self.exit_event = threading.Event()
        self.listener = None
        self.start_time = None
        self.total_seconds = 0
        self.salary_enabled = tk.BooleanVar(value=False)
        self.monthly_salary = tk.DoubleVar()
        self.work_days = tk.IntVar()
        self.earnings_var = tk.StringVar(value="当前收入: 0.00 元")

        # 创建界面组件
        self.create_widgets()
        
        # 初始化键盘监听
        self.init_keyboard_listener()
        # 启动工作倒计时
        self.update_work_timer()

    def create_widgets(self):
        # ====== 第一部分：工作时间倒计时 ======
        work_time_frame = ttk.LabelFrame(self.root, text="工作时间倒计时")
        work_time_frame.pack(padx=10, pady=5, fill="x")
        
        self.work_start_var = tk.StringVar()
        ttk.Label(work_time_frame, text="上班时间:").grid(row=0, column=0, padx=5)
        ttk.Label(work_time_frame, textvariable=self.work_start_var).grid(row=0, column=1)
        
        self.work_end_var = tk.StringVar()
        ttk.Label(work_time_frame, text="距离下班:").grid(row=1, column=0, padx=5)
        ttk.Label(work_time_frame, textvariable=self.work_end_var, font=('Arial', 12, 'bold')).grid(row=1, column=1)

        # ====== 第二部分：鼠标模拟设置 ======
        mouse_frame = ttk.LabelFrame(self.root, text="鼠标模拟设置")
        mouse_frame.pack(padx=10, pady=5, fill="x")
        
        ttk.Label(mouse_frame, text="运行时长:").grid(row=0, column=0)
        self.hours = ttk.Entry(mouse_frame, width=3)
        self.hours.grid(row=0, column=1, padx=2)
        ttk.Label(mouse_frame, text="时").grid(row=0, column=2)
        
        self.minutes = ttk.Entry(mouse_frame, width=3)
        self.minutes.grid(row=0, column=3, padx=2)
        ttk.Label(mouse_frame, text="分").grid(row=0, column=4)
        
        self.seconds = ttk.Entry(mouse_frame, width=3)
        self.seconds.grid(row=0, column=5, padx=2)
        ttk.Label(mouse_frame, text="秒").grid(row=0, column=6)
        
        ttk.Label(mouse_frame, text="移动间隔:").grid(row=1, column=0, pady=5)
        self.interval = ttk.Entry(mouse_frame, width=6)
        self.interval.insert(0, "10")
        self.interval.grid(row=1, column=1, columnspan=2)
        ttk.Label(mouse_frame, text="秒").grid(row=1, column=3)

        self.start_btn = ttk.Button(self.root, text="开始运行", command=self.toggle_run)
        self.start_btn.pack(pady=5)
        
        self.time_left_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.time_left_var, font=('Arial', 12)).pack(pady=5)

        # ====== 第三部分：薪资计算 ======
        salary_frame = ttk.LabelFrame(self.root, text="薪资计算")
        salary_frame.pack(padx=10, pady=5, fill="x")

        self.salary_check = ttk.Checkbutton(salary_frame, text="启用薪资计算", 
                                          variable=self.salary_enabled,
                                          command=self.toggle_salary_display)
        self.salary_check.grid(row=0, column=0, columnspan=2, pady=2)

        ttk.Label(salary_frame, text="月薪（元）:").grid(row=1, column=0, padx=5)
        self.salary_entry = ttk.Entry(salary_frame, textvariable=self.monthly_salary, width=10)
        self.salary_entry.grid(row=1, column=1, padx=5)

        ttk.Label(salary_frame, text="工作日/月:").grid(row=2, column=0, padx=5)
        self.days_entry = ttk.Entry(salary_frame, textvariable=self.work_days, width=10)
        self.days_entry.grid(row=2, column=1, padx=5)

        self.earnings_label = ttk.Label(salary_frame, textvariable=self.earnings_var, 
                                      font=('Arial', 10, 'bold'), foreground='#009900')
        self.earnings_label.grid(row=3, column=0, columnspan=2, pady=5)
        
        self.toggle_salary_display()

    def toggle_salary_display(self):
        if self.salary_enabled.get():
            for widget in [self.salary_entry, self.days_entry, self.earnings_label]:
                widget.grid()
        else:
            for widget in [self.salary_entry, self.days_entry, self.earnings_label]:
                widget.grid_remove()

    def calculate_earnings(self):
        if self.salary_enabled.get():
            try:
                start_time, end_time = self.calculate_work_time()
                now = datetime.datetime.now()
                
                if now < start_time:
                    worked_seconds = 0
                elif now > end_time:
                    worked_seconds = (end_time - start_time).total_seconds()
                else:
                    worked_seconds = (now - start_time).total_seconds()

                monthly = float(self.monthly_salary.get())
                days = int(self.work_days.get())
                daily_hours = 9  # 9:00-18:00
                
                if days <= 0 or monthly <= 0:
                    raise ValueError
                
                salary_per_second = monthly / (days * daily_hours * 3600)
                self.earnings_var.set(f"当前收入: {salary_per_second * worked_seconds:.2f} 元")
            except:
                self.earnings_var.set("无效输入")

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
        messagebox.showinfo("程序已停止", "鼠标模拟运行已终止")

    def calculate_work_time(self):
        now = datetime.datetime.now()
        work_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        work_end = now.replace(hour=18, minute=0, second=0, microsecond=0)
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

    def validate_input(self):
        try:
            h = int(self.hours.get() or 0)
            m = int(self.minutes.get() or 0)
            s = int(self.seconds.get() or 0)
            if any(n < 0 for n in (h, m, s)):
                raise ValueError("时间不能为负数")
            self.total_seconds = h*3600 + m*60 + s
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

    def init_keyboard_listener(self):
        def on_press(key):
            if key == keyboard.Key.esc and self.is_running:
                self.stop_program()
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()

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
        SAFE_MARGIN = 100
        interval = int(self.interval.get())
        while not self.exit_event.is_set() and (time.time() - self.start_time < self.total_seconds):
            target_x = random.randint(SAFE_MARGIN, screen_width - SAFE_MARGIN)
            target_y = random.randint(SAFE_MARGIN, screen_height - SAFE_MARGIN)
            pyautogui.moveTo(
                target_x, target_y,
                duration=1,
                tween=pyautogui.easeInOutQuad
            )
            time.sleep(random.uniform(interval-5, interval+5))

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

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("450x400")
    app = MouseMoverApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_program(), root.destroy()))
    root.mainloop()


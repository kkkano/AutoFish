import json
import os
import subprocess
import sys
import tkinter as tk

from ..utils import app_root


class BrowserModule:
    def build_browser_section(self, parent):
        web_content = self.create_section(parent, "# 快捷摸鱼 (Web)", "【快捷摸鱼 (Web)】")

        web_frame = tk.Frame(web_content)
        web_frame.code_type = 'bg'
        web_frame.pack(fill="x", pady=5)

        btn_frame = tk.Frame(web_frame)
        btn_frame.code_type = 'bg'
        btn_frame.grid(row=0, column=0, columnspan=4, sticky="w")

        for i, (name, url) in enumerate(self.websites):
            self.create_code_button(btn_frame, name, name, lambda u=url: self.open_web(u), row=0, column=i, padx=4)

        self.create_code_label(web_frame, "custom_url =", "自定义URL:", "fg", row=1, column=0, pady=5)
        self.custom_url = self.create_code_entry(
            web_frame,
            tk.StringVar(value="https://"),
            width=30,
            row=1,
            column=1,
            padx=5,
        )
        self.create_code_button(web_frame, "OPEN", "打开", lambda: self.open_web(self.custom_url.get()), row=1, column=2, padx=5)

        # 嵌入式浏览器控制器 (位于 Web Shortcuts 内容区底部)
        self.browser_control_frame = tk.Frame(web_content)  # Parent is web_content
        self.browser_control_frame.code_type = 'bg'
        self.browser_control_frame.pack(fill="x", pady=10)  # Use pack
        self.browser_control_frame.pack_forget()  # Default hidden

        # 初始应用主题
        self.apply_theme()

        return web_content

    def send_browser_command(self, action, **kwargs):
        """发送指令到浏览器内核"""
        if getattr(self, 'browser_process', None) and self.browser_process.poll() is None:
            try:
                cmd = {"action": action}
                cmd.update(kwargs)
                self.browser_process.stdin.write(json.dumps(cmd) + "\n")
                self.browser_process.stdin.flush()
            except Exception as e:
                print(f"Command failed: {e}")

    def _start_browser_process(self, url):
        title = "🐟 摸鱼浏览器"
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--browser-kernel", title, url]
            cwd = os.path.dirname(sys.executable)
        else:
            cmd = [sys.executable, "-m", "autofish.browser_kernel", title, url]
            cwd = app_root()

        self.browser_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            text=True,
            cwd=cwd,
            creationflags=creation_flags,
        )

    def open_web(self, url):
        """打开内嵌浏览器窗口（增强版：使用高性能WebView2内核，嵌入式控制）"""
        if not url or not url.strip():
            return

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # 如果已有浏览器运行，直接跳转
        if getattr(self, 'browser_process', None) and self.browser_process.poll() is None:
            self.send_browser_command('navigate', url=url)
            return

        # 启动浏览器内核进程
        try:
            self._start_browser_process(url)
        except Exception as e:
            self.show_custom_message("启动失败", f"无法启动浏览器内核: {e}")
            return

        # 显示并填充嵌入式控制器
        self.browser_control_frame.pack(fill="x", pady=10)
        for widget in self.browser_control_frame.winfo_children():
            widget.destroy()

        f = self.browser_control_frame

        # 1. Header
        self.create_code_label(f, "# 浏览器控制器 (WebView2)", "【浏览器正在运行】", "comment", row=0, column=0, columnspan=4, sticky="w")

        # 2. URL Bar
        self.create_code_label(f, "current_url =", "地址:", "fg", row=1, column=0)
        url_var = tk.StringVar(value=url)
        url_entry = self.create_code_entry(f, url_var, width=50, row=1, column=1, columnspan=2, sticky="ew")

        def navigate():
            u = url_var.get()
            if not u.startswith(('http://', 'https://')):
                u = 'https://' + u
            self.send_browser_command('navigate', url=u)

        self.create_code_button(f, "GO", "跳转", navigate, row=1, column=3, padx=5)
        url_entry.bind('<Return>', lambda e: navigate())

        # 3. Controls
        self.create_code_label(f, "title =", "标题:", "fg", row=2, column=0)
        title_var = tk.StringVar(value="🐟 摸鱼浏览器")
        self.create_code_entry(f, title_var, width=20, row=2, column=1, sticky="w")

        def update_title(*args):
            self.send_browser_command('set_title', title=title_var.get())

        title_var.trace_add("write", update_title)

        # Opacity
        op_frame = tk.Frame(f)
        op_frame.code_type = 'bg'
        op_frame.grid(row=2, column=2, sticky="w", padx=10)

        self.create_code_label(op_frame, "opacity =", "透明度:", "fg", row=0, column=0)

        def update_op(v):
            self.send_browser_command('set_opacity', value=float(v) / 100, current_title=title_var.get())

        scale = tk.Scale(
            op_frame,
            from_=30,
            to=100,
            orient="horizontal",
            length=80,
            bd=0,
            highlightthickness=0,
            showvalue=0,
            command=update_op,
        )
        scale.set(100)
        scale.code_type = 'scale'
        scale.grid(row=0, column=1)

        # Borderless for browser window
        browser_borderless_var = tk.BooleanVar(value=False)

        def toggle_browser_borderless():
            self.send_browser_command(
                'set_borderless',
                value=browser_borderless_var.get(),
                current_title=title_var.get(),
            )

        self.create_code_check(
            f,
            "frameless",
            "无边框",
            browser_borderless_var,
            toggle_browser_borderless,
            row=2,
            column=4,
            padx=5,
        )

        # Dark Mode Logic
        dark_var = tk.BooleanVar(value=False)

        def toggle_dark():
            if dark_var.get():
                # Generate CSS based on current theme
                theme_name = self.current_theme.get()
                theme = self.theme_presets.get(theme_name, self.theme_presets["默认"])
                bg = theme["bg"]
                fg = theme["fg"]
                entry_bg = theme.get("entry_bg", bg)
                accent = theme.get("accent", "#569CD6")
                keyword = theme.get("keyword", "#569CD6")
                string_color = theme.get("string", "#CE9178")
                comment = theme.get("comment", "#6A9955")

                # 获取用户选择的字体
                font_name = self.current_font.get()
                font_family = self.font_presets.get(font_name, "Consolas, 'Courier New', monospace")

                # 计算辅助色
                def lighten(hex_color, amount=0.1):
                    c = hex_color.lstrip('#')
                    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                    r = min(255, int(r + (255 - r) * amount))
                    g = min(255, int(g + (255 - g) * amount))
                    b = min(255, int(b + (255 - b) * amount))
                    return f"#{r:02x}{g:02x}{b:02x}"

                card_bg = lighten(bg, 0.08)
                hover_bg = lighten(bg, 0.15)
                border_color = lighten(bg, 0.25)
                muted_fg = lighten(bg, 0.5)

                js_code = f"""
                (function() {{
                    var styleId = 'autofish-dark-style';
                    if (document.getElementById(styleId)) return;
                    var style = document.createElement('style');
                    style.id = styleId;
                    style.innerHTML = `
                        * {{
                            font-family: {font_family} !important;
                            background-color: {bg} !important;
                            color: {fg} !important;
                        }}
                        body {{
                            background: {bg} !important;
                            color: {fg} !important;
                        }}
                        a {{
                            color: {accent} !important;
                        }}
                        h1, h2, h3, h4, h5, h6 {{
                            color: {keyword} !important;
                        }}
                        code, pre {{
                            background: {entry_bg} !important;
                            color: {string_color} !important;
                        }}
                        blockquote {{
                            color: {comment} !important;
                            border-left: 3px solid {comment} !important;
                        }}
                        input, textarea, select, button {{
                            background: {entry_bg} !important;
                            color: {fg} !important;
                            border: 1px solid {border_color} !important;
                        }}
                        button:hover {{
                            background: {hover_bg} !important;
                        }}
                        .card, .item, .box, .panel {{
                            background: {card_bg} !important;
                            border-color: {border_color} !important;
                        }}
                        .muted, .secondary, .gray {{
                            color: {muted_fg} !important;
                        }}
                        /* ===== 强制覆盖内联样式（保留一定灵活性） ===== */
                        [style*="background"]:not(img):not(svg) {{
                            background-color: {bg} !important;
                        }}
                    `;
                    document.head.appendChild(style);

                    // 额外处理：设置meta 主题色
                    var metaTheme = document.querySelector('meta[name="theme-color"]');
                    if (!metaTheme) {{
                        metaTheme = document.createElement('meta');
                        metaTheme.name = 'theme-color';
                        document.head.appendChild(metaTheme);
                    }}
                    metaTheme.content = '{bg}';
                }})();
                """
                self.send_browser_command('eval_js', code=js_code)
            else:
                self.send_browser_command('eval_js', code="var s=document.getElementById('autofish-dark-style'); if(s) s.remove();")

        self.create_code_check(f, "dark_mode(css)", "开启暗色", dark_var, toggle_dark, row=2, column=3)

        # 4. Close
        def close_browser():
            self.send_browser_command('quit')
            if getattr(self, 'browser_process', None):
                try:
                    self.browser_process.terminate()
                except Exception:
                    pass
                self.browser_process = None
            self.browser_control_frame.pack_forget()

        self.create_code_button(f, "close_browser()", "关闭浏览器", close_browser, row=3, column=0, columnspan=4, pady=10)

        # Apply theme to new widgets
        self.apply_theme()

        # Auto-inject dark mode if theme is dark
        if "Dark" in self.current_theme.get():
            dark_var.set(True)
            self.root.after(1500, toggle_dark)

import datetime
import tkinter as tk


class SalaryModule:
    def build_salary_section(self, parent):
        salary_content = self.create_section(parent, "# 薪资计算模块 (2026)", "【薪资计算 (2026)】")

        salary_frame = tk.Frame(salary_content)
        salary_frame.code_type = 'bg'
        salary_frame.pack(fill="x", pady=5)

        self.salary_check = self.create_code_check(
            salary_frame,
            "enable_calculator",
            "启用薪资计算",
            self.salary_enabled,
            self.toggle_salary_display,
            row=0,
            column=0,
        )
        self.detail_check = self.create_code_check(
            salary_frame,
            "show_details",
            "详细模式",
            self.detail_mode,
            self.toggle_detail_mode,
            row=0,
            column=1,
            padx=10,
        )

        # 基本薪资行
        self.salary_content = tk.Frame(salary_frame)
        self.salary_content.code_type = 'bg'
        self.salary_content.grid(row=1, column=0, columnspan=4, sticky="w", pady=5)

        self.create_code_label(self.salary_content, "base_salary =", "税前月薪:", "fg", row=0, column=0)
        self.salary_entry = self.create_code_entry(self.salary_content, self.monthly_salary, width=8, row=0, column=1)

        self.create_code_label(self.salary_content, "work_days =", "工作日:", "fg", row=0, column=2, padx=(10, 0))
        self.days_entry = self.create_code_entry(self.salary_content, self.work_days, width=4, row=0, column=3)

        # 结果显示行
        res_frame = tk.Frame(salary_frame)
        res_frame.code_type = 'bg'
        res_frame.grid(row=3, column=0, columnspan=6, sticky="w", pady=5)

        self.Net_label = self.create_code_label(res_frame, "Net:", "税后:", "keyword", row=0, column=0, sticky="e")
        self.earnings_label = self.create_code_label(
            res_frame,
            "Earned:",
            "当前收入:",
            "string",
            row=0,
            column=1,
            sticky="w",
            padx=(5, 0),
        )

        self.earnings_val_label = tk.Label(res_frame, textvariable=self.earnings_var)
        self.earnings_val_label.code_type = "string_val"
        self.earnings_val_label.grid(row=0, column=2, sticky="w", padx=5)

        # 详细模式 (五险一金配置)
        self.detail_frame = tk.Frame(salary_frame)
        self.detail_frame.code_type = 'bg'
        self.detail_frame.grid(row=2, column=0, columnspan=6, sticky="w", pady=5)

        # Header
        self.create_code_label(
            self.detail_frame,
            "# 五险一金 (比例% | 金额￥)",
            "五险一金配置",
            "comment",
            row=0,
            column=0,
            columnspan=6,
            sticky="w",
        )

        # 社保基数
        self.create_code_label(self.detail_frame, "social_base =", "社保基数:", "fg", row=1, column=0)
        self.base_entry = self.create_code_entry(self.detail_frame, self.social_base, width=8, row=1, column=1)

        # Setup sync logic
        self._setup_sync(self.rate_pension, self.val_pension)
        self._setup_sync(self.rate_medical, self.val_medical)
        self._setup_sync(self.rate_unemploy, self.val_unemploy)
        self._setup_sync(self.rate_housing, self.val_housing)

        # Helper to create pair row
        def create_pair(row, label_code, label_norm, rate_var, val_var):
            self.create_code_label(self.detail_frame, label_code, label_norm, "fg", row=row, column=0)
            self.create_code_entry(self.detail_frame, rate_var, width=4, row=row, column=1)  # Rate
            self.create_code_label(self.detail_frame, "% =", "% =", "fg", row=row, column=2)
            self.create_code_entry(self.detail_frame, val_var, width=6, row=row, column=3)  # Value

        create_pair(2, "pension =", "养老保险:", self.rate_pension, self.val_pension)
        create_pair(3, "medical =", "医疗保险:", self.rate_medical, self.val_medical)
        create_pair(4, "unemploy =", "失业保险:", self.rate_unemploy, self.val_unemploy)
        create_pair(5, "housing =", "公积金  :", self.rate_housing, self.val_housing)

        # 专项扣除
        self.create_code_label(self.detail_frame, "spec_deduct =", "专项扣除:", "fg", row=6, column=0)
        self.create_code_entry(self.detail_frame, self.custom_deduction, width=8, row=6, column=1)  # 直接输入金额
        self.create_code_label(
            self.detail_frame,
            "# (房租/老人/子女)",
            "(房租/老人...)",
            "comment",
            row=6,
            column=2,
            columnspan=2,
            sticky="w",
        )

        self.toggle_salary_display()

        return salary_content

    def toggle_salary_display(self):
        """切换薪资计算显示"""
        if self.salary_enabled.get():
            self.salary_content.grid()
            self.detail_check.grid()
            self.toggle_detail_mode()
        else:
            self.salary_content.grid_remove()
            self.detail_check.grid_remove()

    def toggle_detail_mode(self):
        """切换详细模式"""
        if self.detail_mode.get() and self.salary_enabled.get():
            self.detail_frame.grid()
        else:
            self.detail_frame.grid_remove()

    def _setup_sync(self, rate_var, val_var):
        """双向绑定比例和金额"""
        def on_rate(*args):
            if rate_var._syncing:
                return
            try:
                base = float(self.social_base.get())
                r = float(rate_var.get())
                val = base * r / 100
                val_var._syncing = True
                val_var.set(f"{val:.2f}")
                val_var._syncing = False
            except Exception:
                pass

        def on_val(*args):
            if val_var._syncing:
                return
            try:
                base = float(self.social_base.get())
                v = float(val_var.get())
                if base > 0:
                    rate = v / base * 100
                    rate_var._syncing = True
                    rate_var.set(f"{rate:.2f}")
                    rate_var._syncing = False
            except Exception:
                pass

        rate_var._syncing = False
        val_var._syncing = False
        rate_var.trace_add("write", on_rate)
        val_var.trace_add("write", on_val)

    def calculate_tax(self, taxable_income):
        """计算个人所得税（2026年标准，累进税率，简化为单月计算）"""
        # 2026年个税税率表（月度简化计算）
        brackets = [
            (3000, 0.03, 0),      # 0-3000: 3%
            (12000, 0.10, 210),   # 3000-12000: 10%
            (25000, 0.20, 1410),  # 12000-25000: 20%
            (35000, 0.25, 2660),  # 25000-35000: 25%
            (55000, 0.30, 4410),  # 35000-55000: 30%
            (80000, 0.35, 7160),  # 55000-80000: 35%
            (float('inf'), 0.45, 15160),  # 80000+: 45%
        ]

        for threshold, rate, quick_deduction in brackets:
            if taxable_income <= threshold:
                return max(taxable_income * rate - quick_deduction, 0)
        return 0

    def calculate_earnings(self):
        """计算实时摸鱼收入"""
        if self.salary_enabled.get():
            try:
                # 独立计算今日工作时间范围，避免使用 calculate_work_time 的自动跳天逻辑
                now = datetime.datetime.now()
                start_h, start_m = self.parse_time_input(self.work_start_input.get(), 9, 0)
                end_h, end_m = self.parse_time_input(self.work_end_input.get(), 18, 0)

                # 构建今日的开始和结束时间
                start_time = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                end_time = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

                # 如果当前时间小于开始时间，收入为0
                if now < start_time:
                    worked_seconds = 0
                # 如果当前时间大于结束时间，收入为全天（即下班了）
                elif now > end_time:
                    worked_seconds = (end_time - start_time).total_seconds()
                # 工作中
                else:
                    worked_seconds = (now - start_time).total_seconds()

                monthly = float(self.monthly_salary.get())
                days = int(self.work_days.get())

                if days <= 0 or monthly <= 0:
                    raise ValueError

                # 计算每日工作小时数
                start_h, start_m = self.parse_time_input(self.work_start_input.get(), 9, 0)
                end_h, end_m = self.parse_time_input(self.work_end_input.get(), 18, 0)
                daily_hours = (end_h + end_m / 60) - (start_h + start_m / 60)
                if daily_hours <= 0:
                    daily_hours = 8

                if self.detail_mode.get():
                    # 详细模式：计算五险一金和个税
                    pension = float(self.val_pension.get() or 0)
                    medical = float(self.val_medical.get() or 0)
                    unemploy = float(self.val_unemploy.get() or 0)
                    housing = float(self.val_housing.get() or 0)
                    spec_deduct = float(self.custom_deduction.get() or 0)

                    # 五险一金总额
                    social_deduction = pension + medical + unemploy + housing

                    # 应纳税所得额 = 月薪 - 五险一金 - 起征点(5000) - 专项附加扣除
                    taxable = monthly - social_deduction - 5000 - spec_deduct
                    tax = self.calculate_tax(max(taxable, 0))

                    # 税后月薪
                    net_monthly = monthly - social_deduction - tax

                    # 显示详细信息
                    self.net_salary_var.set(
                        f"税后: ￥{net_monthly:.0f} | "
                        f"五险一金: ￥{social_deduction:.0f} | "
                        f"个税: ￥{tax:.0f}"
                    )

                    # 使用税后月薪计算时薪
                    salary_per_second = net_monthly / (days * daily_hours * 3600)
                else:
                    # 简单模式：仅使用税前
                    salary_per_second = monthly / (days * daily_hours * 3600)
                    self.net_salary_var.set("税后: (详细模式可查看)")

                earnings = salary_per_second * worked_seconds
                self.earnings_var.set(f"🐟 已摸鱼收入 ￥{earnings:.2f}")
            except Exception:
                self.earnings_var.set("无效输入")

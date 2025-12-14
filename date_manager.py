import streamlit as st
from datetime import datetime, timedelta

class DateManager:
    def __init__(self):
        self.base_url = "https://live.500.com/wanchang.php"
        self.current_date = datetime.now()
        
    def render(self):
        """渲染简洁的日期选择器"""
        # 创建年份、月份、日的选择框，使用一行布局
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            # 年份选择器（支持过去6年到未来2年）
            years = list(range(self.current_date.year - 6, self.current_date.year + 3))
            selected_year = st.selectbox(
                "年",
                options=years,
                index=years.index(self.current_date.year),
                key="year_selector",
                label_visibility="collapsed"
            )
        
        with col2:
            # 月份选择器
            months = list(range(1, 13))
            selected_month = st.selectbox(
                "月",
                options=months,
                index=self.current_date.month - 1,
                key="month_selector",
                label_visibility="collapsed"
            )
        
        with col3:
            # 计算该月的天数
            if selected_month == 2:
                # 处理闰年
                if (selected_year % 4 == 0 and selected_year % 100 != 0) or (selected_year % 400 == 0):
                    days_in_month = 29
                else:
                    days_in_month = 28
            else:
                days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][selected_month - 1]
            
            # 日期选择器
            days = list(range(1, days_in_month + 1))
            selected_day = st.selectbox(
                "日",
                options=days,
                index=min(self.current_date.day - 1, days_in_month - 1),
                key="day_selector",
                label_visibility="collapsed"
            )
        
        with col4:
            # 搜索按钮
            if st.button(
                "查看该日期比赛",
                key="date_search_button",
                type="primary"
            ):
                # 生成日期字符串
                date_str = f"{selected_year}-{selected_month:02d}-{selected_day:02d}"
                # 设置选中的日期到会话状态
                st.session_state.selected_date = date_str
                # 设置需要更新数据的标志
                st.session_state.update_by_date = True

# 创建全局实例
global_date_manager = DateManager()
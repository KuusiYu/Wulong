import streamlit as st

# 定义UI样式
class UIStyles:
    @staticmethod
    def get_font_css():
        """获取字体CSS样式"""
        return """
        <style>
            /* 引入自定义字体 */
            @font-face {
                font-family: 'Smiley Sans';
                src: url('static/SmileySans-Oblique.ttf') format('truetype');
                font-weight: normal;
                font-style: normal;
            }
            
            /* 全局字体应用 */
            * {
                font-family: 'Smiley Sans', sans-serif !important;
            }
            
            html, body, [data-testid="stApp"] {
                font-family: 'Smiley Sans', sans-serif !important;
            }
        </style>
        """
    
    @staticmethod
    def get_layout_css():
        """获取布局CSS样式"""
        return """
        <style>
            /* 保留顶部工具栏，仅隐藏主菜单按钮 */
            .stMainMenu {
                display: none !important;
            }
            
            /* 确保侧边栏可以正常折叠展开 */
            [data-testid="stSidebar"] {
                /* 移除强制显示的样式，允许正常折叠 */
                position: relative !important;
            }
            
            /* 确保侧边栏头部可见 */
            [data-testid="stSidebarHeader"] {
                display: flex !important;
                visibility: visible !important;
            }
            
            /* 确保侧边栏内容可见 */
            [data-testid="stSidebarContent"] {
                display: block !important;
                visibility: visible !important;
            }
            
            /* 确保侧边栏容器可见 */
            .css-1d391kg {
                display: flex !important;
                flex-direction: column !important;
            }
            
            /* 确保侧边栏展开按钮可见 */
            [data-testid="stExpandSidebarButton"] {
                display: flex !important;
                visibility: visible !important;
            }
            
            /* 修复Material Icons显示为文字的问题 */
            [data-testid="stIconMaterial"] {
                font-family: 'Material Icons' !important;
                font-style: normal;
                font-weight: normal;
                font-size: 24px;
                line-height: 1;
                letter-spacing: normal;
                text-transform: none;
                display: inline-block;
                white-space: nowrap;
                word-wrap: normal;
                direction: ltr;
                -webkit-font-feature-settings: 'liga';
                -webkit-font-smoothing: antialiased;
            }
            
            /* 确保侧边栏展开按钮图标正确显示 */
            [data-testid="stExpandSidebarButton"] span {
                font-family: 'Material Icons' !important;
            }
        </style>
        """
    
    @staticmethod
    def get_card_css():
        """获取现代化比赛卡片CSS样式"""
        return """
        <style>
            /* 现代化比赛卡片样式 */
            .modern-match-card {
                background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                border-radius: 16px;
                padding: 20px;
                margin: 12px 0;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                border: 1px solid #e9ecef;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }
            
            /* 卡片悬停效果 */
            .modern-match-card:hover {
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
                transform: translateY(-4px);
                border-color: #dee2e6;
            }
            
            /* 卡片头部 */
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 12px;
                border-bottom: 2px solid #f0f0f0;
            }
            
            /* 联赛信息 */
            .league-info {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            /* 联赛徽章 */
            .league-badge {
                background-color: #3b82f6;
                color: white;
                padding: 6px 12px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 0.9rem;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            /* 竞彩徽章 */
            .jczq-badge {
                background: linear-gradient(135deg, #ff6b00 0%, #ff8e31 100%);
                color: white;
                padding: 4px 10px;
                border-radius: 16px;
                font-weight: bold;
                font-size: 0.8rem;
                box-shadow: 0 2px 4px rgba(255, 107, 0, 0.2);
            }
            
            /* 比赛时间 */
            .match-time {
                color: #64748b;
                font-size: 0.85rem;
                font-weight: 500;
            }
            
            /* 比赛内容 */
            .match-content {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
                margin-bottom: 16px;
            }
            
            /* 球队信息 */
            .team-info {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 10px;
            }
            
            /* 球队logo */
            .team-logo {
                width: 64px;
                height: 64px;
                border-radius: 50%;
                object-fit: cover;
                border: 3px solid #f0f0f0;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            }
            
            .team-logo:hover {
                transform: scale(1.05);
                border-color: #e0e0e0;
            }
            
            /* 球队logo占位符 */
            .team-logo-placeholder {
                width: 64px;
                height: 64px;
                border-radius: 50%;
                background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
                border: 3px solid #f0f0f0;
            }
            
            /* 球队名称 */
            .team-name {
                font-weight: bold;
                color: #1e293b;
                font-size: 0.95rem;
                text-align: center;
                line-height: 1.2;
            }
            
            /* 比分信息 */
            .score-info {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                min-width: 120px;
            }
            
            /* 全场比分 */
            .full-time-score {
                font-size: 2.2em;
                font-weight: bold;
                color: #3b82f6;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            /* 半场比分 */
            .half-time-score {
                font-size: 0.85em;
                color: #94a3b8;
                font-weight: 500;
            }
            
            /* 比赛状态 */
            .match-status {
                font-size: 0.8em;
                color: #ef4444;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            /* 详细数据 */
            .match-details {
                margin-top: 12px;
            }
            
            /* 自定义details样式 */
            .details-expander {
                border: 1px solid #e9ecef;
                border-radius: 8px;
                overflow: hidden;
                background: #f8f9fa;
            }
            
            .details-summary {
                background: #f8f9fa;
                padding: 12px 16px;
                cursor: pointer;
                font-weight: 600;
                color: #475569;
                transition: all 0.3s ease;
                display: flex;
                justify-content: space-between;
                align-items: center;
                user-select: none;
            }
            
            .details-summary:hover {
                background: #e9ecef;
                color: #1e293b;
            }
            
            .details-summary::after {
                content: '▼';
                font-size: 0.8rem;
                transition: transform 0.3s ease;
            }
            
            .details-expander[open] .details-summary::after {
                transform: rotate(180deg);
            }
            
            .details-content {
                padding: 16px;
                background: white;
                border-top: 1px solid #e9ecef;
            }
            
            .details-content ul {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            
            .details-content li {
                padding: 6px 0;
                color: #475569;
                font-size: 0.9rem;
            }
            
            /* 响应式设计 */
            @media (max-width: 768px) {
                .match-content {
                    gap: 10px;
                }
                
                .team-logo {
                    width: 48px;
                    height: 48px;
                }
                
                .full-time-score {
                    font-size: 1.8em;
                }
                
                .team-name {
                    font-size: 0.85rem;
                }
            }
        </style>
        """
    
    @staticmethod
    def apply_all_styles():
        """应用所有样式"""
        # 应用字体样式
        st.markdown(UIStyles.get_font_css(), unsafe_allow_html=True)
        # 应用布局样式
        st.markdown(UIStyles.get_layout_css(), unsafe_allow_html=True)
        # 应用卡片样式
        st.markdown(UIStyles.get_card_css(), unsafe_allow_html=True)
    
    @staticmethod
    def render_match_card(match_data):
        """使用Streamlit原生组件渲染美观的比赛卡片"""
        # 检查是否有竞彩标识
        jczq_identifier = match_data.get('jczq_identifier', '')
        
        # 创建卡片外层容器，添加现代化样式
        card_html = f"""
        <div class="modern-match-card">
            <!-- 卡片头部 -->
            <div class="card-header">
                <div class="league-info">
                    <span class="league-badge" style="background-color: {match_data['league_color']};">{match_data['league']}</span>
                    {f'<span class="jczq-badge">{jczq_identifier}</span>' if jczq_identifier else ''}
                </div>
                <div class="match-time">{match_data['round']} | {match_data['time']}</div>
            </div>
            
            <!-- 比赛内容 -->
            <div class="match-content">
                <!-- 主队 -->
                <div class="team-info">
                    {f'<img class="team-logo" src="https://odds.500.com/static/soccerdata/images/TeamPic/teamsignnew_{match_data["home_team_id"]}.png" alt="{match_data["home_team"]}" />' if match_data['home_team_id'] else '<div class="team-logo-placeholder"></div>'}
                    <div class="team-name">{match_data['home_team']}</div>
                </div>
                
                <!-- 比分 -->
                <div class="score-info">
                    <div class="full-time-score">{match_data['score']}</div>
                    {f'<div class="half-time-score">({match_data["half_score"]})</div>' if match_data['half_score'] else ''}
                    <div class="match-status">{match_data['match_status']}</div>
                </div>
                
                <!-- 客队 -->
                <div class="team-info">
                    {f'<img class="team-logo" src="https://odds.500.com/static/soccerdata/images/TeamPic/teamsignnew_{match_data["away_team_id"]}.png" alt="{match_data["away_team"]}" />' if match_data['away_team_id'] else '<div class="team-logo-placeholder"></div>'}
                    <div class="team-name">{match_data['away_team']}</div>
                </div>
            </div>
            
            <!-- 详细数据 -->
            <div class="match-details">
                <details class="details-expander">
                    <summary class="details-summary">详细数据</summary>
                    <div class="details-content">
                        <ul>
                            <li>Match ID: {match_data['match_id']}</li>
                            <li>Status: {match_data['status']}</li>
                            <li>LID: {match_data['lid']}</li>
                            <li>FID: {match_data['fid']}</li>
                            <li>SID: {match_data['sid']}</li>
                            {f'<li>竞彩ID: {jczq_identifier}</li>' if jczq_identifier else ''}
                        </ul>
                    </div>
                </details>
            </div>
        </div>
        """
        
        # 渲染卡片
        st.markdown(card_html, unsafe_allow_html=True)
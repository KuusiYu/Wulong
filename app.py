import streamlit as st
import re
import asyncio
import aiohttp
import random
import pandas as pd
import time
# 导入scipy.special用于伽马函数计算
from scipy.special import gamma
# 禁用aiohttp的SSL警告
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from bs4 import BeautifulSoup
# 导入竞彩标识管理模块
from jingcai_manager import global_jingcai_manager, update_matches_with_jingcai, crawl_jingcai_ids
# 导入日期选择管理模块
from date_manager import global_date_manager
# 导入赔率爬虫模块
from odds_crawler import fetch_all_odds_data
# 导入联赛数据模块
from league_data import get_league_data
# 导入历史交战记录爬虫模块
from history_crawler import fetch_match_history

# 配置页面，隐藏顶部工具栏并设置宽屏模式
st.set_page_config(
    initial_sidebar_state="expanded",
    layout="wide",  # 设置默认宽屏模式
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# 显示顶部工具栏和主菜单，移除隐藏CSS

# 定义按日期爬取比赛数据的函数 - 支持历史和未来日期
async def crawl_matches_by_date(date_str):
    """根据指定日期爬取比赛数据（支持历史和未来日期）"""
    # 构建数据URL，该URL同时支持历史和未来日期
    url = f'https://live.500.com/wanchang.php?e={date_str}'
    
    # 防封IP处理：使用随机User-Agent池
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # 防封IP处理：添加随机延迟（优化为更短时间）
    await asyncio.sleep(random.uniform(0.3, 1.0))
    
    try:
        # 创建aiohttp会话
        async with aiohttp.ClientSession() as session:
            # 发送请求
            async with session.get(url, headers=headers, timeout=15, ssl=False) as response:
                # 读取响应内容
                content = await response.read()
                
                # 处理编码问题
                try:
                    # 尝试GBK编码（常见于中文网站）
                    html = content.decode('gbk')
                except UnicodeDecodeError:
                    try:
                        # 尝试GB2312编码
                        html = content.decode('gb2312')
                    except UnicodeDecodeError:
                        # 最后尝试UTF-8编码
                        html = content.decode('utf-8')
                
                # 解析HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # 找到所有比赛行
                match_rows = soup.find_all('tr', attrs={'id': lambda x: x and x.startswith('a')})
                
                matches = []
                
                for row in match_rows:
                    # 提取属性
                    match_id = row.get('id')
                    status = row.get('status')
                    gy = row.get('gy')
                    yy = row.get('yy')
                    lid = row.get('lid')
                    fid = row.get('fid')
                    sid = row.get('sid')
                    
                    # 提取联赛信息 - 参考页面中联赛在td[0]
                    league_td = row.find('td', class_='ssbox_01')
                    if league_td:
                        league = league_td.text.strip()
                        # 提取联赛的背景颜色
                        league_color = league_td.get('bgcolor', '#3b82f6')  # 默认使用蓝色
                    else:
                        league = ''
                        league_color = '#3b82f6'
                    
                    # 提取轮次
                    tds = row.find_all('td')
                    if len(tds) < 9:
                        continue
                        
                    # 参考页面的HTML结构固定，td索引如下：
                    # 0: 赛事, 1: 轮次, 2: 比赛时间, 3: 状态, 4: 主队, 5: 比分, 6: 客队, 7: 半场, 8: 直播, 9: 分析
                    round_info = tds[1].text.strip() if len(tds) > 1 else ''
                    match_time = tds[2].text.strip() if len(tds) > 2 else ''
                    match_status = tds[3].text.strip() if len(tds) > 3 else ''
                    
                    # 提取主队 - 参考页面中主队在td[4]
                    home_td = tds[4]
                    home_team = ''
                    home_team_id = ''
                    if home_td:
                        # 优先提取a标签中的球队名称，避免包含红黄牌和排名
                        home_a = home_td.find('a')
                        if home_a:
                            # 优先提取span.mainName（如果存在）
                            main_name = home_a.find('span', class_='mainName')
                            if main_name:
                                home_team = main_name.text.strip()
                            else:
                                home_team = home_a.text.strip()
                            # 提取球队ID
                            import re
                            href = home_a.get('href', '')
                            # 从href中提取球队ID，如 /team/3303/ 中的3303
                            id_match = re.search(r'/team/(\d+)/', href)
                            if id_match:
                                home_team_id = id_match.group(1)
                        else:
                            # 如果没有a标签，再提取整个td的文本
                            home_team = home_td.text.strip()
                            import re
                            # 移除方括号中的排名
                            home_team = re.sub(r'\[[^\]]+\]', '', home_team)
                            # 移除数字前缀
                            home_team = re.sub(r'^\d+', '', home_team)
                            home_team = home_team.strip()
                    
                    # 提取比分信息 - 参考页面中比分在td[5]
                    score = ''
                    score_td = tds[5] if len(tds) > 5 else None
                    if score_td:
                        # 尝试从pk div提取比分（适用于有比分的比赛）
                        score_div = score_td.find('div', class_='pk')
                        if score_div:
                            # 提取主队比分
                            home_score_a = score_div.find('a', class_='clt1')
                            home_score = home_score_a.text.strip() if home_score_a else ''
                            
                            # 提取客队比分
                            away_score_a = score_div.find('a', class_='clt3')
                            away_score = away_score_a.text.strip() if away_score_a else ''
                            
                            # 组合全场比分
                            score = f"{home_score}-{away_score}" if home_score and away_score else ''
                        else:
                            # 直接从td中获取比分文本
                            score_text = score_td.text.strip()
                            if score_text and score_text != '-':
                                score = score_text
                    
                    # 提取客队 - 参考页面中客队在td[6]
                    away_td = tds[6] if len(tds) > 6 else None
                    away_team = ''
                    away_team_id = ''
                    if away_td:
                        # 优先提取a标签中的球队名称，避免包含红黄牌和排名
                        away_a = away_td.find('a')
                        if away_a:
                            # 优先提取span.mainName（如果存在）
                            main_name = away_a.find('span', class_='mainName')
                            if main_name:
                                away_team = main_name.text.strip()
                            else:
                                away_team = away_a.text.strip()
                            # 提取球队ID
                            import re
                            href = away_a.get('href', '')
                            # 从href中提取球队ID，如 /team/3303/ 中的3303
                            id_match = re.search(r'/team/(\d+)/', href)
                            if id_match:
                                away_team_id = id_match.group(1)
                        else:
                            # 如果没有a标签，再提取整个td的文本
                            away_team = away_td.text.strip()
                            import re
                            # 移除方括号中的排名
                            away_team = re.sub(r'\[[^\]]+\]', '', away_team)
                            # 移除数字前缀
                            away_team = re.sub(r'^\d+', '', away_team)
                            away_team = away_team.strip()
                    
                    # 提取半场比分 - 参考页面中半场在td[7]
                    half_score_td = tds[7] if len(tds) > 7 else None
                    half_score = half_score_td.text.strip() if half_score_td else ''
                    
                    # 构建比赛字典
                    match = {
                        'match_id': match_id,
                        'status': status,
                        'gy': gy,
                        'yy': yy,
                        'lid': lid,
                        'fid': fid,
                        'sid': sid,
                        'league': league,
                        'league_color': league_color,
                        'round': round_info,
                        'time': match_time,
                        'match_status': match_status,
                        'home_team': home_team,
                        'home_team_id': home_team_id,
                        'score': score,
                        'half_score': half_score,
                        'away_team': away_team,
                        'away_team_id': away_team_id,
                        'jingcai_id': ''  # 初始化竞彩标识字段
                    }
                    
                    matches.append(match)
                
                return matches
    except asyncio.TimeoutError:
        st.error('请求超时，请稍后重试')
        return []
    except aiohttp.ClientError as e:
        st.error(f'网络请求失败: {e}')
        return []
    except Exception as e:
        st.error(f'爬取失败: {e}')
        import traceback
        st.text(traceback.format_exc())
        return []


# 定义爬取函数 - 支持防封IP和异步处理
async def crawl_matches():
    url = 'https://live.500.com/2h1.php'
    
    # 防封IP处理：使用随机User-Agent池
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # 防封IP处理：添加随机延迟（优化为更短时间）
    await asyncio.sleep(random.uniform(0.3, 1.0))
    
    try:
        # 创建aiohttp会话
        async with aiohttp.ClientSession() as session:
            # 发送请求
            async with session.get(url, headers=headers, timeout=15, ssl=False) as response:
                # 读取响应内容
                content = await response.read()
                
                # 处理编码问题
                try:
                    # 尝试GBK编码（常见于中文网站）
                    html = content.decode('gbk')
                except UnicodeDecodeError:
                    try:
                        # 尝试GB2312编码
                        html = content.decode('gb2312')
                    except UnicodeDecodeError:
                        # 最后尝试UTF-8编码
                        html = content.decode('utf-8')
                
                # 解析HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # 找到所有比赛行
                match_rows = soup.find_all('tr', attrs={'id': lambda x: x and x.startswith('a')})
                
                matches = []
                
                for row in match_rows:
                    # 提取属性
                    match_id = row.get('id')
                    status = row.get('status')
                    gy = row.get('gy')
                    yy = row.get('yy')
                    lid = row.get('lid')
                    fid = row.get('fid')
                    sid = row.get('sid')
                    
                    # 提取联赛信息
                    league_td = row.find('td', class_='ssbox_01')
                    if league_td:
                        league = league_td.text.strip()
                        # 提取联赛的背景颜色
                        league_color = league_td.get('bgcolor', '#3b82f6')  # 默认使用蓝色
                    else:
                        league = ''
                        league_color = '#3b82f6'
                    
                    # 提取轮次
                    tds = row.find_all('td')
                    if len(tds) < 10:
                        continue
                    
                    # 初始化所有字段
                    home_team = ''
                    away_team = ''
                    score = ''
                    half_score = ''
                    match_status = ''
                    home_team_id = ''
                    away_team_id = ''
                    
                    # 1. 尝试从属性中获取球队信息（最可靠的方式）
                    teams = []
                    if gy:
                        teams = gy.split(',')
                    elif yy:
                        teams = yy.split(',')
                    
                    # 从属性中提取联赛、主队、客队
                    league_from_attr = ''
                    if len(teams) >= 3:
                        league_from_attr, home_team, away_team = teams[:3]
                        home_team = home_team.strip()
                        away_team = away_team.strip()
                    elif len(teams) >= 2:
                        home_team, away_team = teams[:2]
                        home_team = home_team.strip()
                        away_team = away_team.strip()
                    
                    # 2. 如果属性中没有，从td中提取
                    # 提取轮次和时间
                    round_info = tds[2].text.strip() if len(tds) > 2 else ''
                    match_time = tds[3].text.strip() if len(tds) > 3 else ''
                    
                    # 提取比赛状态
                    match_status = tds[4].text.strip() if len(tds) > 4 else ''
                    
                    # 提取比分（仅适用于有比分的赛事）
                    score_div = row.find('div', class_='pk')
                    if score_div:
                        # 提取主队比分
                        home_score_a = score_div.find('a', class_='clt1')
                        home_score = home_score_a.text.strip() if home_score_a else ''
                        
                        # 提取客队比分
                        away_score_a = score_div.find('a', class_='clt3')
                        away_score = away_score_a.text.strip() if away_score_a else ''
                        
                        # 组合全场比分
                        score = f"{home_score}-{away_score}" if home_score and away_score else ''
                    
                    # 提取半场比分
                    half_score_td = tds[8] if len(tds) > 8 else None
                    half_score = half_score_td.text.strip() if half_score_td else ''
                    
                    # 从td中提取主队信息（如果属性中没有）
                    if not home_team:
                        home_td = tds[5] if len(tds) > 5 else None
                        if home_td:
                            # 优先提取a标签中的球队名称
                            home_a = home_td.find('a')
                            if home_a:
                                home_team = home_a.text.strip()
                                # 提取球队ID
                                import re
                                href = home_a.get('href', '')
                                id_match = re.search(r'/team/(\d+)/', href)
                                if id_match:
                                    home_team_id = id_match.group(1)
                            else:
                                home_team = home_td.text.strip()
                    
                    # 从td中提取客队信息（如果属性中没有）
                    if not away_team:
                        away_td = tds[7] if len(tds) > 7 else None
                        if away_td:
                            # 优先提取a标签中的球队名称
                            away_a = away_td.find('a')
                            if away_a:
                                away_team = away_a.text.strip()
                                # 提取球队ID
                                import re
                                href = away_a.get('href', '')
                                id_match = re.search(r'/team/(\d+)/', href)
                                if id_match:
                                    away_team_id = id_match.group(1)
                            else:
                                away_team = away_td.text.strip()
                    
                    # 3. 清理球队名称
                    import re
                    home_team = re.sub(r'\[[^\]]+\]', '', home_team).strip()
                    home_team = re.sub(r'^\d+', '', home_team).strip()
                    away_team = re.sub(r'\[[^\]]+\]', '', away_team).strip()
                    away_team = re.sub(r'^\d+', '', away_team).strip()
                    
                    # 4. 尝试为从属性中提取的球队获取ID
                    # 对于从属性或特殊处理中获取的球队名称，尝试从td[5]和td[7]的a标签中提取ID
                    if (home_team and not home_team_id) or (away_team and not away_team_id):
                        # 检查主队的a标签（td[5]）
                        if home_team and not home_team_id:
                            home_td = tds[5] if len(tds) > 5 else None
                            if home_td:
                                home_a = home_td.find('a')
                                if home_a:
                                    href = home_a.get('href', '')
                                    id_match = re.search(r'/team/(\d+)/', href)
                                    if id_match:
                                        home_team_id = id_match.group(1)
                        
                        # 检查客队的a标签（td[7]）
                        if away_team and not away_team_id:
                            away_td = tds[7] if len(tds) > 7 else None
                            if away_td:
                                away_a = away_td.find('a')
                                if away_a:
                                    href = away_a.get('href', '')
                                    id_match = re.search(r'/team/(\d+)/', href)
                                    if id_match:
                                        away_team_id = id_match.group(1)
                    
                    # 5. 特殊情况处理：如果主队或客队仍然为空，尝试从其他td提取
                    if not home_team or not away_team:
                        # 检查td[5]和td[6]（可能是未来赛事的特殊结构）
                        if len(tds) > 6:
                            if not home_team:
                                home_candidate = tds[5].text.strip()
                                if home_candidate and home_candidate != '-':
                                    home_team = re.sub(r'\[[^\]]+\]', '', home_candidate).strip()
                                    home_team = re.sub(r'^\d+', '', home_team).strip()
                                    # 尝试提取球队ID
                                    home_a = tds[5].find('a')
                                    if home_a:
                                        href = home_a.get('href', '')
                                        id_match = re.search(r'/team/(\d+)/', href)
                                        if id_match:
                                            home_team_id = id_match.group(1)
                            if not away_team:
                                away_candidate = tds[6].text.strip()
                                if away_candidate and away_candidate != '-':
                                    away_team = re.sub(r'\[[^\]]+\]', '', away_candidate).strip()
                                    away_team = re.sub(r'^\d+', '', away_team).strip()
                                    # 尝试提取球队ID
                                    away_a = tds[6].find('a')
                                    if away_a:
                                        href = away_a.get('href', '')
                                        id_match = re.search(r'/team/(\d+)/', href)
                                        if id_match:
                                            away_team_id = id_match.group(1)
                    
                    # 5. 确保比赛状态正确
                    if match_status in ['-', '']:
                        # 根据是否有比分判断比赛状态
                        if score:
                            match_status = '完'
                        else:
                            match_status = ''
                    
                    # 构建比赛字典
                    match = {
                        'match_id': match_id,
                        'status': status,
                        'gy': gy,
                        'yy': yy,
                        'lid': lid,
                        'fid': fid,
                        'sid': sid,
                        'league': league,
                        'league_color': league_color,
                        'round': round_info,
                        'time': match_time,
                        'match_status': match_status,
                        'home_team': home_team,
                        'home_team_id': home_team_id,
                        'score': score,
                        'half_score': half_score,
                        'away_team': away_team,
                        'away_team_id': away_team_id,
                        'jingcai_id': ''  # 初始化竞彩标识字段
                    }
                    
                    matches.append(match)
                
                return matches
    except asyncio.TimeoutError:
        st.error('请求超时，请稍后重试')
        return []
    except aiohttp.ClientError as e:
        st.error(f'网络请求失败: {e}')
        return []
    except Exception as e:
        st.error(f'爬取失败: {e}')
        import traceback
        st.text(traceback.format_exc())
        return []



# 定义状态映射函数，根据status字段值返回正确的比赛状态
def get_match_status_display(status_value):
    """根据status字段值返回正确的中文比赛状态"""
    status_map = {
        '0': '未开始',
        '1': '上半场',
        '2': '中场',
        '3': '下半场',
        '4': '完场',
        '5': '取消',
        '6': '延期',
        '7': '中断',
        '8': '待定'
    }
    return status_map.get(str(status_value), '')

# 初始化会话状态
if 'matches' not in st.session_state:
    st.session_state.matches = []
    st.session_state.last_update = None
    st.session_state.is_crawling = False
    st.session_state.selected_date = None
    st.session_state.update_by_date = False
    st.session_state.is_historical = False

# 爬取函数（带会话状态更新）
def update_matches():
    if st.session_state.is_crawling:
        return
    
    st.session_state.is_crawling = True
    try:
        matches = []
        
        # 检查是否需要根据日期爬取历史数据
        if st.session_state.update_by_date and st.session_state.selected_date:
            date_key = st.session_state.selected_date
            # 直接爬取数据，不使用缓存
            matches = asyncio.run(crawl_matches_by_date(date_key))
            # 根据日期判断是历史还是未来赛事
            current_date = time.strftime("%Y-%m-%d")
            st.session_state.is_historical = date_key < current_date
        else:
            # 直接爬取原始页面数据，不使用缓存
            matches = asyncio.run(crawl_matches())
            st.session_state.is_historical = False
        
        if matches:
            # 处理比赛状态，确保match_status字段使用正确的状态值
            for match in matches:
                match['match_status'] = get_match_status_display(match['status']) if match['status'] else match['match_status']
            
            # 抓取竞彩标识数据
            crawl_jingcai_ids()
            # 将竞彩标识添加到比赛数据中
            matches_with_jingcai = update_matches_with_jingcai(matches)
            st.session_state.matches = matches_with_jingcai
            st.session_state.last_update = time.strftime("%Y-%m-%d %H:%M:%S")
            # 重置日期更新标志
            st.session_state.update_by_date = False
    finally:
        st.session_state.is_crawling = False



# 显示数据
# 先添加日期选择器，检查是否需要更新数据
global_date_manager.render()

# 检查是否需要根据日期更新数据
if st.session_state.update_by_date and st.session_state.selected_date:
    with st.spinner(f'正在获取{st.session_state.selected_date}的比赛数据...'):
        update_matches()
else:
    # 初始加载或刷新时，如果没有选择日期，显示原始页面数据
    if not st.session_state.matches:
        with st.spinner('页面加载中，正在自动获取比赛数据...'):
            # 确保显示原始页面数据
            st.session_state.selected_date = None
            st.session_state.update_by_date = False
            update_matches()

if st.session_state.matches:
    # 转换为DataFrame
    df = pd.DataFrame(st.session_state.matches)
    
    # 添加过滤选项
    leagues = sorted(df['league'].unique())
    selected_league = st.sidebar.selectbox('选择联赛', ['全部'] + leagues)
    
    statuses = sorted(df['match_status'].unique())
    selected_status = st.sidebar.selectbox('选择状态', ['全部'] + statuses)
    
    # 添加竞彩赛事筛选复选框
    filter_jingcai = st.sidebar.checkbox('只显示竞彩赛事')
    
    # 应用过滤
    filtered_df = df.copy()
    if selected_league != '全部':
        filtered_df = filtered_df[filtered_df['league'] == selected_league]
    
    if selected_status != '全部':
        filtered_df = filtered_df[filtered_df['match_status'] == selected_status]
    
    # 应用竞彩赛事筛选
    if filter_jingcai:
        filtered_df = filtered_df[filtered_df['jingcai_id'] != '']
    

    
    # 清除筛选条件按钮
    if st.sidebar.button('清除筛选条件'):
        with st.spinner('正在清除筛选条件...'):
            # 重置所有筛选状态
            st.session_state.selected_date = None
            st.session_state.update_by_date = False
            # 重新获取数据
            update_matches()
            # 触发页面重新渲染
            st.rerun()

    # 刷新按钮：总是显示原始页面数据
    if st.sidebar.button('刷新'):
        with st.spinner('正在刷新数据...'):
            # 重置日期选择状态，确保刷新时显示原始页面数据
            st.session_state.selected_date = None
            st.session_state.update_by_date = False
            update_matches()
    
    # 比赛卡片样式展示
    
    # 定义CSS样式（移到循环外部，只渲染一次）
    st.markdown("""<style>
        .match-card {
            border-radius: 10px;
            padding: 16px;
            margin: 8px 0;
            background-color: #ffffff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .match-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.18);
            transform: translateY(-2px);
        }
        .header-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
        }
        .match-league {
            font-weight: bold;
            color: #1e293b;
            font-size: 1rem;
            margin: 0;
        }
        .match-time {
            color: #64748b;
            font-size: 0.85em;
            margin: 0;
            text-align: right;
        }
        .match-status {
            font-weight: bold;
            color: #ef4444;
            font-size: 0.8em;
        }
        .team-name {
            font-weight: bold;
            color: #1e293b;
            font-size: 0.95rem;
        }
        .match-score {
            font-size: 1.8em;
            font-weight: bold;
            color: #3b82f6;
        }
        .odds-section {
            margin-top: 12px;
            padding: 12px;
            background-color: #f8fafc;
            border-radius: 6px;
            border-left: 3px solid #3b82f6;
        }
        .odds-title {
            font-weight: bold;
            color: #1e293b;
            font-size: 0.9em;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .odds-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8em;
        }
        .odds-table th,
        .odds-table td {
            padding: 4px 8px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        .odds-table th {
            background-color: #e2e8f0;
            color: #64748b;
            font-weight: bold;
        }
        .odds-row {
            background-color: white;
        }
        .odds-row:nth-child(even) {
            background-color: #f8fafc;
        }
        .company-name {
            font-weight: bold;
            color: #3b82f6;
        }
        .odds-type {
            color: #64748b;
            font-style: italic;
        }
        .fetch-odds-btn {
            background-color: #3b82f6;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.8em;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .fetch-odds-btn:hover {
            background-color: #2563eb;
            transform: translateY(-1px);
        }
    </style>""", unsafe_allow_html=True)
    
    # 初始化会话状态用于存储赔率数据（移到循环外部）
    if 'odds_data' not in st.session_state:
        st.session_state.odds_data = {}
    
    # 创建回调函数工厂（移到循环外部）
    def create_on_fetch_odds(fid):
        def on_fetch_odds():
            with st.spinner(f'正在获取比赛{fid}的赔率数据...'):
                try:
                    odds_data = fetch_all_odds_data(fid)
                    st.session_state.odds_data[fid] = odds_data
                except Exception as e:
                    import traceback
                    error_msg = f"获取赔率数据失败: {str(e)}\n详细错误:\n{traceback.format_exc()}"
                    st.error(error_msg)
                    st.session_state.odds_data[fid] = None
        return on_fetch_odds
    
    # 默认使用单列布局
    cols = st.columns(1)
    
    # 卡片计数器
    card_count = 0
    
    for index, row in filtered_df.iterrows():
        with cols[card_count % len(cols)]:
            # 创建比赛卡片，根据内容自动调整高度
            # 使用st.container创建独立的渲染上下文
            container = st.container(border=False)
            
            with container:
                # 渲染竞彩标识徽章
                jingcai_badge = global_jingcai_manager.render_jingcai_badge(row['match_id'])
                
                # 确保未来赛事和历史赛事使用相同的UI结构
                # 检查数据是否存在问题，进行特殊处理
                display_home_team = row["home_team"]
                display_away_team = row["away_team"]
                display_score = row["score"]
                display_half_score = row["half_score"]
                # 使用status字段获取正确的比赛状态
                display_match_status = get_match_status_display(row["status"]) if row["status"] else row["match_status"]
                
                # 特殊处理：如果主队和客队显示有问题，尝试从属性中提取
                if (not display_home_team or display_home_team == '-') and (not display_away_team or display_away_team == '-'):
                    # 尝试从match_id或其他字段获取信息
                    # 检查score字段是否包含球队名称（这是当前问题的根源）
                    if 'U15' in str(display_score) or '[' in str(display_score):
                        # 这是一个错误的映射，将主队显示到了比分字段
                        if not display_home_team or display_home_team == '-':
                            display_home_team = str(display_score)
                            display_score = ''
                    
                    # 检查match_status字段是否包含球队名称
                    if 'U15' in str(display_match_status) or '[' in str(display_match_status):
                        # 这是一个错误的映射，将客队显示到了比赛状态字段
                        if not display_away_team or display_away_team == '-':
                            display_away_team = str(display_match_status)
                            display_match_status = ''
                
                # 清理球队名称
                import re
                display_home_team = re.sub(r'\[[^\]]+\]', '', str(display_home_team)).strip()
                display_away_team = re.sub(r'\[[^\]]+\]', '', str(display_away_team)).strip()
                
                # 修复logo显示逻辑
                # 只使用已有的球队ID来显示logo
                home_logo = ''
                away_logo = ''
                
                # 使用已有的球队ID显示logo
                if row["home_team_id"]:
                    home_logo = f'<img src="https://odds.500.com/static/soccerdata/images/TeamPic/teamsignnew_{row["home_team_id"]}.png" alt="{display_home_team}" width="48" height="48" style="border-radius:50%;" />'
                
                if row["away_team_id"]:
                    away_logo = f'<img src="https://odds.500.com/static/soccerdata/images/TeamPic/teamsignnew_{row["away_team_id"]}.png" alt="{display_away_team}" width="48" height="48" style="border-radius:50%;" />'
                
                # 检查当前比赛是否已有赔率数据
                current_odds = st.session_state.odds_data.get(row['fid'], None)
                
                # 亚盘汉字到数字的映射
                def hanzi_to_handicap(hanzi_str):
                    # 移除升降二字
                    clean_hanzi = hanzi_str.replace('升', '').replace('降', '').strip()
                    
                    # 扩展到10球的亚盘汉字到数字的映射
                    hanzi_map = {
                        # 基础盘口
                        '平手': 0,
                        '平半': 0.25,
                        '半球': 0.5,
                        '半/一': 0.75,
                        '一球': 1,
                        '一/球半': 1.25,
                        '球半': 1.5,
                        '球半/两': 1.75,
                        '两球': 2,
                        '两球/两球半': 2.25,
                        '两球半': 2.5,
                        '两球半/三': 2.75,
                        '三球': 3,
                        '三球/三球半': 3.25,
                        '三球半': 3.5,
                        '三球半/四': 3.75,
                        '四球': 4,
                        '四球/四球半': 4.25,
                        '四球半': 4.5,
                        '四球半/五': 4.75,
                        '五球': 5,
                        '五球/五球半': 5.25,
                        '五球半': 5.5,
                        '五球半/六': 5.75,
                        '六球': 6,
                        '六球/六球半': 6.25,
                        '六球半': 6.5,
                        '六球半/七': 6.75,
                        '七球': 7,
                        '七球/七球半': 7.25,
                        '七球半': 7.5,
                        '七球半/八': 7.75,
                        '八球': 8,
                        '八球/八球半': 8.25,
                        '八球半': 8.5,
                        '八球半/九': 8.75,
                        '九球': 9,
                        '九球/九球半': 9.25,
                        '九球半': 9.5,
                        '九球半/十': 9.75,
                        '十球': 10,
                        # 完整写法
                        '平手/半球': 0.25,
                        '半球/一球': 0.75,
                        '一球/球半': 1.25,
                        '球半/两球': 1.75,
                        '两球/两球半': 2.25,
                        '两球半/三球': 2.75,
                        '三球/三球半': 3.25,
                        '三球半/四球': 3.75,
                        '四球/四球半': 4.25,
                        '四球半/五球': 4.75,
                        '五球/五球半': 5.25,
                        '五球半/六球': 5.75,
                        '六球/六球半': 6.25,
                        '六球半/七球': 6.75,
                        '七球/七球半': 7.25,
                        '七球半/八球': 7.75,
                        '八球/八球半': 8.25,
                        '八球半/九球': 8.75,
                        '九球/九球半': 9.25,
                        '九球半/十球': 9.75,
                        # 简化写法
                        '半一': 0.75,
                        '一/半': 1.25,
                        '球/半': 1.5,
                        '两/两球半': 2.25,
                        '两球半/三': 2.75,
                        '三/三球半': 3.25,
                        '三球半/四': 3.75,
                        '四/四球半': 4.25,
                        '四球半/五': 4.75,
                        '五/五球半': 5.25,
                        '五球半/六': 5.75,
                        '六/六球半': 6.25,
                        '六球半/七': 6.75,
                        '七/七球半': 7.25,
                        '七球半/八': 7.75,
                        '八/八球半': 8.25,
                        '八球半/九': 8.75,
                        '九/九球半': 9.25,
                        '九球半/十': 9.75
                    }
                    
                    # 处理受字情况
                    is_negative = False  # 默认主队减号
                    if '受' in clean_hanzi:
                        is_negative = True
                        # 移除受字
                        clean_hanzi = clean_hanzi.replace('受', '').strip()
                    
                    # 获取数字盘口
                    if clean_hanzi in hanzi_map:
                        handicap_value = hanzi_map[clean_hanzi]
                        # 应用符号：有受字是主队加号（正数），没有受字是主队减号（负数）
                        return f"{'+' if is_negative else '-'}{handicap_value}"
                    return hanzi_str
                
                # 盘口转换函数：处理数字盘口和汉字盘口，删除所有箭头
                def convert_handicap(handicap_str):
                    if not handicap_str:
                        return handicap_str
                    try:
                        # 移除箭头符号（↑或↓）
                        clean_handicap = handicap_str.replace('↑', '').replace('↓', '').strip()
                        
                        # 检查是否为汉字盘口
                        if any(hanzi in clean_handicap for hanzi in ['平手', '平半', '半球', '半/一', '一球', '一/球半', '球半', '两球', '受']):
                            return hanzi_to_handicap(clean_handicap)
                        
                        # 处理数字盘口（如1.5/2）
                        if '/' in clean_handicap:
                            parts = clean_handicap.split('/')
                            if len(parts) == 2:
                                value1 = float(parts[0])
                                value2 = float(parts[1])
                                avg = (value1 + value2) / 2
                                return str(avg)
                        
                        return clean_handicap
                    except (ValueError, TypeError):
                        return handicap_str
                
                # 辅助函数：移除字符串中的箭头符号
                def remove_arrows(text):
                    if not text:
                        return text
                    return text.replace('↑', '').replace('↓', '').strip()
                
                # 构建赔率数据HTML
                odds_html = ""
                if current_odds:
                    # 欧赔数据
                    if current_odds['oupei']:
                        odds_html += f"<div class='odds-title'>欧赔数据</div>"
                        odds_html += "<table class='odds-table'><tr><th>公司</th><th colspan='3'>初盘</th><th colspan='3'>即时盘</th></tr>"
                        for company, data in current_odds['oupei'].items():
                            odds_html += f"<tr class='odds-row'>"
                            odds_html += f"<td class='company-name'>{company}</td>"
                            # 移除欧赔数值中的箭头
                            initial_0 = remove_arrows(data['initial'][0])
                            initial_1 = remove_arrows(data['initial'][1])
                            initial_2 = remove_arrows(data['initial'][2])
                            instant_0 = remove_arrows(data['instant'][0])
                            instant_1 = remove_arrows(data['instant'][1])
                            instant_2 = remove_arrows(data['instant'][2])
                            odds_html += f"<td>{initial_0}</td><td>{initial_1}</td><td>{initial_2}</td>"
                            odds_html += f"<td>{instant_0}</td><td>{instant_1}</td><td>{instant_2}</td>"
                            odds_html += "</tr>"
                        odds_html += "</table><br>"
                    
                    # 亚盘数据
                    if current_odds['yapan']:
                        odds_html += f"<div class='odds-title'>亚盘数据</div>"
                        odds_html += "<table class='odds-table'><tr><th>公司</th><th colspan='3'>初盘</th><th colspan='3'>即时盘</th></tr>"
                        for company, data in current_odds['yapan'].items():
                            odds_html += f"<tr class='odds-row'>"
                            odds_html += f"<td class='company-name'>{company}</td>"
                            # 处理亚盘数据
                            initial_handicap = convert_handicap(data['initial'][1])
                            instant_handicap = convert_handicap(data['instant'][1])
                            # 移除亚盘赔率数值中的箭头
                            initial_0 = remove_arrows(data['initial'][0])
                            initial_2 = remove_arrows(data['initial'][2])
                            instant_0 = remove_arrows(data['instant'][0])
                            instant_2 = remove_arrows(data['instant'][2])
                            odds_html += f"<td>{initial_0}</td><td>{initial_handicap}</td><td>{initial_2}</td>"
                            odds_html += f"<td>{instant_0}</td><td>{instant_handicap}</td><td>{instant_2}</td>"
                            odds_html += "</tr>"
                        odds_html += "</table><br>"
                    
                    # 大小球数据
                    if current_odds['daxiao']:
                        odds_html += f"<div class='odds-title'>大小球数据</div>"
                        odds_html += "<table class='odds-table'><tr><th>公司</th><th colspan='3'>初盘</th><th colspan='3'>即时盘</th></tr>"
                        for company, data in current_odds['daxiao'].items():
                            odds_html += f"<tr class='odds-row'>"
                            odds_html += f"<td class='company-name'>{company}</td>"
                            # 处理大小球数据
                            initial_handicap = convert_handicap(data['initial'][1])
                            instant_handicap = convert_handicap(data['instant'][1])
                            # 移除大小球赔率数值中的箭头
                            initial_0 = remove_arrows(data['initial'][0])
                            initial_2 = remove_arrows(data['initial'][2])
                            instant_0 = remove_arrows(data['instant'][0])
                            instant_2 = remove_arrows(data['instant'][2])
                            odds_html += f"<td>{initial_0}</td><td>{initial_handicap}</td><td>{initial_2}</td>"
                            odds_html += f"<td>{instant_0}</td><td>{instant_handicap}</td><td>{instant_2}</td>"
                            odds_html += "</tr>"
                        odds_html += "</table>"
                # 应用合并样式
                st.markdown('''<style>
                    .match-card-merged-container {
                        border-radius: 10px;
                        background-color: #ffffff;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
                        transition: all 0.3s ease;
                        overflow: hidden;
                        margin-bottom: 16px;
                    }
                    .match-card-merged-container:hover {
                        box-shadow: 0 4px 12px rgba(0,0,0,0.18);
                        transform: translateY(-2px);
                    }
                    .match-card-inner {
                        padding: 16px;
                    }
                </style>''', unsafe_allow_html=True)
                
                # 创建合并容器
                merged_container = st.container(border=False)
                
                with merged_container:
                    # 添加合并容器的CSS类
                    st.markdown('<div class="match-card-merged-container">', unsafe_allow_html=True)
                    
                    # 创建比赛卡片HTML
                    # 创建比赛卡片HTML，避免嵌套f-string
                    half_score_html = '<div style="font-size:0.75em;color:#64748b;">(' + display_half_score + ')</div>' if display_half_score else ''
                    card_content = '<div class="match-card-inner">'
                    card_content += '<div class="header-info">'
                    card_content += '<div style="display:flex;gap:8px;align-items:center;">'
                    card_content += '<div class="match-league" style="background-color:' + row['league_color'] + ';color:white;padding:2px 8px;border-radius:4px;">' + row['league'] + '</div>'
                    card_content += jingcai_badge
                    card_content += '</div>'
                    card_content += '<div class="match-time">' + row['round'] + ' | ' + row['time'] + '</div>'
                    card_content += '</div>'
                    card_content += '<div style="display:flex;justify-content:space-between;align-items:center;">'
                    card_content += '<div style="display:flex;flex-direction:column;align-items:center;gap:4px;flex:1;min-width:120px;">'
                    card_content += home_logo
                    card_content += '<div class="team-name" style="text-align:center;font-size:0.9rem;">' + display_home_team + '</div>'
                    card_content += '</div>'
                    card_content += '<div style="text-align:center;flex:0 0 auto;width:100px;">'
                    card_content += '<div class="match-score">' + display_score + '</div>'
                    card_content += half_score_html
                    card_content += '<div class="match-status">' + display_match_status + '</div>'
                    card_content += '</div>'
                    card_content += '<div style="display:flex;flex-direction:column;align-items:center;gap:4px;flex:1;min-width:120px;">'
                    card_content += away_logo
                    card_content += '<div class="team-name" style="text-align:center;font-size:0.9rem;">' + display_away_team + '</div>'
                    card_content += '</div>'
                    card_content += '</div>'
                    card_content += '</div>'
                    
                    # 渲染卡片
                    st.html(card_content)
                    
                    # 使用Streamlit expander作为详情部分，现在它会继承合并容器的样式
                    with st.expander("详细数据", expanded=False):
                        # 创建标签页，将详细数据、赔率数据、联赛数据和双方历史交战记录分开
                        tab1, tab2, tab3, tab4, tab5 = st.tabs(["基本信息", "赔率", "联（杯）赛", "双方数据", "预测分析"])
                        
                        # 基本信息标签页
                        with tab1:
                            # 使用普通字符串拼接避免f-string问题
                            st.markdown('- Match ID: ' + row['match_id'] + '\n' +
                                       '- Status: ' + row['status'] + '\n' +
                                       '- LID: ' + row['lid'] + '\n' +
                                       '- FID: ' + row['fid'] + '\n' +
                                       '- SID: ' + row['sid'])
                        
                        # 赔率标签页
                        with tab2:
                            # 只有当用户点击展开时，才检查并获取赔率数据
                            if row['fid'] not in st.session_state.odds_data:
                                # 获取赔率数据
                                with st.spinner('正在获取比赛' + row['fid'] + '的赔率数据...'):
                                    try:
                                        odds_data = fetch_all_odds_data(row['fid'])
                                        st.session_state.odds_data[row['fid']] = odds_data
                                    except Exception as e:
                                        import traceback
                                        error_msg = f"获取赔率数据失败: {str(e)}\n详细错误:\n{traceback.format_exc()}"
                                        st.error(error_msg)
                                        st.session_state.odds_data[row['fid']] = None
                            
                            # 获取最新的赔率数据
                            current_odds = st.session_state.odds_data.get(row['fid'], None)
                            
                            # 构建赔率HTML
                            odds_html = "<p style='color:#64748b;font-size:0.85em;'>暂无赔率数据</p>"
                            if current_odds:
                                # 构建具体赔率数据
                                temp_html = ""
                                
                                # 欧赔数据
                                if current_odds['oupei']:
                                    temp_html += f"<div class='odds-title'>欧赔数据</div>"
                                    temp_html += "<table class='odds-table'><tr><th>公司</th><th colspan='3'>初盘</th><th colspan='3'>即时盘</th></tr>"
                                    for company, data in current_odds['oupei'].items():
                                        # 移除欧赔数值中的箭头
                                        initial_0 = remove_arrows(data['initial'][0])
                                        initial_1 = remove_arrows(data['initial'][1])
                                        initial_2 = remove_arrows(data['initial'][2])
                                        instant_0 = remove_arrows(data['instant'][0])
                                        instant_1 = remove_arrows(data['instant'][1])
                                        instant_2 = remove_arrows(data['instant'][2])
                                        temp_html += f"<tr class='odds-row'>"
                                        temp_html += f"<td class='company-name'>{company}</td>"
                                        temp_html += f"<td>{initial_0}</td><td>{initial_1}</td><td>{initial_2}</td>"
                                        temp_html += f"<td>{instant_0}</td><td>{instant_1}</td><td>{instant_2}</td>"
                                        temp_html += "</tr>"
                                    temp_html += "</table><br>"
                                
                                # 亚盘数据
                                if current_odds['yapan']:
                                    temp_html += f"<div class='odds-title'>亚盘数据</div>"
                                    temp_html += "<table class='odds-table'><tr><th>公司</th><th colspan='3'>初盘</th><th colspan='3'>即时盘</th></tr>"
                                    for company, data in current_odds['yapan'].items():
                                        temp_html += f"<tr class='odds-row'>"
                                        temp_html += f"<td class='company-name'>{company}</td>"
                                        # 处理亚盘数据
                                        initial_handicap = convert_handicap(data['initial'][1])
                                        instant_handicap = convert_handicap(data['instant'][1])
                                        # 移除亚盘赔率数值中的箭头
                                        initial_0 = remove_arrows(data['initial'][0])
                                        initial_2 = remove_arrows(data['initial'][2])
                                        instant_0 = remove_arrows(data['instant'][0])
                                        instant_2 = remove_arrows(data['instant'][2])
                                        temp_html += f"<td>{initial_0}</td><td>{initial_handicap}</td><td>{initial_2}</td>"
                                        temp_html += f"<td>{instant_0}</td><td>{instant_handicap}</td><td>{instant_2}</td>"
                                        temp_html += "</tr>"
                                    temp_html += "</table><br>"
                                
                                # 大小球数据
                                if current_odds['daxiao']:
                                    temp_html += f"<div class='odds-title'>大小球数据</div>"
                                    temp_html += "<table class='odds-table'><tr><th>公司</th><th colspan='3'>初盘</th><th colspan='3'>即时盘</th></tr>"
                                    for company, data in current_odds['daxiao'].items():
                                        temp_html += f"<tr class='odds-row'>"
                                        temp_html += f"<td class='company-name'>{company}</td>"
                                        # 处理大小球数据
                                        initial_handicap = convert_handicap(data['initial'][1])
                                        instant_handicap = convert_handicap(data['instant'][1])
                                        # 移除大小球赔率数值中的箭头
                                        initial_0 = remove_arrows(data['initial'][0])
                                        initial_2 = remove_arrows(data['initial'][2])
                                        instant_0 = remove_arrows(data['instant'][0])
                                        instant_2 = remove_arrows(data['instant'][2])
                                        temp_html += f"<td>{initial_0}</td><td>{initial_handicap}</td><td>{initial_2}</td>"
                                        temp_html += f"<td>{instant_0}</td><td>{instant_handicap}</td><td>{instant_2}</td>"
                                        temp_html += "</tr>"
                                    temp_html += "</table>"
                                
                                # 如果有具体赔率数据，就使用temp_html，否则保持默认
                                if temp_html:
                                    odds_html = temp_html
                            
                            # 渲染赔率数据
                            st.html(odds_html)
                        
                        # 联（杯）赛标签页
                        with tab3:
                            # 使用SID获取联赛数据
                            sid = row['sid']
                            
                            # 获取比赛的主客队id（从logo图片url中提取）
                            home_team_id = None
                            away_team_id = None
                            
                            # 从card_content中提取主队和客队id
                            # 查找主队logo
                            home_logo_match = re.search(r'teamsignnew_(\d+)\.png', card_content)
                            if home_logo_match:
                                home_team_id = home_logo_match.group(1)
                            
                            # 查找客队logo
                            away_logo_match = re.search(r'teamsignnew_(\d+)\.png', card_content, re.DOTALL)
                            if away_logo_match:
                                # 确保获取的是客队id，而不是主队id
                                logo_matches = re.findall(r'teamsignnew_(\d+)\.png', card_content)
                                if len(logo_matches) >= 2:
                                    away_team_id = logo_matches[1]
                                elif len(logo_matches) == 1:
                                    away_team_id = logo_matches[0]
                            
                            # 检查会话状态中是否已有该联赛数据
                            if f'league_data_{sid}' not in st.session_state:
                                with st.spinner(f'正在获取联赛{sid}的数据...'):
                                    league_data = get_league_data(sid)
                                    st.session_state[f'league_data_{sid}'] = league_data
                            else:
                                league_data = st.session_state[f'league_data_{sid}']
                            
                            # 显示联赛平均数据
                            if league_data['average_data']:
                                avg_data = league_data['average_data']
                                
                                # 使用columns创建两列布局，优化排版
                                col1, col2 = st.columns(2)
                                
                                # 第一列：赛果分布
                                with col1:
                                    st.markdown('### 赛果分布')
                                    result_dist = avg_data.get('result_distribution', {})
                                    if result_dist:
                                        # 为每个赛果创建独立的行
                                        result_html = '<div style="margin-bottom: 10px;">' + ''.join([f'<div style="margin: 4px 0;">{key}: <strong>{value}</strong>场</div>' for key, value in result_dist.items()]) + '</div>'
                                        st.html(result_html)
                                    else:
                                        st.info('暂无赛果分布数据')
                                
                                # 第二列：场均进球
                                with col2:
                                    st.markdown('### 场均进球')
                                    goal_html = '<div style="margin-bottom: 10px;">' 
                                    
                                    # 场均总进球
                                    total_goal = avg_data.get('total_average_goals')
                                    if total_goal:
                                        goal_html += f'<div style="margin: 4px 0;">总进球: <strong>{total_goal}</strong>个</div>'
                                    
                                    # 主场场均进球和客场场均进球
                                    home_away_goal = avg_data.get('home_away_average_goals', {})
                                    for key, value in home_away_goal.items():
                                        goal_html += f'<div style="margin: 4px 0;">{key}: <strong>{value}</strong>个</div>'
                                    

                                    
                                    goal_html += '</div>'
                                    
                                    if '暂无' not in goal_html:
                                        st.html(goal_html)
                                    else:
                                        st.info('暂无场均进球数据')
                                
                                # 删除分隔线
                            
                            # 显示联赛积分榜
                            if league_data['standings']:
                                st.subheader('联赛积分榜')
                                
                                # 创建更美观的积分榜表格
                                standings_html = """
                                <div style='overflow-x: auto;'>
                                    <table style='border-collapse: collapse; width: 100%; font-size: 14px; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
                                        <thead style='background-color: #f0f2f6;'>
                                            <tr>
                                                <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 60px;'>排名</th>
                                                <th style='padding: 12px 8px; text-align: left; border-bottom: 2px solid #e6e8eb;'>队伍</th>
                                                <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>赛</th>
                                                <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>胜</th>
                                                <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>平</th>
                                                <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>负</th>
                                                <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 60px;'>积分</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                """
                                
                                for i, team in enumerate(league_data['standings']):
                                    # 交替行背景色
                                    bg_color = '#ffffff' if i % 2 == 0 else '#fafbfc'
                                    
                                    # 检查当前球队是否为主队或客队
                                    team_id = None
                                    team_name = team['team']['name']
                                    
                                    # 从队伍链接中提取球队id
                                    if 'team/' in team['team']['link']:
                                        team_id_match = re.search(r'/team/(\d+)/', team['team']['link'])
                                        if team_id_match:
                                            team_id = team_id_match.group(1)
                                    
                                    # 设置球队标签
                                    team_label = ''
                                    team_style = 'color: #1f77b4;'
                                    
                                    if team_id:
                                        if team_id == home_team_id:
                                            team_label = ' 🟢主队'
                                            team_style = 'color: #28a745; font-weight: bold; background-color: #d4edda;'
                                        elif team_id == away_team_id:
                                            team_label = ' 🔴客队'
                                            team_style = 'color: #dc3545; font-weight: bold; background-color: #f8d7da;'
                                    
                                    standings_html += f"""
                                            <tr style='background-color: {bg_color}; transition: background-color 0.2s ease;'>
                                                <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; font-weight: bold;'>{team['rank']}</td>
                                                <td style='padding: 10px 8px; text-align: left; border-bottom: 1px solid #e6e8eb; {team_style}'>{team_name}{team_label}</td>
                                                <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{team['matches']}</td>
                                                <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; color: #28a745;'>{team['wins']}</td>
                                                <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; color: #ffc107;'>{team['draws']}</td>
                                                <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; color: #dc3545;'>{team['losses']}</td>
                                                <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; font-weight: bold; color: #17a2b8;'>{team['points']}</td>
                                            </tr>
                                    """
                                
                                standings_html += """
                                        </tbody>
                                    </table>
                                </div>
                                """
                                st.html(standings_html)
                            else:
                                st.markdown('暂无联赛数据')
                        
                        # 双方数据标签页
                        with tab4:
                            # 使用FID获取双方历史交战记录
                            fid = row['fid']
                            
                            # 检查会话状态中是否已有该比赛的历史数据
                            if f'history_data_{fid}' not in st.session_state:
                                with st.spinner(f'正在获取比赛{fid}的双方历史交战记录...'):
                                    try:
                                        history_data = fetch_match_history(fid)
                                        # 确保history_data不是None
                                        if history_data is None:
                                            # 返回一个空的历史数据结构
                                            history_data = {
                                                'match_info': '',
                                                'stats': '',
                                                'matches': [],
                                                'average_data': {},
                                                'pre_match_standings': {
                                                    'title': '',
                                                    'team_a': {'name': '', 'stats': {}},
                                                    'team_b': {'name': '', 'stats': {}}
                                                },
                                                'recent_records': {'home': [], 'away': []},
                                                'recent_records_all': [],
                                                'recent_records_home_away': {
                                                    'team_a_home': [],
                                                    'team_a_away': [],
                                                    'team_b_home': [],
                                                    'team_b_away': []
                                                }
                                            }
                                        st.session_state[f'history_data_{fid}'] = history_data
                                    except Exception as e:
                                        import traceback
                                        error_msg = f"获取历史数据失败: {str(e)}\n详细错误:\n{traceback.format_exc()}"
                                        st.error(error_msg)
                                        # 返回一个空的历史数据结构
                                        st.session_state[f'history_data_{fid}'] = {
                                            'match_info': '',
                                            'stats': '',
                                            'matches': [],
                                            'average_data': {},
                                            'pre_match_standings': {
                                                'title': '',
                                                'team_a': {'name': '', 'stats': {}},
                                                'team_b': {'name': '', 'stats': {}}
                                            },
                                            'recent_records': {'home': [], 'away': []}
                                        }
                            else:
                                history_data = st.session_state[f'history_data_{fid}']
                            
                            # 显示平均数据
                            average_data = history_data.get('average_data', {})
                            team_a = average_data.get('team_a', {})
                            team_b = average_data.get('team_b', {})
                            
                            # 检查是否有历史交战记录、平均数据、赛前积分排名或近期战绩
                            has_data = len(history_data['matches']) > 0 or (team_a.get('name') and team_b.get('name')) or history_data['pre_match_standings']['title'] or len(history_data.get('recent_records_all', [])) > 0 or bool(history_data.get('recent_records_home_away', {}))
                            
                            if has_data:
                                # 显示赛前联赛积分排名
                                pre_match = history_data['pre_match_standings']
                                if pre_match['title'] and pre_match['team_a']['name'] and pre_match['team_b']['name']:
                                    st.markdown(f'### {pre_match["title"]}')
                                    
                                    # 创建表格HTML
                                    standings_html = """
                                    <div style='overflow-x: auto;'>
                                        <table style='border-collapse: collapse; width: 100%; font-size: 14px; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
                                            <thead style='background-color: #f0f2f6;'>
                                                <tr>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 150px;'>球队</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 60px;'>比赛</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>胜</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>平</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>负</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>进</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>失</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 50px;'>净</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 60px;'>积分</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 60px;'>排名</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 70px;'>胜率</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                    """
                                    
                                    # 定义表格行生成函数
                                    def generate_standings_row(team, stats_type, bg_color):
                                        stats = team['stats'].get(stats_type, {})
                                        return f"""
                                                <tr style='background-color: {bg_color}; transition: background-color 0.2s ease;'>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; font-weight: bold;'>{stats_type}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{stats.get('比赛', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; color: #28a745;'>{stats.get('胜', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; color: #ffc107;'>{stats.get('平', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; color: #dc3545;'>{stats.get('负', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{stats.get('进', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{stats.get('失', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{stats.get('净', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb; font-weight: bold;'>{stats.get('积分', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{stats.get('排名', '')}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{stats.get('胜率', '')}</td>
                                                </tr>
                                        """
                                    
                                    # 主队数据
                                    standings_html += f"""
                                                <tr style='background-color: #e8f5e8; transition: background-color 0.2s ease;'>
                                                    <td style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; font-weight: bold; font-size: 16px; color: #28a745;' colspan='11'>{pre_match['team_a']['name']} [{pre_match['team_a']['rank']}]</td>
                                                </tr>
                                    """
                                    
                                    # 主队各类数据行
                                    standings_html += generate_standings_row(pre_match['team_a'], '总成绩', '#ffffff')
                                    standings_html += generate_standings_row(pre_match['team_a'], '主场', '#fafbfc')
                                    standings_html += generate_standings_row(pre_match['team_a'], '客场', '#ffffff')
                                    
                                    # 客队数据
                                    standings_html += f"""
                                                <tr style='background-color: #e3f2fd; transition: background-color 0.2s ease;'>
                                                    <td style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; font-weight: bold; font-size: 16px; color: #007bff;' colspan='11'>{pre_match['team_b']['name']} [{pre_match['team_b']['rank']}]</td>
                                                </tr>
                                    """
                                    
                                    # 客队各类数据行
                                    standings_html += generate_standings_row(pre_match['team_b'], '总成绩', '#ffffff')
                                    standings_html += generate_standings_row(pre_match['team_b'], '主场', '#fafbfc')
                                    standings_html += generate_standings_row(pre_match['team_b'], '客场', '#ffffff')
                                    
                                    # 关闭表格标签
                                    standings_html += """
                                            </tbody>
                                        </table>
                                    </div>
                                    """
                                    
                                    # 渲染表格
                                    st.html(standings_html)
                                    # 删除分隔线
                                
                                    # 显示历史比赛列表
                                if history_data['matches']:
                                    st.markdown('### 历史交战记录')
                                    
                                    # 计算历史交战记录统计指标的函数
                                    def calculate_headtohead_stats(matches, team_a_name, team_b_name):
                                        """根据历史交战记录计算统计数据"""
                                        total_matches = len(matches)
                                        
                                        if total_matches == 0:
                                            return 0, 0, 0, 0, 0, 0, 0, 0
                                        
                                        # 初始化统计数据
                                        team_a_wins = 0
                                        team_b_wins = 0
                                        draws = 0
                                        team_a_goals = 0
                                        team_b_goals = 0
                                        
                                        for match in matches:
                                            # 提取比分
                                            import re
                                            score_match = re.search(r'\s+(\d+):(\d+)\s+', match['teams'])
                                            if score_match:
                                                home_goals = int(score_match.group(1))
                                                away_goals = int(score_match.group(2))
                                                
                                                # 提取主队和客队名称
                                                teams_text = match['teams']
                                                score_text = score_match.group(0)
                                                home_team, away_team = teams_text.split(score_text, 1)
                                                home_team = home_team.strip()
                                                away_team = away_team.strip()
                                                
                                                # 更新进球数
                                                if home_team == team_a_name:
                                                    team_a_goals += home_goals
                                                    team_b_goals += away_goals
                                                elif home_team == team_b_name:
                                                    team_b_goals += home_goals
                                                    team_a_goals += away_goals
                                                
                                                # 计算胜负
                                                if home_goals > away_goals:
                                                    if home_team == team_a_name:
                                                        team_a_wins += 1
                                                    elif home_team == team_b_name:
                                                        team_b_wins += 1
                                                elif away_goals > home_goals:
                                                    if away_team == team_a_name:
                                                        team_a_wins += 1
                                                    elif away_team == team_b_name:
                                                        team_b_wins += 1
                                                else:
                                                    draws += 1
                                        
                                        # 计算胜率、平率
                                        team_a_win_rate = round(team_a_wins / total_matches * 100, 1)
                                        team_b_win_rate = round(team_b_wins / total_matches * 100, 1)
                                        draw_rate = round(draws / total_matches * 100, 1)
                                        
                                        # 计算平均进球数、平均失球数
                                        team_a_avg_goals = round(team_a_goals / total_matches, 2)
                                        team_a_avg_conceded = round(team_b_goals / total_matches, 2)
                                        team_b_avg_goals = round(team_b_goals / total_matches, 2)
                                        team_b_avg_conceded = round(team_a_goals / total_matches, 2)
                                        
                                        return team_a_win_rate, team_b_win_rate, draw_rate, team_a_avg_goals, team_a_avg_conceded, team_b_avg_goals, team_b_avg_conceded
                                    
                                    # 获取主队和客队名称
                                    team_a_name = pre_match['team_a']['name'] if pre_match.get('team_a') else ''
                                    team_b_name = pre_match['team_b']['name'] if pre_match.get('team_b') else ''
                                    
                                    # 计算历史交战记录统计指标
                                    team_a_win_rate, team_b_win_rate, draw_rate, team_a_avg_goals, team_a_avg_conceded, team_b_avg_goals, team_b_avg_conceded = calculate_headtohead_stats(history_data['matches'], team_a_name, team_b_name)
                                    
                                    # 显示历史交战记录统计信息
                                    if history_data['stats']:
                                        # 构建增强的统计信息
                                        enhanced_stats = f"{history_data['stats']}，{team_a_name}胜率<span style='color: #22c55e;'>{team_a_win_rate}%</span>，{team_b_name}胜率<span style='color: #22c55e;'>{team_b_win_rate}%</span>，平率<span style='color: #eab308;'>{draw_rate}%</span>，{team_a_name}均进<span style='color: #22c55e;'>{team_a_avg_goals}球</span>，{team_a_name}均失<span style='color: #ef4444;'>{team_a_avg_conceded}球</span>，{team_b_name}均进<span style='color: #22c55e;'>{team_b_avg_goals}球</span>，{team_b_name}均失<span style='color: #ef4444;'>{team_b_avg_conceded}球</span>"
                                        st.markdown(f'**{enhanced_stats}**', unsafe_allow_html=True)
                                        # 删除分隔线
                                    
                                    # 创建历史交战记录表格
                                    history_html = """
                                    <div style='overflow-x: auto;'>
                                        <table style='border-collapse: collapse; width: 100%; font-size: 14px; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
                                            <thead style='background-color: #f0f2f6;'>
                                                <tr>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 80px;'>赛事</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 100px;'>比赛日期</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 200px;'>对阵</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 60px;'>半场</th>
                                                    <th style='padding: 12px 8px; text-align: center; border-bottom: 2px solid #e6e8eb; width: 60px;'>赛果</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                    """
                                    
                                    for i, match in enumerate(history_data['matches']):
                                        # 交替行背景色
                                        bg_color = '#ffffff' if i % 2 == 0 else '#fafbfc'
                                        
                                        # 处理对阵信息，对全场比分进行特殊标识
                                        teams_text = match['teams']
                                        
                                        # 定义比分高亮函数
                                        def highlight_score(match_obj):
                                            score = match_obj.group(1)
                                            return f' <span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">{score}</span> '
                                        
                                        # 匹配比分模式，格式为：数字:数字，确保只匹配比分
                                        highlighted_teams = re.sub(r'(\d+:\d+)', highlight_score, teams_text)
                                        
                                        history_html += f"""
                                                <tr style='background-color: {bg_color}; transition: background-color 0.2s ease;'>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{match['league']}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{match['date']}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{highlighted_teams}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{match['half_score']}</td>
                                                    <td style='padding: 10px 8px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{match['result']}</td>
                                                </tr>
                                        """
                                    
                                    history_html += """
                                            </tbody>
                                        </table>
                                    </div>
                                    """
                                    st.html(history_html)
                                    # 删除分隔线
                                
                                # 显示平均数据
                                if team_a and team_b and team_a.get('name') and team_b.get('name'):
                                    # 检查是否有实际的平均数据
                                    has_avg_data = any([
                                        team_a.get('average_goals'), team_a.get('average_conceded'),
                                        team_b.get('average_goals'), team_b.get('average_conceded')
                                    ])
                                    
                                    if has_avg_data:
                                        st.markdown('### 平均数据')
                                        
                                        # 使用Streamlit原生组件显示平均数据
                                        col1, col2 = st.columns(2)
                                        
                                        # 主队数据
                                        with col1:
                                            st.markdown(f"#### {team_a.get('name', '')}")
                                            
                                            # 创建数据字典
                                            team_a_data = {
                                                '统计项': ['平均入球', '平均失球'],
                                                '总平均数': [team_a.get('average_goals', ''), team_a.get('average_conceded', '')],
                                                '主场': [team_a.get('average_goals_home', ''), team_a.get('average_conceded_home', '')],
                                                '客场': [team_a.get('average_goals_away', ''), team_a.get('average_conceded_away', '')]
                                            }
                                            
                                            # 显示表格，隐藏索引列
                                            st.dataframe(team_a_data, hide_index=True)
                                    
                                        # 客队数据
                                        with col2:
                                            st.markdown(f"#### {team_b.get('name', '')}")
                                            
                                            # 创建数据字典
                                            team_b_data = {
                                                '统计项': ['平均入球', '平均失球'],
                                                '总平均数': [team_b.get('average_goals', ''), team_b.get('average_conceded', '')],
                                                '主场': [team_b.get('average_goals_home', ''), team_b.get('average_conceded_home', '')],
                                                '客场': [team_b.get('average_goals_away', ''), team_b.get('average_conceded_away', '')]
                                            }
                                            
                                            # 显示表格，隐藏索引列
                                            st.dataframe(team_b_data, hide_index=True)
                                    
                                    # 显示近期战绩（不区分主客场）
                                    recent_records_all = history_data.get('recent_records_all', [])
                                    if recent_records_all:
                                        st.markdown('### 近期战绩（不区分主客场）')
                                        
                                        # 分离主队和客队的战绩
                                        home_records = [record for record in recent_records_all if record.get('team_type') == '主队']
                                        away_records = [record for record in recent_records_all if record.get('team_type') == '客队']
                                        
                                        # 创建一个两列布局
                                        col1, col2 = st.columns(2)
                                        
                                        # 定义一个函数来创建战绩表格
                                        def create_records_table(records, team_name):
                                            if not records:
                                                return f"<div style='text-align: center; padding: 20px;'>{team_name}暂无近期战绩数据</div>"
                                                
                                            table_html = """
                                            <div style='overflow-x: auto; margin-bottom: 15px;'>
                                                <table style='border-collapse: collapse; width: 100%; font-size: 12px; background-color: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.1);'>
                                                    <thead style='background-color: #f0f2f6;'>
                                                        <tr>
                                                            <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛事</th>
                                                            <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>日期</th>
                                                            <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>对阵</th>
                                                            <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>半场</th>
                                                            <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛果</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                            """
                                            
                                            for i, record in enumerate(records):
                                                # 交替行背景色
                                                bg_color = '#ffffff' if i % 2 == 0 else '#fafbfc'
                                                
                                                # 处理对阵信息，将比分标红
                                                teams_text = record['teams']
                                                colored_teams = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', teams_text)
                                                
                                                # 处理半场比分，将比分标红
                                                half_score_text = record['half_score']
                                                colored_half_score = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', half_score_text)
                                                
                                                table_html += f"""
                                                        <tr style='background-color: {bg_color};'>
                                                            <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['league']}</td>
                                                            <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['date']}</td>
                                                            <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_teams}</td>
                                                            <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_half_score}</td>
                                                            <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['result']}</td>
                                                        </tr>
                                                """
                                            
                                            table_html += """
                                                    </tbody>
                                                </table>
                                            </div>
                                            """
                                            return table_html
                                        
                                        # 计算主队近期战绩统计
                                        def calculate_record_stats(records, team_type):
                                            """根据近期战绩计算统计数据"""
                                            wins = 0
                                            draws = 0
                                            losses = 0
                                            goals_for = 0
                                            goals_against = 0
                                            
                                            for record in records:
                                                # 提取结果
                                                result = record['result']
                                                if result == '胜':
                                                    wins += 1
                                                elif result == '平':
                                                    draws += 1
                                                elif result == '负':
                                                    losses += 1
                                                
                                                # 提取比分
                                                import re
                                                score_match = re.search(r'(\d+):(\d+)', record['teams'])
                                                if score_match:
                                                    home_goals = int(score_match.group(1))
                                                    away_goals = int(score_match.group(2))
                                                    
                                                    # 判断是主队还是客队，调整进球统计
                                                    if team_type == 'home':
                                                        goals_for += home_goals
                                                        goals_against += away_goals
                                                    else:
                                                        goals_for += away_goals
                                                        goals_against += home_goals
                                            
                                            # 计算胜率、平率、负率
                                            total_matches = wins + draws + losses
                                            win_rate = round(wins / total_matches * 100, 1) if total_matches > 0 else 0
                                            draw_rate = round(draws / total_matches * 100, 1) if total_matches > 0 else 0
                                            loss_rate = round(losses / total_matches * 100, 1) if total_matches > 0 else 0
                                            
                                            # 计算平均进球数、平均失球数
                                            avg_goals_for = round(goals_for / total_matches, 2) if total_matches > 0 else 0
                                            avg_goals_against = round(goals_against / total_matches, 2) if total_matches > 0 else 0
                                            
                                            return wins, draws, losses, goals_for, goals_against, win_rate, draw_rate, loss_rate, avg_goals_for, avg_goals_against
                                        
                                        # 获取主队名称
                                        home_team_name = pre_match['team_a']['name'] if pre_match.get('team_a') else '主队'
                                        # 获取客队名称  
                                        away_team_name = pre_match['team_b']['name'] if pre_match.get('team_b') else '客队'
                                        
                                        # 计算主队统计
                                        home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_win_rate, home_draw_rate, home_loss_rate, home_avg_goals_for, home_avg_goals_against = calculate_record_stats(home_records, 'home')
                                        # 计算客队统计
                                        away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_win_rate, away_draw_rate, away_loss_rate, away_avg_goals_for, away_avg_goals_against = calculate_record_stats(away_records, 'away')
                                        
                                        # 在两列中分别显示主队和客队的战绩
                                        with col1:
                                            # 显示主队近期战绩 summary（计算得出）
                                            st.markdown(
                                                f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>近10场战绩<span style='margin-left: 20px;'><span style='color: #22c55e;'>{home_wins}胜</span><span style='color: #eab308; margin: 0 5px;'>{home_draws}平</span><span style='color: #ef4444;'>{home_losses}负</span></span><span style='margin-left: 20px;'>胜率<span style='color: #22c55e;'>{home_win_rate}%</span>平率<span style='color: #eab308; margin: 0 5px;'>{home_draw_rate}%</span>负率<span style='color: #ef4444;'>{home_loss_rate}%</span></span><span style='margin-left: 20px;'>进<span style='color: #22c55e;'>{home_goals_for}球</span>失<span style='color: #ef4444;'>{home_goals_against}球</span></span><span style='margin-left: 20px;'>场均进<span style='color: #22c55e;'>{home_avg_goals_for}球</span>场均失<span style='color: #ef4444;'>{home_avg_goals_against}球</span></span></p>",
                                                unsafe_allow_html=True
                                            )
                                            home_table = create_records_table(home_records, '主队')
                                            st.html(home_table)
                                        
                                        with col2:
                                            # 显示客队近期战绩 summary（计算得出）
                                            st.markdown(
                                                f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>近10场战绩<span style='margin-left: 20px;'><span style='color: #22c55e;'>{away_wins}胜</span><span style='color: #eab308; margin: 0 5px;'>{away_draws}平</span><span style='color: #ef4444;'>{away_losses}负</span></span><span style='margin-left: 20px;'>胜率<span style='color: #22c55e;'>{away_win_rate}%</span>平率<span style='color: #eab308; margin: 0 5px;'>{away_draw_rate}%</span>负率<span style='color: #ef4444;'>{away_loss_rate}%</span></span><span style='margin-left: 20px;'>进<span style='color: #22c55e;'>{away_goals_for}球</span>失<span style='color: #ef4444;'>{away_goals_against}球</span></span><span style='margin-left: 20px;'>场均进<span style='color: #22c55e;'>{away_avg_goals_for}球</span>场均失<span style='color: #ef4444;'>{away_avg_goals_against}球</span></span></p>",
                                                unsafe_allow_html=True
                                            )
                                            away_table = create_records_table(away_records, '客队')
                                            st.html(away_table)
                                    
                                    # 显示近期战绩（区分主客场）
                                    recent_records_home_away = history_data.get('recent_records_home_away', {})
                                    if recent_records_home_away:
                                        st.markdown('### 近期战绩（区分主客场）')
                                        
                                        # 战绩统计计算函数
                                        def calculate_record_stats(records, team_type):
                                            """根据近期战绩计算统计数据"""
                                            wins = 0
                                            draws = 0
                                            losses = 0
                                            goals_for = 0
                                            goals_against = 0
                                            
                                            for record in records:
                                                # 提取结果
                                                result = record['result']
                                                if result == '胜':
                                                    wins += 1
                                                elif result == '平':
                                                    draws += 1
                                                elif result == '负':
                                                    losses += 1
                                                
                                                # 提取比分
                                                import re
                                                score_match = re.search(r'(\d+):(\d+)', record['teams'])
                                                if score_match:
                                                    home_goals = int(score_match.group(1))
                                                    away_goals = int(score_match.group(2))
                                                    
                                                    # 判断是主队还是客队，调整进球统计
                                                    if team_type == 'home':
                                                        goals_for += home_goals
                                                        goals_against += away_goals
                                                    else:
                                                        goals_for += away_goals
                                                        goals_against += home_goals
                                            
                                            # 计算胜率、平率、负率
                                            total_matches = wins + draws + losses
                                            win_rate = round(wins / total_matches * 100, 1) if total_matches > 0 else 0
                                            draw_rate = round(draws / total_matches * 100, 1) if total_matches > 0 else 0
                                            loss_rate = round(losses / total_matches * 100, 1) if total_matches > 0 else 0
                                            
                                            # 计算平均进球数、平均失球数
                                            avg_goals_for = round(goals_for / total_matches, 2) if total_matches > 0 else 0
                                            avg_goals_against = round(goals_against / total_matches, 2) if total_matches > 0 else 0
                                            
                                            return wins, draws, losses, goals_for, goals_against, win_rate, draw_rate, loss_rate, avg_goals_for, avg_goals_against
                                        
                                        # 获取主队和客队名称
                                        home_team_name = pre_match['team_a']['name'] if pre_match.get('team_a') else '主队'
                                        away_team_name = pre_match['team_b']['name'] if pre_match.get('team_b') else '客队'
                                        
                                        # 创建一个两列布局
                                        col1, col2 = st.columns(2)
                                        
                                        # 主队主场和客场数据
                                        with col1:
                                            # 主队主场数据
                                            team_a_home = recent_records_home_away.get('team_a_home', [])
                                            if team_a_home:
                                                # 计算主场统计
                                                home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_win_rate, home_draw_rate, home_loss_rate, home_avg_goals_for, home_avg_goals_against = calculate_record_stats(team_a_home, 'home')
                                                # 显示主场战绩 summary
                                                st.markdown(
                                                    f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>近{len(team_a_home)}场主场战绩<span style='margin-left: 20px;'><span style='color: #22c55e;'>{home_wins}胜</span><span style='color: #eab308; margin: 0 5px;'>{home_draws}平</span><span style='color: #ef4444;'>{home_losses}负</span></span><span style='margin-left: 20px;'>胜率<span style='color: #22c55e;'>{home_win_rate}%</span>平率<span style='color: #eab308; margin: 0 5px;'>{home_draw_rate}%</span>负率<span style='color: #ef4444;'>{home_loss_rate}%</span></span><span style='margin-left: 20px;'>进<span style='color: #22c55e;'>{home_goals_for}球</span>失<span style='color: #ef4444;'>{home_goals_against}球</span></span><span style='margin-left: 20px;'>场均进<span style='color: #22c55e;'>{home_avg_goals_for}球</span>场均失<span style='color: #ef4444;'>{home_avg_goals_against}球</span></span></p>",
                                                    unsafe_allow_html=True
                                                )
                                                team_a_home_html = """
                                                <div style='overflow-x: auto; margin-bottom: 15px;'>
                                                    <table style='border-collapse: collapse; width: 100%; font-size: 12px; background-color: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.1);'>
                                                        <thead style='background-color: #f0f2f6;'>
                                                            <tr>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛事</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>日期</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>对阵</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>半场</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛果</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                """
                                                
                                                import re
                                                for i, record in enumerate(team_a_home):
                                                    bg_color = '#ffffff' if i % 2 == 0 else '#fafbfc'
                                                    
                                                    # 处理对阵信息，将比分标红
                                                    teams_text = record['teams']
                                                    colored_teams = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', teams_text)
                                                    
                                                    # 处理半场比分，将比分标红
                                                    half_score_text = record['half_score']
                                                    colored_half_score = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', half_score_text)
                                                    
                                                    team_a_home_html += f"""
                                                            <tr style='background-color: {bg_color};'>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['league']}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['date']}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_teams}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_half_score}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['result']}</td>
                                                            </tr>
                                                    """
                                                
                                                team_a_home_html += """
                                                        </tbody>
                                                    </table>
                                                </div>
                                                """
                                                st.html(team_a_home_html)
                                            
                                            # 主队客场数据
                                            team_a_away = recent_records_home_away.get('team_a_away', [])
                                            if team_a_away:
                                                # 计算客场统计
                                                away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_win_rate, away_draw_rate, away_loss_rate, away_avg_goals_for, away_avg_goals_against = calculate_record_stats(team_a_away, 'away')
                                                # 显示客场战绩 summary
                                                st.markdown(
                                                    f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>近{len(team_a_away)}场客场战绩<span style='margin-left: 20px;'><span style='color: #22c55e;'>{away_wins}胜</span><span style='color: #eab308; margin: 0 5px;'>{away_draws}平</span><span style='color: #ef4444;'>{away_losses}负</span></span><span style='margin-left: 20px;'>胜率<span style='color: #22c55e;'>{away_win_rate}%</span>平率<span style='color: #eab308; margin: 0 5px;'>{away_draw_rate}%</span>负率<span style='color: #ef4444;'>{away_loss_rate}%</span></span><span style='margin-left: 20px;'>进<span style='color: #22c55e;'>{away_goals_for}球</span>失<span style='color: #ef4444;'>{away_goals_against}球</span></span><span style='margin-left: 20px;'>场均进<span style='color: #22c55e;'>{away_avg_goals_for}球</span>场均失<span style='color: #ef4444;'>{away_avg_goals_against}球</span></span></p>",
                                                    unsafe_allow_html=True
                                                )
                                                team_a_away_html = """
                                                <div style='overflow-x: auto;'>
                                                    <table style='border-collapse: collapse; width: 100%; font-size: 12px; background-color: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.1);'>
                                                        <thead style='background-color: #f0f2f6;'>
                                                            <tr>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛事</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>日期</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>对阵</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>半场</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛果</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                """
                                                
                                                for i, record in enumerate(team_a_away):
                                                    bg_color = '#ffffff' if i % 2 == 0 else '#fafbfc'
                                                    
                                                    # 处理对阵信息，将比分标红
                                                    teams_text = record['teams']
                                                    colored_teams = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', teams_text)
                                                    
                                                    # 处理半场比分，将比分标红
                                                    half_score_text = record['half_score']
                                                    colored_half_score = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', half_score_text)
                                                    
                                                    team_a_away_html += f"""
                                                            <tr style='background-color: {bg_color};'>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['league']}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['date']}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_teams}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_half_score}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['result']}</td>
                                                            </tr>
                                                    """
                                                
                                                team_a_away_html += """
                                                        </tbody>
                                                    </table>
                                                </div>
                                                """
                                                st.html(team_a_away_html)
                                        
                                        # 客队主场和客场数据
                                        with col2:
                                            # 客队主场数据
                                            team_b_home = recent_records_home_away.get('team_b_home', [])
                                            if team_b_home:
                                                # 计算主场统计
                                                home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_win_rate, home_draw_rate, home_loss_rate, home_avg_goals_for, home_avg_goals_against = calculate_record_stats(team_b_home, 'home')
                                                # 显示主场战绩 summary
                                                st.markdown(
                                                    f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>近{len(team_b_home)}场主场战绩<span style='margin-left: 20px;'><span style='color: #22c55e;'>{home_wins}胜</span><span style='color: #eab308; margin: 0 5px;'>{home_draws}平</span><span style='color: #ef4444;'>{home_losses}负</span></span><span style='margin-left: 20px;'>胜率<span style='color: #22c55e;'>{home_win_rate}%</span>平率<span style='color: #eab308; margin: 0 5px;'>{home_draw_rate}%</span>负率<span style='color: #ef4444;'>{home_loss_rate}%</span></span><span style='margin-left: 20px;'>进<span style='color: #22c55e;'>{home_goals_for}球</span>失<span style='color: #ef4444;'>{home_goals_against}球</span></span><span style='margin-left: 20px;'>场均进<span style='color: #22c55e;'>{home_avg_goals_for}球</span>场均失<span style='color: #ef4444;'>{home_avg_goals_against}球</span></span></p>",
                                                    unsafe_allow_html=True
                                                )
                                                team_b_home_html = """
                                                <div style='overflow-x: auto; margin-bottom: 15px;'>
                                                    <table style='border-collapse: collapse; width: 100%; font-size: 12px; background-color: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.1);'>
                                                        <thead style='background-color: #f0f2f6;'>
                                                            <tr>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛事</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>日期</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>对阵</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>半场</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛果</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                """
                                                
                                                for i, record in enumerate(team_b_home):
                                                    bg_color = '#ffffff' if i % 2 == 0 else '#fafbfc'
                                                    
                                                    # 处理对阵信息，将比分标红
                                                    teams_text = record['teams']
                                                    colored_teams = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', teams_text)
                                                    
                                                    # 处理半场比分，将比分标红
                                                    half_score_text = record['half_score']
                                                    colored_half_score = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', half_score_text)
                                                    
                                                    team_b_home_html += f"""
                                                            <tr style='background-color: {bg_color};'>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['league']}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['date']}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_teams}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_half_score}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['result']}</td>
                                                            </tr>
                                                    """
                                                
                                                team_b_home_html += """
                                                        </tbody>
                                                    </table>
                                                </div>
                                                """
                                                st.html(team_b_home_html)
                                            
                                            # 客队客场数据
                                            team_b_away = recent_records_home_away.get('team_b_away', [])
                                            if team_b_away:
                                                # 计算客场统计
                                                away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_win_rate, away_draw_rate, away_loss_rate, away_avg_goals_for, away_avg_goals_against = calculate_record_stats(team_b_away, 'away')
                                                # 显示客场战绩 summary
                                                st.markdown(
                                                    f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>近{len(team_b_away)}场客场战绩<span style='margin-left: 20px;'><span style='color: #22c55e;'>{away_wins}胜</span><span style='color: #eab308; margin: 0 5px;'>{away_draws}平</span><span style='color: #ef4444;'>{away_losses}负</span></span><span style='margin-left: 20px;'>胜率<span style='color: #22c55e;'>{away_win_rate}%</span>平率<span style='color: #eab308; margin: 0 5px;'>{away_draw_rate}%</span>负率<span style='color: #ef4444;'>{away_loss_rate}%</span></span><span style='margin-left: 20px;'>进<span style='color: #22c55e;'>{away_goals_for}球</span>失<span style='color: #ef4444;'>{away_goals_against}球</span></span><span style='margin-left: 20px;'>场均进<span style='color: #22c55e;'>{away_avg_goals_for}球</span>场均失<span style='color: #ef4444;'>{away_avg_goals_against}球</span></span></p>",
                                                    unsafe_allow_html=True
                                                )
                                                team_b_away_html = """
                                                <div style='overflow-x: auto;'>
                                                    <table style='border-collapse: collapse; width: 100%; font-size: 12px; background-color: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.1);'>
                                                        <thead style='background-color: #f0f2f6;'>
                                                            <tr>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛事</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>日期</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>对阵</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>半场</th>
                                                                <th style='padding: 8px 4px; text-align: center; border-bottom: 2px solid #e6e8eb;'>赛果</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                """
                                                
                                                for i, record in enumerate(team_b_away):
                                                    bg_color = '#ffffff' if i % 2 == 0 else '#fafbfc'
                                                    
                                                    # 处理对阵信息，将比分标红
                                                    teams_text = record['teams']
                                                    colored_teams = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', teams_text)
                                                    
                                                    # 处理半场比分，将比分标红
                                                    half_score_text = record['half_score']
                                                    colored_half_score = re.sub(r'(\d+:\d+)', r'<span style="color: #ef4444; font-weight: bold; font-size: 1.1em;">\1</span>', half_score_text)
                                                    
                                                    team_b_away_html += f"""
                                                            <tr style='background-color: {bg_color};'>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['league']}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['date']}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_teams}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{colored_half_score}</td>
                                                                <td style='padding: 6px 4px; text-align: center; border-bottom: 1px solid #e6e8eb;'>{record['result']}</td>
                                                            </tr>
                                                    """
                                                
                                                team_b_away_html += """
                                                        </tbody>
                                                    </table>
                                                </div>
                                                """
                                                st.html(team_b_away_html)
                            else:
                                # 没有数据时显示友好提示
                                st.markdown('### 双方数据')
                                st.info('暂无该场比赛的相关数据')
                        
                        # 预测分析标签页
                        with tab5:
                            # st.markdown('### 预测分析')
                            
                            # 获取联赛数据用于预测分析
                            sid = row['sid']
                            
                            # 检查会话状态中是否已有该联赛数据
                            if f'league_data_{sid}' not in st.session_state:
                                with st.spinner(f'正在获取联赛{sid}的数据...'):
                                    league_data = get_league_data(sid)
                                    st.session_state[f'league_data_{sid}'] = league_data
                            else:
                                league_data = st.session_state[f'league_data_{sid}']
                            
                            # 显示联赛场均进球数据
                            # if league_data['average_data']:
                            #     avg_data = league_data['average_data']
                            #     
                            #     st.markdown('#### 联赛场均进球')
                            #     
                            #     # 构建场均进球HTML
                            #     goal_html = '<div style="margin-bottom: 10px;">'
                            #     
                            #     # 场均总进球
                            #     total_goal = avg_data.get('total_average_goals')
                            #     if total_goal:
                            #         goal_html += f'<div style="margin: 4px 0;">总进球: <strong>{total_goal}</strong>个</div>'
                            #     
                            #     # 主场场均进球和客场场均进球
                            #     home_away_goal = avg_data.get('home_away_average_goals', {})
                            #     for key, value in home_away_goal.items():
                            #         goal_html += f'<div style="margin: 4px 0;">{key}: <strong>{value}</strong>个</div>'
                            #     
                            #     goal_html += '</div>'
                            #     
                            #     if '暂无' not in goal_html:
                            #         st.html(goal_html)
                            #     else:
                            #         st.info('暂无场均进球数据')
                            
                            # 显示历史交战记录统计信息
                            # st.markdown('#### 历史交战记录')
                            
                            if history_data and 'stats' in history_data:
                                # 定义计算历史交战记录统计指标的函数
                                def calculate_headtohead_stats(matches, team_a_name, team_b_name):
                                    total_matches = len(matches)
                                    team_a_wins = 0
                                    team_b_wins = 0
                                    draws = 0
                                    team_a_goals = 0
                                    team_b_goals = 0
                                    
                                    # 记录进球数分布
                                    team_a_goals_dist = {x: 0 for x in range(6)}
                                    team_b_goals_dist = {x: 0 for x in range(6)}
                                    
                                    for match in matches:
                                        # 提取比分
                                        import re
                                        score_match = re.search(r'(\d+):(\d+)', match['teams'])
                                        if score_match:
                                            home_goals = int(score_match.group(1))
                                            away_goals = int(score_match.group(2))
                                            
                                            # 判断哪一方是主队
                                            if match['teams'].startswith(team_a_name):
                                                team_a_goals += home_goals
                                                team_b_goals += away_goals
                                                
                                                # 更新进球数分布（限制在0-5球）
                                                team_a_goals_dist[min(home_goals, 5)] += 1
                                                team_b_goals_dist[min(away_goals, 5)] += 1
                                                
                                                if home_goals > away_goals:
                                                    team_a_wins += 1
                                                elif away_goals > home_goals:
                                                    team_b_wins += 1
                                                else:
                                                    draws += 1
                                            elif match['teams'].startswith(team_b_name):
                                                team_a_goals += away_goals
                                                team_b_goals += home_goals
                                                
                                                # 更新进球数分布（限制在0-5球）
                                                team_a_goals_dist[min(away_goals, 5)] += 1
                                                team_b_goals_dist[min(home_goals, 5)] += 1
                                                
                                                if away_goals > home_goals:
                                                    team_a_wins += 1
                                                elif home_goals > away_goals:
                                                    team_b_wins += 1
                                                else:
                                                    draws += 1
                                    
                                    # 计算胜率、平率
                                    team_a_win_rate = round(team_a_wins / total_matches * 100, 1) if total_matches > 0 else 0
                                    team_b_win_rate = round(team_b_wins / total_matches * 100, 1) if total_matches > 0 else 0
                                    draw_rate = round(draws / total_matches * 100, 1) if total_matches > 0 else 0
                                    
                                    # 计算平均进球数、平均失球数
                                    team_a_avg_goals = round(team_a_goals / total_matches, 2) if total_matches > 0 else 0
                                    team_a_avg_conceded = round(team_b_goals / total_matches, 2) if total_matches > 0 else 0
                                    team_b_avg_goals = round(team_b_goals / total_matches, 2) if total_matches > 0 else 0
                                    team_b_avg_conceded = round(team_a_goals / total_matches, 2) if total_matches > 0 else 0
                                    
                                    # 计算进球数分布的概率
                                    team_a_goals_prob = {x: count / total_matches if total_matches > 0 else 0 for x, count in team_a_goals_dist.items()}
                                    team_b_goals_prob = {x: count / total_matches if total_matches > 0 else 0 for x, count in team_b_goals_dist.items()}
                                    
                                    return team_a_win_rate, team_b_win_rate, draw_rate, team_a_avg_goals, team_a_avg_conceded, team_b_avg_goals, team_b_avg_conceded, team_a_goals_prob, team_b_goals_prob
                                
                                # 获取主队和客队名称
                                team_a_name = pre_match['team_a']['name'] if pre_match.get('team_a') else ''
                                team_b_name = pre_match['team_b']['name'] if pre_match.get('team_b') else ''
                                
                                # 计算历史交战记录统计指标
                                team_a_win_rate, team_b_win_rate, draw_rate, team_a_avg_goals, team_a_avg_conceded, team_b_avg_goals, team_b_avg_conceded, team_a_h2h_goals_prob, team_b_h2h_goals_prob = calculate_headtohead_stats(history_data['matches'], team_a_name, team_b_name)
                                
                                # 显示历史交战记录统计信息
                                # if history_data['stats']:
                                #     # 构建增强的统计信息
                                #     enhanced_stats = f"{history_data['stats']}，{team_a_name}胜率<span style='color: #22c55e;'>{team_a_win_rate}%</span>，{team_b_name}胜率<span style='color: #22c55e;'>{team_b_win_rate}%</span>，平率<span style='color: #eab308;'>{draw_rate}%</span>，{team_a_name}均进<span style='color: #22c55e;'>{team_a_avg_goals}球</span>，{team_a_name}均失<span style='color: #ef4444;'>{team_a_avg_conceded}球</span>，{team_b_name}均进<span style='color: #22c55e;'>{team_b_avg_goals}球</span>，{team_b_name}均失<span style='color: #ef4444;'>{team_b_avg_conceded}球</span>"
                                #     st.markdown(f'<p><strong>{enhanced_stats}</strong></p>', unsafe_allow_html=True)
                            # else:
                            #     st.info('暂无历史交战记录数据')
                            
                            # 其他预测分析内容可以在这里继续添加
                            # 显示近期战绩（不区分主客场）
                            # st.markdown('#### 近期战绩（不区分主客场）')
                            
                            # 获取比赛的fid（固定比赛ID）
                            fid = row['fid']
                            
                            # 检查是否已经缓存了该比赛的历史数据
                            if f'history_data_{fid}' not in st.session_state:
                                # 如果没有缓存，使用fetch_match_history函数获取数据
                                with st.spinner(f'正在获取比赛{fid}的历史数据...'):
                                    try:
                                        # 获取比赛历史数据
                                        history_data = fetch_match_history(fid)
                                        st.session_state[f'history_data_{fid}'] = history_data
                                    except Exception as e:
                                        st.error(f'获取历史数据失败: {e}')
                                        history_data = None
                            else:
                                # 如果已经缓存，直接从session_state获取
                                history_data = st.session_state[f'history_data_{fid}']
                            
                            # 显示近期战绩（不区分主客场）的数据
                            if history_data and 'recent_records_all' in history_data:
                                recent_records_all = history_data['recent_records_all']
                                
                                # 分离主队和客队的战绩
                                home_records = [record for record in recent_records_all if record.get('team_type') == '主队']
                                away_records = [record for record in recent_records_all if record.get('team_type') == '客队']
                                
                                # 创建一个两列布局
                                col1, col2 = st.columns(2)
                                
                                # 战绩统计计算函数
                                def calculate_record_stats(records, team_type):
                                    """根据近期战绩计算统计数据"""
                                    wins = 0
                                    draws = 0
                                    losses = 0
                                    goals_for = 0
                                    goals_against = 0
                                    
                                    for record in records:
                                        # 提取结果
                                        result = record['result']
                                        if result == '胜':
                                            wins += 1
                                        elif result == '平':
                                            draws += 1
                                        elif result == '负':
                                            losses += 1
                                        
                                        # 提取比分
                                        import re
                                        score_match = re.search(r'(\d+):(\d+)', record['teams'])
                                        if score_match:
                                            home_goals = int(score_match.group(1))
                                            away_goals = int(score_match.group(2))
                                            
                                            # 判断是主队还是客队，调整进球统计
                                            if team_type == 'home':
                                                goals_for += home_goals
                                                goals_against += away_goals
                                            else:
                                                goals_for += away_goals
                                                goals_against += home_goals
                                    
                                    # 计算胜率、平率、负率
                                    total_matches = wins + draws + losses
                                    win_rate = round(wins / total_matches * 100, 1) if total_matches > 0 else 0
                                    draw_rate = round(draws / total_matches * 100, 1) if total_matches > 0 else 0
                                    loss_rate = round(losses / total_matches * 100, 1) if total_matches > 0 else 0
                                    
                                    # 计算平均进球数、平均失球数
                                    avg_goals_for = round(goals_for / total_matches, 2) if total_matches > 0 else 0
                                    avg_goals_against = round(goals_against / total_matches, 2) if total_matches > 0 else 0
                                    
                                    return wins, draws, losses, goals_for, goals_against, win_rate, draw_rate, loss_rate, avg_goals_for, avg_goals_against
                                
                                # 获取主队名称
                                home_team_name = pre_match['team_a']['name'] if pre_match.get('team_a') else '主队'
                                # 获取客队名称  
                                away_team_name = pre_match['team_b']['name'] if pre_match.get('team_b') else '客队'
                                
                                # 计算主队统计
                                home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_win_rate, home_draw_rate, home_loss_rate, home_avg_goals_for, home_avg_goals_against = calculate_record_stats(home_records, 'home')
                                # 计算客队统计
                                away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_win_rate, away_draw_rate, away_loss_rate, away_avg_goals_for, away_avg_goals_against = calculate_record_stats(away_records, 'away')
                                
                                # 在两列中分别显示主队和客队的战绩
                                # with col1:
                                #     # 显示主队近期战绩 summary（计算得出）
                                #     st.markdown(
                                #         f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>近10场战绩<span style='margin-left: 20px;'><span style='color: #22c55e;'>{home_wins}胜</span><span style='color: #eab308; margin: 0 5px;'>{home_draws}平</span><span style='color: #ef4444;'>{home_losses}负</span></span><span style='margin-left: 20px;'>胜率<span style='color: #22c55e;'>{home_win_rate}%</span>平率<span style='color: #eab308; margin: 0 5px;'>{home_draw_rate}%</span>负率<span style='color: #ef4444;'>{home_loss_rate}%</span></span><span style='margin-left: 20px;'>进<span style='color: #22c55e;'>{home_goals_for}球</span>失<span style='color: #ef4444;'>{home_goals_against}球</span></span><span style='margin-left: 20px;'>场均进<span style='color: #22c55e;'>{home_avg_goals_for}球</span>场均失<span style='color: #ef4444;'>{home_avg_goals_against}球</span></span></p>",
                                #         unsafe_allow_html=True
                                #     )
                                # 
                                # with col2:
                                #     # 显示客队近期战绩 summary（计算得出）
                                #     st.markdown(
                                #         f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>近10场战绩<span style='margin-left: 20px;'><span style='color: #22c55e;'>{away_wins}胜</span><span style='color: #eab308; margin: 0 5px;'>{away_draws}平</span><span style='color: #ef4444;'>{away_losses}负</span></span><span style='margin-left: 20px;'>胜率<span style='color: #22c55e;'>{away_win_rate}%</span>平率<span style='color: #eab308; margin: 0 5px;'>{away_draw_rate}%</span>负率<span style='color: #ef4444;'>{away_loss_rate}%</span></span><span style='margin-left: 20px;'>进<span style='color: #22c55e;'>{away_goals_for}球</span>失<span style='color: #ef4444;'>{away_goals_against}球</span></span><span style='margin-left: 20px;'>场均进<span style='color: #22c55e;'>{away_avg_goals_for}球</span>场均失<span style='color: #ef4444;'>{away_avg_goals_against}球</span></span></p>",
                                #         unsafe_allow_html=True
                                #     )
                            # else:
                            #     st.info('暂无近期战绩数据')
                            
                            # 显示平均数据
                            # st.markdown('#### 平均数据')
                            
                            # 从history_data中获取平均数据
                            # if history_data and 'average_data' in history_data:
                            #     average_data = history_data['average_data']
                            #     team_a = average_data.get('team_a', {})
                            #     team_b = average_data.get('team_b', {})
                            #     
                            #     # 检查是否有实际的平均数据
                            #     has_avg_data = any([
                            #         team_a.get('average_goals'), team_a.get('average_conceded'),
                            #         team_b.get('average_goals'), team_b.get('average_conceded')
                            #     ])
                            #     
                            #     if has_avg_data:
                            #         # 使用Streamlit原生组件显示平均数据
                            #         col1, col2 = st.columns(2)
                            #         
                            #         # 主队数据
                            #         with col1:
                            #             st.markdown(f"#### {team_a.get('name', '')}")
                            #             
                            #             # 创建数据字典
                            #             team_a_data = {
                            #                 '统计项': ['平均入球', '平均失球'],
                            #                 '总平均数': [team_a.get('average_goals', ''), team_a.get('average_conceded', '')],
                            #                 '主场': [team_a.get('average_goals_home', ''), team_a.get('average_conceded_home', '')],
                            #                 '客场': [team_a.get('average_goals_away', ''), team_a.get('average_conceded_away', '')]
                            #             }
                            #             
                            #             # 显示表格，隐藏索引列
                            #             st.dataframe(team_a_data, hide_index=True)
                            #     
                            #         # 客队数据
                            #         with col2:
                            #             st.markdown(f"#### {team_b.get('name', '')}")
                            #             
                            #             # 创建数据字典
                            #             team_b_data = {
                            #                 '统计项': ['平均入球', '平均失球'],
                            #                 '总平均数': [team_b.get('average_goals', ''), team_b.get('average_conceded', '')],
                            #                 '主场': [team_b.get('average_goals_home', ''), team_b.get('average_conceded_home', '')],
                            #                 '客场': [team_b.get('average_goals_away', ''), team_b.get('average_conceded_away', '')]
                            #             }
                            #             
                            #             # 显示表格，隐藏索引列
                            #             st.dataframe(team_b_data, hide_index=True)
                            #     else:
                            #         st.info('暂无平均数据')
                            # else:
                            #     st.info('暂无平均数据')
                            
                            # 显示主客队近期战绩（区分主客场）的场均进球和场均失球
                            # st.markdown('#### 主客队场均进球与失球（区分主客场）')
                            
                            # 从history_data中提取近期战绩（区分主客场）数据
                            # if history_data and 'recent_records_home_away' in history_data:
                            #     recent_records_home_away = history_data['recent_records_home_away']
                            #     
                            #     # 获取主队和客队名称
                            #     home_team_name = pre_match['team_a']['name'] if pre_match.get('team_a') else '主队'
                            #     away_team_name = pre_match['team_b']['name'] if pre_match.get('team_b') else '客队'
                            #     
                            #     # 战绩统计计算函数（与tab4中相同）
                            #     def calculate_record_stats(records, team_type):
                            #         """根据近期战绩计算统计数据"""
                            #         wins = 0
                            #         draws = 0
                            #         losses = 0
                            #         goals_for = 0
                            #         goals_against = 0
                            #         
                            #         for record in records:
                            #             # 提取结果
                            #             result = record['result']
                            #             if result == '胜':
                            #                 wins += 1
                            #             elif result == '平':
                            #                 draws += 1
                            #             elif result == '负':
                            #                 losses += 1
                            #             
                            #             # 提取比分
                            #             import re
                            #             score_match = re.search(r'(\d+):(\d+)', record['teams'])
                            #             if score_match:
                            #                 home_goals = int(score_match.group(1))
                            #                 away_goals = int(score_match.group(2))
                            #                 
                            #                 # 判断是主队还是客队，调整进球统计
                            #                 if team_type == 'home':
                            #                     goals_for += home_goals
                            #                     goals_against += away_goals
                            #                 else:
                            #                     goals_for += away_goals
                            #                     goals_against += home_goals
                            #         
                            #         # 计算胜率、平率、负率
                            #         total_matches = wins + draws + losses
                            #         win_rate = round(wins / total_matches * 100, 1) if total_matches > 0 else 0
                            #         draw_rate = round(draws / total_matches * 100, 1) if total_matches > 0 else 0
                            #         loss_rate = round(losses / total_matches * 100, 1) if total_matches > 0 else 0
                            #         
                            #         # 计算平均进球数、平均失球数
                            #         avg_goals_for = round(goals_for / total_matches, 2) if total_matches > 0 else 0
                            #         avg_goals_against = round(goals_against / total_matches, 2) if total_matches > 0 else 0
                            #         
                            #         return wins, draws, losses, goals_for, goals_against, win_rate, draw_rate, loss_rate, avg_goals_for, avg_goals_against
                            #     
                            #     # 创建一个两列布局
                            #     col1, col2 = st.columns(2)
                            #     
                            #     # 主队主场和客场数据
                            #     with col1:
                            #         # 主队主场数据
                            #         team_a_home = recent_records_home_away.get('team_a_home', [])
                            #         if team_a_home:
                            #             # 计算主场统计
                            #             home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_win_rate, home_draw_rate, home_loss_rate, home_avg_goals_for, home_avg_goals_against = calculate_record_stats(team_a_home, 'home')
                            #             # 显示主场场均进球和场均失球
                            #             st.markdown(
                            #                 f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>近{len(team_a_home)}场主场场均进<span style='color: #22c55e; margin-left: 10px;'>{home_avg_goals_for}球</span>场均失<span style='color: #ef4444; margin-left: 10px;'>{home_avg_goals_against}球</span></p>",
                            #                 unsafe_allow_html=True
                            #             )
                            #         
                            #         # 主队客场数据
                            #         team_a_away = recent_records_home_away.get('team_a_away', [])
                            #         if team_a_away:
                            #             # 计算客场统计
                            #             away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_win_rate, away_draw_rate, away_loss_rate, away_avg_goals_for, away_avg_goals_against = calculate_record_stats(team_a_away, 'away')
                            #             # 显示客场场均进球和场均失球
                            #             st.markdown(
                            #                 f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>近{len(team_a_away)}场客场场均进<span style='color: #22c55e; margin-left: 10px;'>{away_avg_goals_for}球</span>场均失<span style='color: #ef4444; margin-left: 10px;'>{away_avg_goals_against}球</span></p>",
                            #                 unsafe_allow_html=True
                            #             )
                            #     
                            #     # 客队主场和客场数据
                            #     with col2:
                            #         # 客队主场数据
                            #         team_b_home = recent_records_home_away.get('team_b_home', [])
                            #         if team_b_home:
                            #             # 计算主场统计
                            #             home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_win_rate, home_draw_rate, home_loss_rate, home_avg_goals_for, home_avg_goals_against = calculate_record_stats(team_b_home, 'home')
                            #             # 显示主场场均进球和场均失球
                            #             st.markdown(
                            #                 f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>近{len(team_b_home)}场主场场均进<span style='color: #22c55e; margin-left: 10px;'>{home_avg_goals_for}球</span>场均失<span style='color: #ef4444; margin-left: 10px;'>{home_avg_goals_against}球</span></p>",
                            #                 unsafe_allow_html=True
                            #             )
                            #         
                            #         # 客队客场数据
                            #         team_b_away = recent_records_home_away.get('team_b_away', [])
                            #         if team_b_away:
                            #             # 计算客场统计
                            #             away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_win_rate, away_draw_rate, away_loss_rate, away_avg_goals_for, away_avg_goals_against = calculate_record_stats(team_b_away, 'away')
                            #             # 显示客场场均进球和场均失球
                            #             st.markdown(
                            #                 f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>近{len(team_b_away)}场客场场均进<span style='color: #22c55e; margin-left: 10px;'>{away_avg_goals_for}球</span>场均失<span style='color: #ef4444; margin-left: 10px;'>{away_avg_goals_against}球</span></p>",
                            #                 unsafe_allow_html=True
                            #             )
                            # else:
                            #     st.info('暂无主客队历史战绩数据')
                            
                            # 显示主客队进攻力和防守力参数
                            # st.markdown('#### 主客队进攻力与防守力参数')
                            
                            # 获取联赛主场和客场场均进球数
                            league_home_avg_goals = 0
                            league_away_avg_goals = 0
                            if league_data['average_data']:
                                home_away_goal = league_data['average_data'].get('home_away_average_goals', {})
                                # 提取联赛主场场均进球数
                                for key, value in home_away_goal.items():
                                    if '主场' in key:
                                        league_home_avg_goals = float(value) if value and value != '暂无' else 0
                                    elif '客场' in key:
                                        league_away_avg_goals = float(value) if value and value != '暂无' else 0
                            
                            # 计算主客队进攻力和防守力参数
                            if history_data and 'recent_records_home_away' in history_data:
                                recent_records_home_away = history_data['recent_records_home_away']
                                
                                # 创建一个两列布局
                                col1, col2 = st.columns(2)
                                
                                # 初始化所有参数为0
                                home_attack_param = 0
                                home_defense_param = 0
                                away_attack_param = 0
                                away_defense_param = 0
                                
                                # 主队数据
                                team_a_home = recent_records_home_away.get('team_a_home', [])
                                team_a_away = recent_records_home_away.get('team_a_away', [])
                                
                                # 计算主队进攻力参数（主队近几场场均进球数/联赛主场场均进球数）
                                if team_a_home and league_home_avg_goals > 0:
                                    # 使用主队主场数据计算场均进球
                                    home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_win_rate, home_draw_rate, home_loss_rate, home_avg_goals_for, home_avg_goals_against = calculate_record_stats(team_a_home, 'home')
                                    home_attack_param = round(home_avg_goals_for / league_home_avg_goals, 2)
                                
                                # 计算主队防守力参数（主队近几场场均失球数/联赛客场场均进球数）
                                if team_a_home and league_away_avg_goals > 0:
                                    # 使用主队主场数据计算场均失球
                                    home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_win_rate, home_draw_rate, home_loss_rate, home_avg_goals_for, home_avg_goals_against = calculate_record_stats(team_a_home, 'home')
                                    home_defense_param = round(home_avg_goals_against / league_away_avg_goals, 2)
                                
                                # 客队数据
                                team_b_home = recent_records_home_away.get('team_b_home', [])
                                team_b_away = recent_records_home_away.get('team_b_away', [])
                                
                                # 计算客队进攻力参数（客队近几场场均进球数/联赛客场场均进球数）
                                if team_b_away and league_away_avg_goals > 0:
                                    # 使用客队客场数据计算场均进球
                                    b_away_wins, b_away_draws, b_away_losses, b_away_goals_for, b_away_goals_against, b_away_win_rate, b_away_draw_rate, b_away_loss_rate, b_away_avg_goals_for, b_away_avg_goals_against = calculate_record_stats(team_b_away, 'away')
                                    away_attack_param = round(b_away_avg_goals_for / league_away_avg_goals, 2)
                                
                                # 计算客队防守力参数（客队客场场均失球数/联赛主场场均进球数）
                                if team_b_away and league_home_avg_goals > 0:
                                    # 使用客队客场数据计算场均失球
                                    b_away_wins, b_away_draws, b_away_losses, b_away_goals_for, b_away_goals_against, b_away_win_rate, b_away_draw_rate, b_away_loss_rate, b_away_avg_goals_for, b_away_avg_goals_against = calculate_record_stats(team_b_away, 'away')
                                    away_defense_param = round(b_away_avg_goals_against / league_home_avg_goals, 2)
                                
                                # 在两列中分别显示主客队的进攻力和防守力参数
                                # with col1:
                                #     st.markdown(f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>进攻力参数：<span style='color: #22c55e; margin-left: 10px;'>{home_attack_param}</span></p>", unsafe_allow_html=True)
                                #     st.markdown(f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>防守力参数：<span style='color: #ef4444; margin-left: 10px;'>{home_defense_param}</span></p>", unsafe_allow_html=True)
                                # 
                                # with col2:
                                #     st.markdown(f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>进攻力参数：<span style='color: #22c55e; margin-left: 10px;'>{away_attack_param}</span></p>", unsafe_allow_html=True)
                                #     st.markdown(f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>防守力参数：<span style='color: #ef4444; margin-left: 10px;'>{away_defense_param}</span></p>", unsafe_allow_html=True)
                                
                                # 计算主队xG：主队进攻力参数 * 客队防守力参数 * 联赛主场场均进球数
                                home_xg = round(home_attack_param * away_defense_param * league_home_avg_goals, 2)
                                
                                # 计算客队xG：客队进攻力参数 * 主队防守力参数 * 联赛客场场均进球数
                                away_xg = round(away_attack_param * home_defense_param * league_away_avg_goals, 2)
                                
                                # 贝叶斯修正xG
                                def bayesian_xg_correction(original_xg, h2h_avg_goals, h2h_avg_conceded, h2h_win_rate, h2h_draw_rate, h2h_matches, league_avg_goals, h2h_goals_prob, 
                                                         recent_home_win_rate, recent_home_avg_goals, recent_home_avg_conceded, 
                                                         recent_away_win_rate, recent_away_avg_goals, recent_away_avg_conceded,
                                                         is_home_team=True):
                                    """
                                    使用贝叶斯方法修正预期进球数
                                    original_xg: 原始计算的预期进球数
                                    h2h_avg_goals: 历史交战记录中的平均进球数
                                    h2h_avg_conceded: 历史交战记录中的平均失球数
                                    h2h_win_rate: 历史交战记录中的胜率
                                    h2h_draw_rate: 历史交战记录中的平局率
                                    h2h_matches: 历史交战记录的场次
                                    league_avg_goals: 联赛平均进球数（先验的基准值）
                                    h2h_goals_prob: 历史交战记录中的进球数分布概率
                                    recent_home_win_rate: 主队近期胜率
                                    recent_home_avg_goals: 主队近期场均进球
                                    recent_home_avg_conceded: 主队近期场均失球
                                    recent_away_win_rate: 客队近期胜率
                                    recent_away_avg_goals: 客队近期场均进球
                                    recent_away_avg_conceded: 客队近期场均失球
                                    is_home_team: 是否为主队
                                    返回：修正后的预期进球数
                                    """
                                    # 如果没有历史交战记录，返回原始xG
                                    if h2h_matches == 0:
                                        # 即使没有历史交战记录，也使用近期战绩进行修正
                                        corrected_xg = original_xg
                                    else:
                                        # 计算权重：历史交战记录的权重基于场次，最多占50%
                                        # 这样可以避免小样本的历史数据过度影响预测
                                        h2h_weight = min(0.5, h2h_matches / 10)  # 最多50%权重，10场以上就达到最大权重
                                        prior_weight = 1 - h2h_weight
                                        
                                        # 先验分布：使用联赛平均进球数和原始xG的加权平均作为先验
                                        prior = prior_weight * league_avg_goals + (1 - prior_weight) * original_xg
                                        
                                        # 计算额外的修正因子：全面考虑胜平负率、进球数、丢球数等历史数据
                                        
                                        # 1. 胜率因子：胜率越高，球队的进攻能力可能越强
                                        win_rate_factor = 1.0 + (h2h_win_rate / 100) * 0.3  # 胜率每增加10%，进攻能力提升3%
                                        
                                        # 2. 平局率因子：平局率反映了比赛的防守强度
                                        # 平局率越高，比赛可能越保守，进球数可能越少
                                        draw_factor = 1.0 - (h2h_draw_rate / 100) * 0.1  # 平局率每增加10%，进球预期减少1%
                                        
                                        # 3. 对手防守因子：基于对手平均失球数
                                        # 对手失球越多，说明其防守越弱，我方进球机会越多
                                        opponent_defense_factor = h2h_avg_conceded / league_avg_goals
                                        
                                        # 4. 进球数分布因子：基于历史进球数分布的集中度
                                        # 计算进球数分布的熵，熵越小说明分布越集中
                                        import math
                                        entropy = -sum(p * math.log(p) if p > 0 else 0 for p in h2h_goals_prob.values())
                                        distribution_factor = 1.0 + (1 - entropy / 2.5) * 0.1  # 熵越小，因子越大（最多增加10%）
                                        
                                        # 结合所有因子计算修正后的历史交战平均进球数
                                        adjusted_h2h_goals = h2h_avg_goals * win_rate_factor * draw_factor * opponent_defense_factor * distribution_factor
                                        
                                        # 5. 额外考虑历史平均进球数与原始xG的差异
                                        # 如果历史平均进球数与原始xG差异很大，适当调整权重
                                        difference_factor = 1.0 - abs(h2h_avg_goals - original_xg) * 0.1  # 差异越大，权重略微降低
                                        adjusted_h2h_weight = h2h_weight * difference_factor
                                        adjusted_prior_weight = 1 - adjusted_h2h_weight
                                        
                                        # 后验分布：结合先验和调整后的历史交战记录数据
                                        corrected_xg = adjusted_prior_weight * prior + adjusted_h2h_weight * adjusted_h2h_goals
                                    
                                    # 二次深度修正：结合近期战绩进行修正
                                    # 1. 获取当前球队和对手的近期数据
                                    if is_home_team:
                                        team_recent_win_rate = recent_home_win_rate
                                        team_recent_avg_goals = recent_home_avg_goals
                                        opponent_recent_avg_conceded = recent_away_avg_conceded
                                    else:
                                        team_recent_win_rate = recent_away_win_rate
                                        team_recent_avg_goals = recent_away_avg_goals
                                        opponent_recent_avg_conceded = recent_home_avg_conceded
                                    
                                    # 2. 近期战绩修正因子
                                    # 近期胜率因子：近期表现越好，进攻能力越强
                                    recent_win_factor = 1.0 + (team_recent_win_rate / 100) * 0.4  # 近期胜率每增加10%，进攻能力提升4%
                                    
                                    # 3. 近期进球效率因子：近期进球越多，进攻状态越好
                                    recent_goals_factor = team_recent_avg_goals / league_avg_goals if league_avg_goals > 0 else 1.0
                                    
                                    # 4. 近期对手防守因子：对手近期失球越多，防守越弱
                                    recent_opponent_defense_factor = opponent_recent_avg_conceded / league_avg_goals if league_avg_goals > 0 else 1.0
                                    
                                    # 5. 综合近期战绩修正系数
                                    recent_performance_factor = recent_win_factor * recent_goals_factor * recent_opponent_defense_factor
                                    
                                    # 6. 应用近期战绩修正，给予20%的权重
                                    final_corrected_xg = corrected_xg * 0.8 + corrected_xg * recent_performance_factor * 0.2
                                    
                                    # 确保修正后的xG在合理范围内（0到5之间）
                                    final_corrected_xg = max(0, min(5, final_corrected_xg))
                                    
                                    return round(final_corrected_xg, 2)
                                
                                # 获取历史交战记录的场次
                                h2h_matches = len(history_data['matches']) if history_data else 0
                                
                                # 获取近期战绩数据（不区分主客场）并计算统计值
                                # 默认值设置
                                recent_home_win_rate = 0
                                recent_home_avg_goals = 0
                                recent_home_avg_conceded = 0
                                recent_away_win_rate = 0
                                recent_away_avg_goals = 0
                                recent_away_avg_conceded = 0
                                
                                if history_data and 'recent_records_all' in history_data:
                                    recent_records_all = history_data['recent_records_all']
                                    
                                    # 分离主队和客队的战绩
                                    home_records = [record for record in recent_records_all if record.get('team_type') == '主队']
                                    away_records = [record for record in recent_records_all if record.get('team_type') == '客队']
                                    
                                    # 战绩统计计算函数
                                    def calculate_record_stats(records, team_type):
                                        """根据近期战绩计算统计数据"""
                                        wins = 0
                                        draws = 0
                                        losses = 0
                                        goals_for = 0
                                        goals_against = 0
                                        
                                        for record in records:
                                            # 提取结果
                                            result = record['result']
                                            if result == '胜':
                                                wins += 1
                                            elif result == '平':
                                                draws += 1
                                            elif result == '负':
                                                losses += 1
                                            
                                            # 提取比分
                                            import re
                                            score_match = re.search(r'(\d+):(\d+)', record['teams'])
                                            if score_match:
                                                home_goals = int(score_match.group(1))
                                                away_goals = int(score_match.group(2))
                                                
                                                # 判断是主队还是客队，调整进球统计
                                                if team_type == 'home':
                                                    goals_for += home_goals
                                                    goals_against += away_goals
                                                else:
                                                    goals_for += away_goals
                                                    goals_against += home_goals
                                        
                                        # 计算胜率、平率、负率
                                        total_matches = wins + draws + losses
                                        win_rate = round(wins / total_matches * 100, 1) if total_matches > 0 else 0
                                        
                                        # 计算平均进球数、平均失球数
                                        avg_goals_for = round(goals_for / total_matches, 2) if total_matches > 0 else 0
                                        avg_goals_against = round(goals_against / total_matches, 2) if total_matches > 0 else 0
                                        
                                        return win_rate, avg_goals_for, avg_goals_against
                                    
                                    # 计算主队近期战绩统计
                                    recent_home_win_rate, recent_home_avg_goals, recent_home_avg_conceded = calculate_record_stats(home_records, 'home')
                                    # 计算客队近期战绩统计
                                    recent_away_win_rate, recent_away_avg_goals, recent_away_avg_conceded = calculate_record_stats(away_records, 'away')
                                
                                # 修正主客队xG
                                # 对于主队xG：使用主队的胜率、平局率、进球分布和客队的平均失球数
                                corrected_home_xg = bayesian_xg_correction(home_xg, team_a_avg_goals, team_b_avg_conceded, team_a_win_rate, draw_rate, h2h_matches, league_home_avg_goals, team_a_h2h_goals_prob, 
                                                                     recent_home_win_rate, recent_home_avg_goals, recent_home_avg_conceded, 
                                                                     recent_away_win_rate, recent_away_avg_goals, recent_away_avg_conceded,
                                                                     is_home_team=True)
                                # 对于客队xG：使用客队的胜率、平局率、进球分布和主队的平均失球数
                                corrected_away_xg = bayesian_xg_correction(away_xg, team_b_avg_goals, team_a_avg_conceded, team_b_win_rate, draw_rate, h2h_matches, league_away_avg_goals, team_b_h2h_goals_prob, 
                                                                     recent_home_win_rate, recent_home_avg_goals, recent_home_avg_conceded, 
                                                                     recent_away_win_rate, recent_away_avg_goals, recent_away_avg_conceded,
                                                                     is_home_team=False)
                                
                                # 显示预期进球数（xG）
                                st.markdown('#### 预期进球数（xG）')
                                
                                # 创建一个新的两列布局，专门用于显示预期进球数
                                xg_col1, xg_col2 = st.columns(2)
                                
                                # 在两列中分别显示原始和修正后的预期进球数
                                with xg_col1:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>原始预期进球：<span style='color: #22c55e; margin-left: 10px;'>{home_xg}</span></p>", unsafe_allow_html=True)
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{home_team_name}</strong>修正预期进球：<span style='color: #3b82f6; margin-left: 10px;'>{corrected_home_xg}</span></p>", unsafe_allow_html=True)
                                
                                with xg_col2:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>原始预期进球：<span style='color: #22c55e; margin-left: 10px;'>{away_xg}</span></p>", unsafe_allow_html=True)
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{away_team_name}</strong>修正预期进球：<span style='color: #3b82f6; margin-left: 10px;'>{corrected_away_xg}</span></p>", unsafe_allow_html=True)
                                
                                # 使用负二项分布进行预测
                                st.markdown('#### 负二项分布预测')
                                
                                # 定义负二项分布概率质量函数
                                def negative_binomial_pmf(x, mean, k):
                                    """
                                    计算负二项分布的概率质量函数
                                    x: 进球数
                                    mean: 期望进球数（λ）
                                    k: 离散参数
                                    返回：x个进球的概率
                                    """
                                    if mean == 0 or k == 0:
                                        return 1.0 if x == 0 else 0.0
                                    
                                    # 计算PMF: Γ(x + k) / (Γ(k) * x!) * (k/(k+λ))^k * (λ/(k+λ))^x
                                    term1 = gamma(x + k) / (gamma(k) * gamma(x + 1))
                                    term2 = (k / (k + mean)) ** k
                                    term3 = (mean / (k + mean)) ** x
                                    
                                    return term1 * term2 * term3
                                
                                # 设置离散参数：主队k为联赛主场场均进球数，客队k为联赛客场场均进球数
                                home_k = max(0.1, league_home_avg_goals)  # 避免k为0
                                away_k = max(0.1, league_away_avg_goals)  # 避免k为0
                                
                                # 计算原始xG的进球数概率分布（0-5球）
                                original_home_goals_probs = {x: negative_binomial_pmf(x, home_xg, home_k) for x in range(6)}
                                original_away_goals_probs = {x: negative_binomial_pmf(x, away_xg, away_k) for x in range(6)}
                                
                                # 计算修正后xG的进球数概率分布（0-5球）
                                corrected_home_goals_probs = {x: negative_binomial_pmf(x, corrected_home_xg, home_k) for x in range(6)}
                                corrected_away_goals_probs = {x: negative_binomial_pmf(x, corrected_away_xg, away_k) for x in range(6)}
                                
                                # 计算原始xG的比赛结果概率（胜平负）
                                original_home_win_prob = 0
                                original_draw_prob = 0
                                original_away_win_prob = 0
                                
                                for home_goals in range(6):
                                    for away_goals in range(6):
                                        prob = original_home_goals_probs[home_goals] * original_away_goals_probs[away_goals]
                                        if home_goals > away_goals:
                                            original_home_win_prob += prob
                                        elif home_goals == away_goals:
                                            original_draw_prob += prob
                                        else:
                                            original_away_win_prob += prob
                                
                                # 归一化原始概率
                                original_total_prob = original_home_win_prob + original_draw_prob + original_away_win_prob
                                if original_total_prob > 0:
                                    original_home_win_prob /= original_total_prob
                                    original_draw_prob /= original_total_prob
                                    original_away_win_prob /= original_total_prob
                                
                                # 计算修正后xG的比赛结果概率（胜平负）
                                corrected_home_win_prob = 0
                                corrected_draw_prob = 0
                                corrected_away_win_prob = 0
                                
                                for home_goals in range(6):
                                    for away_goals in range(6):
                                        prob = corrected_home_goals_probs[home_goals] * corrected_away_goals_probs[away_goals]
                                        if home_goals > away_goals:
                                            corrected_home_win_prob += prob
                                        elif home_goals == away_goals:
                                            corrected_draw_prob += prob
                                        else:
                                            corrected_away_win_prob += prob
                                
                                # 归一化修正后概率
                                corrected_total_prob = corrected_home_win_prob + corrected_draw_prob + corrected_away_win_prob
                                if corrected_total_prob > 0:
                                    corrected_home_win_prob /= corrected_total_prob
                                    corrected_draw_prob /= corrected_total_prob
                                    corrected_away_win_prob /= corrected_total_prob
                                
                                # 计算原始xG的常见比分概率
                                common_scores = [(0,0), (1,0), (0,1), (1,1), (2,0), (0,2), (2,1), (1,2), (2,2)]
                                original_score_probs = {score: original_home_goals_probs[score[0]] * original_away_goals_probs[score[1]] for score in common_scores}
                                
                                # 计算修正后xG的常见比分概率
                                corrected_score_probs = {score: corrected_home_goals_probs[score[0]] * corrected_away_goals_probs[score[1]] for score in common_scores}
                                
                                # 显示胜平负概率
                                st.markdown('##### 胜平负概率')
                                
                                # 原始xG预测的胜平负概率
                                st.markdown("<p style='font-size: 11px; color: #6b7280;'><strong>原始xG预测</strong></p>", unsafe_allow_html=True)
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{home_team_name}胜</strong>：<span style='color: #22c55e; margin-left: 10px;'>{round(original_home_win_prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                with col2:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>平局</strong>：<span style='color: #f59e0b; margin-left: 10px;'>{round(original_draw_prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                with col3:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{away_team_name}胜</strong>：<span style='color: #ef4444; margin-left: 10px;'>{round(original_away_win_prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                
                                # 修正后xG预测的胜平负概率
                                st.markdown("<p style='font-size: 11px; color: #6b7280; margin-top: 15px;'><strong>贝叶斯修正xG预测</strong></p>", unsafe_allow_html=True)
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{home_team_name}胜</strong>：<span style='color: #3b82f6; margin-left: 10px;'>{round(corrected_home_win_prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                with col2:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>平局</strong>：<span style='color: #f59e0b; margin-left: 10px;'>{round(corrected_draw_prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                with col3:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{away_team_name}胜</strong>：<span style='color: #ef4444; margin-left: 10px;'>{round(corrected_away_win_prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                
                                # 显示进球数概率分布
                                st.markdown('##### 进球数概率分布（0-5球）')
                                
                                # 原始xG预测的进球数概率分布
                                st.markdown("<p style='font-size: 11px; color: #6b7280;'><strong>原始xG预测</strong></p>", unsafe_allow_html=True)
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{home_team_name}进球概率</strong></p>", unsafe_allow_html=True)
                                    for x, prob in original_home_goals_probs.items():
                                        st.markdown(f"<p style='font-size: 11px; margin-left: 20px;'>{x}球：<span style='color: #22c55e; margin-left: 10px;'>{round(prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                with col2:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{away_team_name}进球概率</strong></p>", unsafe_allow_html=True)
                                    for x, prob in original_away_goals_probs.items():
                                        st.markdown(f"<p style='font-size: 11px; margin-left: 20px;'>{x}球：<span style='color: #22c55e; margin-left: 10px;'>{round(prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                
                                # 修正后xG预测的进球数概率分布
                                st.markdown("<p style='font-size: 11px; color: #6b7280; margin-top: 15px;'><strong>贝叶斯修正xG预测</strong></p>", unsafe_allow_html=True)
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{home_team_name}进球概率</strong></p>", unsafe_allow_html=True)
                                    for x, prob in corrected_home_goals_probs.items():
                                        st.markdown(f"<p style='font-size: 11px; margin-left: 20px;'>{x}球：<span style='color: #3b82f6; margin-left: 10px;'>{round(prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                with col2:
                                    st.markdown(f"<p style='font-size: 12px;'><strong>{away_team_name}进球概率</strong></p>", unsafe_allow_html=True)
                                    for x, prob in corrected_away_goals_probs.items():
                                        st.markdown(f"<p style='font-size: 11px; margin-left: 20px;'>{x}球：<span style='color: #3b82f6; margin-left: 10px;'>{round(prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                
                                # 显示常见比分概率
                                st.markdown('##### 常见比分概率')
                                
                                # 原始xG预测的常见比分概率
                                st.markdown("<p style='font-size: 11px; color: #6b7280;'><strong>原始xG预测</strong></p>", unsafe_allow_html=True)
                                score_cols = st.columns(3)
                                for i, (score, prob) in enumerate(original_score_probs.items()):
                                    col = score_cols[i % 3]
                                    col.markdown(f"<p style='font-size: 11px;'><strong>{score[0]}:{score[1]}</strong>：<span style='color: #22c55e; margin-left: 10px;'>{round(prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                                
                                # 修正后xG预测的常见比分概率
                                st.markdown("<p style='font-size: 11px; color: #6b7280; margin-top: 15px;'><strong>贝叶斯修正xG预测</strong></p>", unsafe_allow_html=True)
                                score_cols = st.columns(3)
                                for i, (score, prob) in enumerate(corrected_score_probs.items()):
                                    col = score_cols[i % 3]
                                    col.markdown(f"<p style='font-size: 11px;'><strong>{score[0]}:{score[1]}</strong>：<span style='color: #3b82f6; margin-left: 10px;'>{round(prob * 100, 1)}%</span></p>", unsafe_allow_html=True)
                            else:
                                st.info('暂无足够数据计算进攻力和防守力参数')
                            
                            st.info('更多预测功能正在开发中，敬请期待！')
                    
                    # 关闭合并容器的div标签
                    st.markdown('</div>', unsafe_allow_html=True)
        
        # 更新卡片计数器
        card_count += 1
    

    

else:
    st.info('点击按钮开始爬取比赛数据')




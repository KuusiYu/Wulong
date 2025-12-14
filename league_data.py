import requests
from bs4 import BeautifulSoup
import re

def get_league_data(sid):
    """
    获取联赛数据，包括平均数据和积分榜
    :param sid: 联赛ID
    :return: 包含平均数据和积分榜的字典
    """
    url = f"https://liansai.500.com/zuqiu-{sid}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"正在请求URL: {url}")
        response = requests.get(url, headers=headers)
        # 尝试使用GBK编码（500彩票网常用GBK编码）
        response.encoding = 'gbk'
        
        # 检查响应状态
        if response.status_code != 200:
            print(f"请求失败，状态码: {response.status_code}")
            return {
                'average_data': None,
                'standings': None
            }
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取联赛平均数据
        average_data = get_average_data(soup)
        
        # 获取联赛积分榜
        standings = get_standings(soup)
        
        return {
            'average_data': average_data,
            'standings': standings
        }
    except Exception as e:
        print(f"获取联赛数据失败: {e}")
        return {
            'average_data': None,
            'standings': None
        }

def get_average_data(soup):
    """
    从HTML中提取联赛平均数据
    """
    try:
        # 定位联赛数据统计表格（类名为lchart）
        stats_table = soup.find('table', class_='lchart')
        if not stats_table:
            print("未找到联赛数据统计表格")
            return None
        
        # 获取表格内容
        rows = stats_table.find_all('tr')
        if len(rows) < 2:
            print("联赛数据统计表格行数不足")
            return None
        
        # 获取第二行数据（第一行是表头）
        data_row = rows[1]
        cells = data_row.find_all('td')
        if len(cells) < 2:
            print("联赛数据统计表格列数不足")
            return None
        
        # 提取赛果分布情况（第一列）
        result_dist = {}
        result_cell = cells[0]
        result_text = result_cell.get_text()
        
        # 尝试多种方式提取赛果分布
        
        # 方式1: 查找包含'主胜'、'平局'、'客胜'的文本片段
        main_win_match = re.search(r'主胜[:：](\d+)场', result_text)
        draw_match = re.search(r'平局[:：](\d+)场', result_text)
        away_win_match = re.search(r'客胜[:：](\d+)场', result_text)
        
        if main_win_match:
            result_dist['主胜'] = main_win_match.group(1)
        if draw_match:
            result_dist['平局'] = draw_match.group(1)
        if away_win_match:
            result_dist['客胜'] = away_win_match.group(1)
        
        # 方式2: 如果方式1失败，直接查找所有数字
        if not result_dist:
            result_numbers = re.findall(r'(\d+)场', result_text)
            if len(result_numbers) >= 3:
                # 假设顺序是主胜、平局、客胜
                result_dist['主胜'] = result_numbers[0]
                result_dist['平局'] = result_numbers[1]
                result_dist['客胜'] = result_numbers[2]
        
        # 方式3: 从单元格文本中直接分割提取
        if not result_dist:
            result_parts = result_text.split('\n')
            for part in result_parts:
                part = part.strip()
                if '主胜' in part:
                    match = re.search(r'(\d+)场', part)
                    if match:
                        result_dist['主胜'] = match.group(1)
                elif '平局' in part:
                    match = re.search(r'(\d+)场', part)
                    if match:
                        result_dist['平局'] = match.group(1)
                elif '客胜' in part:
                    match = re.search(r'(\d+)场', part)
                    if match:
                        result_dist['客胜'] = match.group(1)
        
        # 提取进球分布情况（第二列）
        goal_dist = {}
        home_away_goal = {}
        total_goal = None
        
        goal_cell = cells[1]
        
        # 1. 提取主队场均进球和客队场均进球（从lchart_jinq元素中）
        jinq_div = goal_cell.find('div', class_='lchart_jinq')
        if jinq_div:
            jinq_items = jinq_div.find_all('div', class_='lchart_jinq_itm')
            if len(jinq_items) >= 2:
                # 主队场均进球
                home_jinq = jinq_items[0]
                home_span = home_jinq.find('span')
                if home_span:
                    goal_dist['主队场均进球'] = home_span.get_text().strip()
                
                # 客队场均进球
                away_jinq = jinq_items[1]
                away_span = away_jinq.find('span')
                if away_span:
                    goal_dist['客队场均进球'] = away_span.get_text().strip()
        
        # 2. 提取场均总进球（从p.lb元素中）
        lb_p = goal_cell.find('p', class_='lb')
        if lb_p:
            lb_text = lb_p.get_text()
            # 方式1: 直接从p.lb元素中提取所有数字
            total_goal_match = re.search(r'(\d+\.?\d*)', lb_text)
            if total_goal_match:
                total_goal = total_goal_match.group(1)
        
        # 3. 提取主场场均进球和客场场均进球（从最后一个p元素中）
        p_elements = goal_cell.find_all('p')
        if p_elements:
            last_p = p_elements[-1]
            last_p_text = last_p.get_text()
            
            # 提取主场场均进球
            home_avg_match = re.search(r'主场场均进球[:：](\d+\.?\d*)个', last_p_text)
            if home_avg_match:
                home_away_goal['主场场均进球'] = home_avg_match.group(1)
            
            # 提取客场场均进球
            away_avg_match = re.search(r'客场场均进球[:：](\d+\.?\d*)个', last_p_text)
            if away_avg_match:
                home_away_goal['客场场均进球'] = away_avg_match.group(1)
        
        return {
            'result_distribution': result_dist,
            'goal_distribution': goal_dist,
            'total_average_goals': total_goal,
            'home_away_average_goals': home_away_goal
        }
    except Exception as e:
        print(f"解析联赛平均数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_standings(soup):
    """
    从HTML中提取联赛积分榜
    """
    try:
        # 定位积分榜表格（类名为lstable1 ljifen_top_list_s）
        standings_table = soup.find('table', class_='lstable1 ljifen_top_list_s')
        if not standings_table:
            # 尝试使用其他class组合
            standings_table = soup.find('table', class_='lstable1')
            if not standings_table:
                standings_table = soup.find('table', class_='ljifen_top_list_s')
        
        if not standings_table:
            # 调试: 打印页面中的表格信息
            all_tables = soup.find_all('table')
            print(f"未找到联赛积分榜表格，页面中共有 {len(all_tables)} 个表格")
            for i, table in enumerate(all_tables):
                print(f"表格{i+1}类名: {table.get('class')}")
            return None
        
        standings = []
        rows = standings_table.find_all('tr')
        
        # 跳过表头行，从第二行开始处理数据
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            
            # 获取排名
            rank = cells[0].get_text().strip()
            if not rank:
                continue
            
            # 获取队伍信息
            team_cell = cells[1]
            team_a = team_cell.find('a')
            team_name = team_a.get_text().strip() if team_a else cells[1].get_text().strip()
            team_link = team_a['href'] if team_a else ''
            team_title = team_a['title'] if team_a and 'title' in team_a.attrs else ''
            
            # 获取比赛数据
            matches = cells[2].get_text().strip()
            wins = cells[3].get_text().strip()
            draws = cells[4].get_text().strip()
            losses = cells[5].get_text().strip()
            points = cells[6].get_text().strip()
            
            # 确保数据有效
            if team_name:
                standings.append({
                    'rank': rank,
                    'team': {
                        'name': team_name,
                        'link': team_link,
                        'title': team_title
                    },
                    'matches': matches,
                    'wins': wins,
                    'draws': draws,
                    'losses': losses,
                    'points': points
                })
        
        return standings if standings else None
    except Exception as e:
        print(f"解析联赛积分榜失败: {e}")
        import traceback
        traceback.print_exc()
        return None
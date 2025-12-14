import requests
from bs4 import BeautifulSoup
import random
import re
import time


def fetch_match_history(fid):
    """根据比赛ID抓取双方历史交战记录"""
    url = f'https://odds.500.com/fenxi/shuju-{fid}.shtml'
    
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
    
    # 防封IP处理：添加随机延迟
    time.sleep(random.uniform(0.3, 1.0))
    
    try:
        # 发送请求
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        # 处理编码问题
        try:
            html = response.content.decode('gbk')
        except UnicodeDecodeError:
            try:
                html = response.content.decode('gb2312')
            except UnicodeDecodeError:
                html = response.content.decode('utf-8')
        
        # 解析HTML
        soup = BeautifulSoup(html, 'html.parser')
                
        # 检查页面是否返回"暂无该场比赛的数据"
        if "暂无该场比赛的数据" in html:
            print(f"页面返回暂无数据: {url}")
            # 返回空数据结构
            return {
                'match_info': '',
                'stats': '',
                'matches': [],
                'average_data': {
                    'team_a': {
                        'name': '',
                        'rank': '',
                        'average_goals': '',
                        'average_goals_home': '',
                        'average_goals_away': '',
                        'average_conceded': '',
                        'average_conceded_home': '',
                        'average_conceded_away': ''
                    },
                    'team_b': {
                        'name': '',
                        'rank': '',
                        'average_goals': '',
                        'average_goals_home': '',
                        'average_goals_away': '',
                        'average_conceded': '',
                        'average_conceded_home': '',
                        'average_conceded_away': ''
                    }
                },
                'pre_match_standings': {
                    'title': '',
                    'team_a': {
                        'name': '',
                        'rank': '',
                        'stats': {
                            '总成绩': {},
                            '主场': {},
                            '客场': {}
                        }
                    },
                    'team_b': {
                        'name': '',
                        'rank': '',
                        'stats': {
                            '总成绩': {},
                            '主场': {},
                            '客场': {}
                        }
                    }
                },
                'recent_records_all': [],
                'recent_records_home_away': {
                    'team_a_home': [],
                    'team_a_away': [],
                    'team_b_home': [],
                    'team_b_away': []
                }
            }
        
        # 初始化结果
        history_data = {
            'match_info': '',
            'stats': '',
            'matches': [],
            'average_data': {
                'team_a': {
                    'name': '',
                    'rank': '',
                    'average_goals': '',
                    'average_goals_home': '',
                    'average_goals_away': '',
                    'average_conceded': '',
                    'average_conceded_home': '',
                    'average_conceded_away': ''
                },
                'team_b': {
                    'name': '',
                    'rank': '',
                    'average_goals': '',
                    'average_goals_home': '',
                    'average_goals_away': '',
                    'average_conceded': '',
                    'average_conceded_home': '',
                    'average_conceded_away': ''
                }
            },
            'pre_match_standings': {
                'title': '',
                'team_a': {
                    'name': '',
                    'rank': '',
                    'stats': {
                        '总成绩': {},
                        '主场': {},
                        '客场': {}
                    }
                },
                'team_b': {
                    'name': '',
                    'rank': '',
                    'stats': {
                        '总成绩': {},
                        '主场': {},
                        '客场': {}
                    }
                }
            },
            'recent_records_all': [],
            'recent_records_home_away': {
                'team_a_home': [],
                'team_a_away': [],
                'team_b_home': [],
                'team_b_away': []
            }
        }
        
        # 查找两队交战史区域
        team_jiaozhan = soup.find('div', id='team_jiaozhan')
        if not team_jiaozhan:
            # 尝试查找其他可能的两队交战史区域
            team_jiaozhan = soup.find('div', class_='history')
            if not team_jiaozhan:
                print(f"未找到两队交战史区域: {url}")
                return history_data
                
        # 提取比赛信息
        title = team_jiaozhan.find('h4')
        if title:
            history_data['match_info'] = title.text.strip()
                
        # 提取统计信息
        his_info = team_jiaozhan.find('span', class_='his_info')
        if his_info:
            history_data['stats'] = his_info.text.strip()
                
        # 提取历史比赛列表
        table = team_jiaozhan.find('table', class_='pub_table')
        if not table:
            # 尝试查找其他可能的表格
            table = team_jiaozhan.find('table')
            if not table:
                print(f"未找到历史比赛表格: {url}")
                # 不提前返回，继续解析其他数据
                
        if table:
            tbody = table.find('tbody')
            if not tbody:
                tbody = table  # 有些表格可能没有tbody
                    
            rows = tbody.find_all('tr')
            print(f"找到{len(rows)}行数据")
                    
            for row in rows:
                # 提取所有单元格，包括th和td
                cells = row.find_all(['th', 'td'])
                        
                # 跳过表头行（如果第一列是th）
                if cells and cells[0].name == 'th':
                    continue
                        
                # 跳过本场比赛行（带有bmatch类）
                if 'bmatch' in row.get('class', []):
                    continue
                        
                # 确保至少有5个单元格
                if len(cells) < 5:
                    print(f"行数据不足5个单元格: {len(cells)}个")
                    continue
                        
                # 提取赛事信息
                league = cells[0].text.strip() if cells[0] else ''
                        
                # 提取日期
                date = cells[1].text.strip() if cells[1] else ''
                        
                # 提取对阵信息和比分
                teams_cell = cells[2]
                        
                # 提取主队名称
                home_team = teams_cell.find('span', class_='dz-l')
                home_team_name = home_team.text.strip() if home_team else ''
                # 移除主队排名
                if home_team:
                    home_rank = home_team.find('span', class_='gray')
                    if home_rank:
                        home_team_name = home_team_name.replace(home_rank.text, '').strip()
                        
                # 提取客队名称
                away_team = teams_cell.find('span', class_='dz-r')
                away_team_name = away_team.text.strip() if away_team else ''
                # 移除客队排名
                if away_team:
                    away_rank = away_team.find('span', class_='gray')
                    if away_rank:
                        away_team_name = away_team_name.replace(away_rank.text, '').strip()
                        
                # 提取比分
                score_tag = teams_cell.find('em')
                score_text = ' VS '
                if score_tag:
                    # 提取比分文本
                    score_content = score_tag.text.strip()
                    if score_content != 'VS':
                        # 在比分前后添加空格
                        score_text = f" {score_content} "
                        
                # 组合对阵信息
                teams_text = f"{home_team_name}{score_text}{away_team_name}"
                        
                # 提取半场比分
                half_score = cells[3].text.strip() if cells[3] else ''
                # 处理半场比分，添加空格
                if half_score and half_score != 'VS':
                    half_score = f" {half_score} "
                elif half_score == 'VS':
                    half_score = ' VS '
                        
                # 提取赛果
                result = cells[4].text.strip() if cells[4] else ''
                        
                # 构建比赛数据
                match_data = {
                    'league': league,
                    'date': date,
                    'teams': teams_text,
                    'half_score': half_score,
                    'result': result
                }
                        
                history_data['matches'].append(match_data)
                print(f"添加了一场比赛数据: {match_data['teams']}")
                
        # 提取平均数据
        print(f"开始提取平均数据: {url}")
                
        # 查找平均数据区域
        integral_div = None
                
        # 1. 首先查找所有div，搜索包含"平均数据"文本的div
        all_divs = soup.find_all('div')
        for div in all_divs:
            h4 = div.find('h4')
            if h4 and '平均数据' in h4.text:
                integral_div = div
                print(f"通过包含平均数据标题的h4找到div")
                # 向上查找父级M_box div
                parent = div.parent
                while parent:
                    if 'M_box' in parent.get('class', []):
                        integral_div = parent
                        print(f"找到父级M_box div")
                        break
                    parent = parent.parent
                break
                
        # 2. 如果没有找到，尝试CSS选择器
        if not integral_div:
            integral_div = soup.select_one('div.M_box.integral')
            if integral_div:
                print(f"通过CSS选择器div.M_box.integral找到平均数据区域")
                
        # 3. 如果仍然找不到，尝试查找所有带有M_box类的div
        if not integral_div:
            all_m_boxes = soup.find_all('div', class_='M_box')
            print(f"找到{len(all_m_boxes)}个M_box类的div")
            for div in all_m_boxes:
                h4 = div.find('h4')
                if h4 and '平均数据' in h4.text:
                    integral_div = div
                    print(f"通过M_box类和平均数据标题找到平均数据区域")
                    break
                
        # 4. 如果仍然找不到，尝试查找所有带有integral类的div
        if not integral_div:
            all_integral_divs = soup.find_all('div', class_='integral')
            print(f"找到{len(all_integral_divs)}个integral类的div")
            for div in all_integral_divs:
                h4 = div.find('h4')
                if h4 and '平均数据' in h4.text:
                    integral_div = div
                    print(f"通过integral类和平均数据标题找到平均数据区域")
                    break
                
        # 打印调试信息
        if integral_div:
            print(f"integral_div内容（前1000字符）: {str(integral_div)[:1000]}")
        else:
            print(f"未找到平均数据区域")
                
        # 直接查找关键元素作为备选方案
        all_team_names = soup.find_all('div', class_='team_name')
        all_pub_tables = soup.find_all('table', class_='pub_table')
        print(f"直接找到{len(all_team_names)}个team_name类的div和{len(all_pub_tables)}个pub_table类的table")
                
        # 开始提取平均数据
        team_a_name = ''
        team_b_name = ''
                
        # 提取球队名称和排名
        if integral_div:
            m_sub_title = integral_div.find('div', class_='M_sub_title')
            if m_sub_title:
                team_names = m_sub_title.find_all('div', class_='team_name')
                if len(team_names) >= 2:
                    # 主队名称和排名
                    team_a_text = team_names[0].text.strip()
                    team_a_rank_match = re.search(r'\[(.*?)\]', team_a_text)
                    if team_a_rank_match:
                        history_data['average_data']['team_a']['name'] = team_a_text.replace(team_a_rank_match.group(0), '').strip()
                        history_data['average_data']['team_a']['rank'] = team_a_rank_match.group(1)
                    else:
                        history_data['average_data']['team_a']['name'] = team_a_text
                            
                    # 客队名称和排名
                    team_b_text = team_names[1].text.strip()
                    team_b_rank_match = re.search(r'\[(.*?)\]', team_b_text)
                    if team_b_rank_match:
                        history_data['average_data']['team_b']['name'] = team_b_text.replace(team_b_rank_match.group(0), '').strip()
                        history_data['average_data']['team_b']['rank'] = team_b_rank_match.group(1)
                    else:
                        history_data['average_data']['team_b']['name'] = team_b_text
        # 如果从integral_div没有找到球队名称，使用直接查找的结果
        elif len(all_team_names) >= 2:
            # 主队名称和排名
            team_a_text = all_team_names[0].text.strip()
            team_a_rank_match = re.search(r'\[(.*?)\]', team_a_text)
            if team_a_rank_match:
                history_data['average_data']['team_a']['name'] = team_a_text.replace(team_a_rank_match.group(0), '').strip()
                history_data['average_data']['team_a']['rank'] = team_a_rank_match.group(1)
            else:
                history_data['average_data']['team_a']['name'] = team_a_text
                    
            # 客队名称和排名
            team_b_text = all_team_names[1].text.strip()
            team_b_rank_match = re.search(r'\[(.*?)\]', team_b_text)
            if team_b_rank_match:
                history_data['average_data']['team_b']['name'] = team_b_text.replace(team_b_rank_match.group(0), '').strip()
                history_data['average_data']['team_b']['rank'] = team_b_rank_match.group(1)
            else:
                history_data['average_data']['team_b']['name'] = team_b_text
                
        # 提取平均数据表格
        team_a_table = None
        team_b_table = None
                
        if integral_div:
            m_content = integral_div.find('div', class_='M_content')
            if m_content:
                # 先尝试通过class查找team_a和team_b
                team_a_div = m_content.find('div', class_='team_a')
                team_b_div = m_content.find('div', class_='team_b')
                        
                # 如果找到了，再查找表格
                if team_a_div:
                    team_a_table = team_a_div.find('table', class_='pub_table')
                    # 如果没有找到带class的表格，尝试查找任何表格
                    if not team_a_table:
                        team_a_table = team_a_div.find('table')
                if team_b_div:
                    team_b_table = team_b_div.find('table', class_='pub_table')
                    # 如果没有找到带class的表格，尝试查找任何表格
                    if not team_b_table:
                        team_b_table = team_b_div.find('table')
                        
                # 如果还是没有找到，尝试在M_content中直接查找所有表格
                if not team_a_table or not team_b_table:
                    all_tables = m_content.find_all('table')
                    if len(all_tables) >= 2:
                        team_a_table = all_tables[0]
                        team_b_table = all_tables[1]
        # 如果从integral_div没有找到表格，使用直接查找的结果
        elif len(all_pub_tables) >= 2:
            team_a_table = all_pub_tables[0]
            team_b_table = all_pub_tables[1]
                
        # 添加调试信息
        print(f"平均数据表格查找结果: team_a_table={team_a_table is not None}, team_b_table={team_b_table is not None}")
                
        # 处理主队数据表格
        if team_a_table:
            rows = team_a_table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 4:
                    row_title = tds[0].text.strip()
                    if row_title == '平均入球':
                        history_data['average_data']['team_a']['average_goals'] = tds[1].text.strip()
                        history_data['average_data']['team_a']['average_goals_home'] = tds[2].text.strip()
                        history_data['average_data']['team_a']['average_goals_away'] = tds[3].text.strip()
                    elif row_title == '平均失球':
                        history_data['average_data']['team_a']['average_conceded'] = tds[1].text.strip()
                        history_data['average_data']['team_a']['average_conceded_home'] = tds[2].text.strip()
                        history_data['average_data']['team_a']['average_conceded_away'] = tds[3].text.strip()
                
        # 处理客队数据表格
        if team_b_table:
            rows = team_b_table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 4:
                    row_title = tds[0].text.strip()
                    if row_title == '平均入球':
                        history_data['average_data']['team_b']['average_goals'] = tds[1].text.strip()
                        history_data['average_data']['team_b']['average_goals_home'] = tds[2].text.strip()
                        history_data['average_data']['team_b']['average_goals_away'] = tds[3].text.strip()
                    elif row_title == '平均失球':
                        history_data['average_data']['team_b']['average_conceded'] = tds[1].text.strip()
                        history_data['average_data']['team_b']['average_conceded_home'] = tds[2].text.strip()
                        history_data['average_data']['team_b']['average_conceded_away'] = tds[3].text.strip()
                
        print(f"平均数据提取完成")
                
        # 提取近期战绩（不区分主客场）
        print(f"开始提取近期战绩（不区分主客场）")
                
        # 查找近期战绩（不区分主客场）区域
        recent_records_all_div = soup.find('div', class_='M_box record')
        if recent_records_all_div:
            # 添加调试信息，输出整个近期战绩区域的HTML结构
            print(f"找到近期战绩区域，开始提取内容")
            print(f"近期战绩区域包含的子元素数量: {len(recent_records_all_div.find_all(recursive=False))}")
                    
            # 查找所有p标签，看看是否有包含"近10场战绩"的
            all_p_in_record = recent_records_all_div.find_all('p')
            print(f"近期战绩区域内找到{len(all_p_in_record)}个p标签")
            for i, p_tag in enumerate(all_p_in_record):
                p_text = p_tag.text.strip()
                if p_text:
                    print(f"p标签{i}内容: {p_text}")
                    if '近10场战绩' in p_text:
                        print(f"找到包含'近10场战绩'的p标签！")
                    
            # 近期战绩包含两个部分：主队(team_a)和客队(team_b)
            team_a_div = recent_records_all_div.find('div', class_='team_a')
            team_b_div = recent_records_all_div.find('div', class_='team_b')
                    
            # 定义函数来解析单个队伍的近期战绩表格
            def parse_team_recent_records(team_div, team_name):
                if not team_div:
                    print(f"未找到{team_name}的近期战绩区域")
                    return
                        
                # 提取近期战绩 summary 信息（如：7胜0平3负 进18球失13球）
                # 尝试从整个team_div中查找包含"近10场战绩"的p标签
                all_p_tags = team_div.find_all('p')
                for p_tag in all_p_tags:
                    p_text = p_tag.text.strip()
                    if '近10场战绩' in p_text:
                        summary_text = p_text
                        print(f"{team_name}近期战绩 summary: {summary_text}")
                        # 存储 summary 信息到 history_data
                        if team_name == "主队":
                            history_data['recent_records_summary_team_a'] = summary_text
                        else:
                            history_data['recent_records_summary_team_b'] = summary_text
                        break
                        
                # 如果没有找到，尝试查找包含"近10场"的span标签
                if not (team_name == "主队" and 'recent_records_summary_team_a' in history_data) and not (team_name == "客队" and 'recent_records_summary_team_b' in history_data):
                    all_spans = team_div.find_all('span')
                    for span in all_spans:
                        span_text = span.text.strip()
                        if '近10场' in span_text:
                            summary_text = span_text
                            print(f"{team_name}近期战绩 summary (从span标签): {summary_text}")
                            # 存储 summary 信息到 history_data
                            if team_name == "主队":
                                history_data['recent_records_summary_team_a'] = summary_text
                            else:
                                history_data['recent_records_summary_team_b'] = summary_text
                            break
                        
                # 如果仍然没有找到，尝试查找整个team_div的前几个元素
                if not (team_name == "主队" and 'recent_records_summary_team_a' in history_data) and not (team_name == "客队" and 'recent_records_summary_team_b' in history_data):
                    # 查找team_div的直接子元素
                    direct_children = team_div.find_all(recursive=False)
                    for child in direct_children:
                        child_text = child.text.strip()
                        if '近10场战绩' in child_text:
                            summary_text = child_text
                            print(f"{team_name}近期战绩 summary (从直接子元素): {summary_text}")
                            # 存储 summary 信息到 history_data
                            if team_name == "主队":
                                history_data['recent_records_summary_team_a'] = summary_text
                            else:
                                history_data['recent_records_summary_team_b'] = summary_text
                            break
                        
                # 找到队伍的表格
                table = team_div.find('table', class_='pub_table')
                if not table:
                    print(f"未找到{team_name}的近期战绩表格")
                    return
                        
                tbody = table.find('tbody')
                if not tbody:
                    tbody = table  # 有些表格可能没有tbody
                        
                rows = tbody.find_all('tr')
                print(f"{team_name}近期战绩找到{len(rows)}行数据")
                        
                # 数据行计数器，用于跳过第一行（当前比赛）
                data_row_count = 0
                        
                for row in rows:
                    # 提取所有单元格，包括th和td
                    cells = row.find_all(['th', 'td'])
                            
                    # 跳过表头行（如果第一列是th）
                    if cells and cells[0].name == 'th':
                        continue
                            
                    # 确保至少有6个单元格
                    if len(cells) < 6:
                        print(f"{team_name}近期战绩行数据不足6个单元格: {len(cells)}个")
                        continue
                            
                    # 跳过第一行数据（当前比赛）
                    if data_row_count == 0:
                        data_row_count += 1
                        continue
                            
                    # 增加数据行计数
                    data_row_count += 1
                            
                    # 提取赛事信息
                    league = cells[0].text.strip() if cells[0] else ''
                            
                    # 提取日期
                    date = cells[1].text.strip() if cells[1] else ''
                            
                    # 提取对阵信息和比分
                    teams_cell = cells[2]
                            
                    # 提取主队名称
                    home_team = teams_cell.find('span', class_='dz-l')
                    home_team_name = home_team.text.strip() if home_team else ''
                    # 移除主队排名
                    if home_team:
                        home_rank = home_team.find('span', class_='gray')
                        if home_rank:
                            home_team_name = home_team_name.replace(home_rank.text, '').strip()
                            
                    # 提取客队名称
                    away_team = teams_cell.find('span', class_='dz-r')
                    away_team_name = away_team.text.strip() if away_team else ''
                    # 移除客队排名
                    if away_team:
                        away_rank = away_team.find('span', class_='gray')
                        if away_rank:
                            away_team_name = away_team_name.replace(away_rank.text, '').strip()
                            
                    # 提取比分
                    score_tag = teams_cell.find('em')
                    score_text = ' VS '
                    if score_tag:
                        # 提取比分文本
                        score_content = score_tag.text.strip()
                        if score_content != 'VS':
                            # 在比分前后添加空格
                            score_text = f" {score_content} "
                            
                    # 组合对阵信息
                    teams_text = f"{home_team_name}{score_text}{away_team_name}"
                            
                    # 提取半场比分
                    half_score = cells[4].text.strip() if cells[4] else ''
                    # 处理半场比分，添加空格
                    if half_score and half_score != 'VS':
                        half_score = f" {half_score} "
                    elif half_score == 'VS':
                        half_score = ' VS '
                            
                    # 提取赛果
                    result = cells[5].text.strip() if cells[5] else ''
                            
                    # 构建比赛数据
                    match_data = {
                        'league': league,
                        'date': date,
                        'teams': teams_text,
                        'half_score': half_score,
                        'result': result,
                        'team_type': team_name  # 标记是主队还是客队的战绩
                    }
                            
                    history_data['recent_records_all'].append(match_data)
                    print(f"添加了{team_name}一场近期战绩（不区分主客场）数据: {match_data['teams']}")
                    
            # 解析主队和客队的近期战绩
            parse_team_recent_records(team_a_div, "主队")
            parse_team_recent_records(team_b_div, "客队")
        else:
            print(f"未找到近期战绩（不区分主客场）区域")
                
        # 提取近期战绩（区分主客场）
        print(f"开始提取近期战绩（区分主客场）")
                
        # 定义一个辅助函数来提取区分主客场的战绩
        def extract_home_away_records(div_id):
            records = []
            div = soup.find('div', id=div_id)
            if div:
                table = div.find('table', class_='pub_table')
                if table:
                    tbody = table.find('tbody')
                    if not tbody:
                        tbody = table  # 有些表格可能没有tbody
                    
                    rows = tbody.find_all('tr')
                    print(f"近期战绩（区分主客场）{div_id}找到{len(rows)}行数据")
                    
                    # 数据行计数器，用于跳过第一行（当前比赛）
                    data_row_count = 0
                    
                    for row in rows:
                        # 提取所有单元格，包括th和td
                        cells = row.find_all(['th', 'td'])
                                
                        # 跳过表头行（如果第一列是th）
                        if cells and cells[0].name == 'th':
                            continue
                                
                        # 确保至少有6个单元格
                        if len(cells) < 6:
                            print(f"近期战绩（区分主客场）{div_id}行数据不足6个单元格: {len(cells)}个")
                            continue
                                
                        # 跳过第一行数据（当前比赛）
                        if data_row_count == 0:
                            data_row_count += 1
                            continue
                                
                        # 增加数据行计数
                        data_row_count += 1
                                
                        # 提取赛事信息
                        league = cells[0].text.strip() if cells[0] else ''
                                
                        # 提取日期
                        date = cells[1].text.strip() if cells[1] else ''
                                
                        # 提取对阵信息和比分
                        teams_cell = cells[2]
                                
                        # 提取主队名称
                        home_team = teams_cell.find('span', class_='dz-l')
                        home_team_name = home_team.text.strip() if home_team else ''
                        # 移除主队排名
                        if home_team:
                            home_rank = home_team.find('span', class_='gray')
                            if home_rank:
                                home_team_name = home_team_name.replace(home_rank.text, '').strip()
                                
                        # 提取客队名称
                        away_team = teams_cell.find('span', class_='dz-r')
                        away_team_name = away_team.text.strip() if away_team else ''
                        # 移除客队排名
                        if away_team:
                            away_rank = away_team.find('span', class_='gray')
                            if away_rank:
                                away_team_name = away_team_name.replace(away_rank.text, '').strip()
                                
                        # 提取比分
                        score_tag = teams_cell.find('em')
                        score_text = ' VS '
                        if score_tag:
                            # 提取比分文本
                            score_content = score_tag.text.strip()
                            if score_content != 'VS':
                                # 在比分前后添加空格
                                score_text = f" {score_content} "
                                
                        # 组合对阵信息
                        teams_text = f"{home_team_name}{score_text}{away_team_name}"
                                
                        # 提取半场比分
                        half_score = cells[4].text.strip() if cells[4] else ''
                        # 处理半场比分，添加空格
                        if half_score and half_score != 'VS':
                            half_score = f" {half_score} "
                        elif half_score == 'VS':
                            half_score = ' VS '
                                
                        # 提取赛果
                        result = cells[5].text.strip() if cells[5] else ''
                                
                        # 构建比赛数据
                        match_data = {
                            'league': league,
                            'date': date,
                            'teams': teams_text,
                            'half_score': half_score,
                            'result': result
                        }
                                
                        records.append(match_data)
            else:
                print(f"近期战绩（区分主客场）{div_id}未找到div")
            return records
                
        # 提取主队主场战绩（team_zhanji2_1）
        history_data['recent_records_home_away']['team_a_home'] = extract_home_away_records('team_zhanji2_1')
                
        # 提取客队客场战绩（team_zhanji2_0）
        history_data['recent_records_home_away']['team_b_away'] = extract_home_away_records('team_zhanji2_0')
                
        # 提取客队主场战绩（team_zhanji2_3）
        history_data['recent_records_home_away']['team_b_home'] = extract_home_away_records('team_zhanji2_3')
                
        # 提取主队客场战绩（team_zhanji2_2）
        history_data['recent_records_home_away']['team_a_away'] = extract_home_away_records('team_zhanji2_2')
                
        print(f"近期战绩（区分主客场）提取完成")
                
        # 提取赛前联赛积分排名
        print(f"开始提取赛前联赛积分排名")
                
        # 查找赛前联赛积分排名区域
        pre_match_div = None
                
        # 1. 查找包含"赛前联赛积分排名"或"赛前杯赛积分排名"文本的M_box
        all_m_boxes = soup.find_all('div', class_='M_box')
        for div in all_m_boxes:
            h4 = div.find('h4')
            if h4 and ('赛前联赛积分排名' in h4.text or '赛前杯赛积分排名' in h4.text):
                pre_match_div = div
                print(f"找到赛前积分排名区域")
                break
                
        if pre_match_div:
            # 提取标题
            h4 = pre_match_div.find('h4')
            if h4:
                history_data['pre_match_standings']['title'] = h4.text.strip()
                    
            # 提取球队名称和排名
            m_sub_title = pre_match_div.find('div', class_='M_sub_title')
            if m_sub_title:
                team_names = m_sub_title.find_all('div', class_='team_name')
                if len(team_names) >= 2:
                    # 主队名称和排名
                    team_a_text = team_names[0].text.strip()
                    team_a_rank_match = re.search(r'\[(.*?)\]', team_a_text)
                    if team_a_rank_match:
                        history_data['pre_match_standings']['team_a']['name'] = team_a_text.replace(team_a_rank_match.group(0), '').strip()
                        history_data['pre_match_standings']['team_a']['rank'] = team_a_rank_match.group(1)
                    else:
                        history_data['pre_match_standings']['team_a']['name'] = team_a_text
                            
                    # 客队名称和排名
                    team_b_text = team_names[1].text.strip()
                    team_b_rank_match = re.search(r'\[(.*?)\]', team_b_text)
                    if team_b_rank_match:
                        history_data['pre_match_standings']['team_b']['name'] = team_b_text.replace(team_b_rank_match.group(0), '').strip()
                        history_data['pre_match_standings']['team_b']['rank'] = team_b_rank_match.group(1)
                    else:
                        history_data['pre_match_standings']['team_b']['name'] = team_b_text
                    
            # 提取积分排名表格
            m_content = pre_match_div.find('div', class_='M_content')
            if m_content:
                # 查找两队的表格容器
                team_a_div = m_content.find('div', class_='team_a')
                team_b_div = m_content.find('div', class_='team_b')
                        
                # 定义函数来解析表格数据
                def parse_standings_table(table_div):
                    if not table_div:
                        return {}
                    
                    table = table_div.find('table', class_='pub_table')
                    if not table:
                        table = table_div.find('table')
                    if not table:
                        return {}
                    
                    tbody = table.find('tbody')
                    if not tbody:
                        tbody = table
                    
                    rows = tbody.find_all('tr')
                    stats = {}
                    
                    # 列名映射
                    column_names = ['比赛', '胜', '平', '负', '进', '失', '净', '积分', '排名', '胜率']
                    
                    for row in rows:
                        tds = row.find_all('td')
                        if len(tds) >= 11:
                            # 提取行标题（总成绩、主场、客场）
                            row_title = tds[0].text.strip()
                            if row_title in ['总成绩', '主场', '客场']:
                                # 提取各项数据
                                row_data = {}
                                for i in range(1, 11):
                                    if i <= len(column_names):
                                        row_data[column_names[i-1]] = tds[i].text.strip()
                                stats[row_title] = row_data
                    
                    return stats
                        
                # 解析两队的表格数据
                history_data['pre_match_standings']['team_a']['stats'] = parse_standings_table(team_a_div)
                history_data['pre_match_standings']['team_b']['stats'] = parse_standings_table(team_b_div)
                
        print(f"赛前联赛积分排名提取完成")
                
        return history_data
    except requests.Timeout:
        print(f'请求超时: {url}')
        return {'match_info': '', 'stats': '', 'matches': [], 'average_data': {'team_a': {}, 'team_b': {}}, 'pre_match_standings': {'title': '', 'team_a': {'name': '', 'rank': '', 'stats': {'总成绩': {}, '主场': {}, '客场': {}}}, 'team_b': {'name': '', 'rank': '', 'stats': {'总成绩': {}, '主场': {}, '客场': {}}}},'recent_records_all': [], 'recent_records_home_away': {'team_a_home': [], 'team_a_away': [], 'team_b_home': [], 'team_b_away': []}}
    except requests.RequestException as e:
        print(f'网络请求失败: {e}')
        return {'match_info': '', 'stats': '', 'matches': [], 'average_data': {'team_a': {}, 'team_b': {}}, 'pre_match_standings': {'title': '', 'team_a': {'name': '', 'rank': '', 'stats': {'总成绩': {}, '主场': {}, '客场': {}}}, 'team_b': {'name': '', 'rank': '', 'stats': {'总成绩': {}, '主场': {}, '客场': {}}}},'recent_records_all': [], 'recent_records_home_away': {'team_a_home': [], 'team_a_away': [], 'team_b_home': [], 'team_b_away': []}}
    except Exception as e:
        print(f'爬取历史交战记录失败: {e}')
        import traceback
        traceback.print_exc()
        return {'match_info': '', 'stats': '', 'matches': [], 'average_data': {'team_a': {}, 'team_b': {}}, 'pre_match_standings': {'title': '', 'team_a': {'name': '', 'rank': '', 'stats': {'总成绩': {}, '主场': {}, '客场': {}}}, 'team_b': {'name': '', 'rank': '', 'stats': {'总成绩': {}, '主场': {}, '客场': {}}}},'recent_records_all': [], 'recent_records_home_away': {'team_a_home': [], 'team_a_away': [], 'team_b_home': [], 'team_b_away': []}}
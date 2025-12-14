import requests
# 禁用urllib3的InsecureRequestWarning警告
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

from bs4 import BeautifulSoup
import time
import random

class MatchCrawler:
    """比赛数据爬取类"""
    
    @staticmethod
    def crawl_matches():
        """爬取比赛数据"""
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
        
        # 防封IP处理：添加随机延迟
        time.sleep(random.uniform(1, 3))
        
        try:
            # 发送请求
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            
            # 读取响应内容，处理编码问题
            # 先获取原始字节，然后尝试多种编码解码
            content = response.content
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
                    
                round_info = tds[2].text.strip() if len(tds) > 2 else ''
                match_time = tds[3].text.strip() if len(tds) > 3 else ''
                match_status = tds[4].text.strip() if len(tds) > 4 else ''
                
                # 提取主队
                home_td = tds[5]
                home_team = ''
                home_team_id = ''
                if home_td:
                    # 优先提取a标签中的球队名称，避免包含红黄牌
                    home_a = home_td.find('a')
                    if home_a:
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
                
                # 提取比分信息
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
                else:
                    score = ''
                
                # 提取半场比分
                half_score_td = tds[8] if len(tds) > 8 else None
                half_score = half_score_td.text.strip() if half_score_td else ''
                
                # 提取客队
                away_td = tds[7]
                away_team = ''
                away_team_id = ''
                if away_td:
                    # 优先提取a标签中的球队名称，避免包含红黄牌
                    away_a = away_td.find('a')
                    if away_a:
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
                else:
                    away_team = ''
                
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
                    'away_team_id': away_team_id
                }
                
                matches.append(match)
            
            return matches
        except requests.Timeout:
            return []
        except requests.RequestException as e:
            print(f'网络请求失败: {e}')
            return []
        except Exception as e:
            print(f'爬取失败: {e}')
            import traceback
            traceback.print_exc()
            return []
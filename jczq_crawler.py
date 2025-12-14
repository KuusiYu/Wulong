import requests
# 禁用urllib3的InsecureRequestWarning警告
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

from bs4 import BeautifulSoup
import time
import random

class JCZQCrawler:
    """竞彩足球数据爬取类"""
    
    @staticmethod
    def get_user_agents():
        """获取用户代理池"""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
    
    @staticmethod
    def get_jczq_data():
        """爬取竞彩足球数据"""
        url = 'https://live.500.com/'
        
        headers = {
            'User-Agent': random.choice(JCZQCrawler.get_user_agents()),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 添加随机延迟，防止被封IP
        time.sleep(random.uniform(1, 3))
        
        try:
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            
            # 处理编码问题
            content = response.content
            try:
                html = content.decode('gbk')
            except UnicodeDecodeError:
                try:
                    html = content.decode('gb2312')
                except UnicodeDecodeError:
                    html = content.decode('utf-8')
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 找到比赛表格
            table = soup.find('table', id='table_match')
            if not table:
                return {}
            
            # 获取所有比赛行
            match_rows = table.find_all('tr', attrs={'id': lambda x: x and x.startswith('a')})
            
            jczq_data = {}
            
            for row in match_rows:
                # 提取比赛ID (fid)
                fid = row.get('fid')
                if not fid:
                    continue
                
                # 提取第一列，包含竞彩标识（如：周一001）
                tds = row.find_all('td')
                if len(tds) < 1:
                    continue
                
                first_td = tds[0]
                jczq_identifier = first_td.text.strip()
                
                # 检查是否为竞彩比赛（包含如：周一001格式）
                # 竞彩标识格式通常是：周X数字
                import re
                jczq_match = re.search(r'^周[一二三四五六日]\d+$', jczq_identifier)
                if jczq_match:
                    jczq_data[fid] = jczq_identifier
            
            return jczq_data
            
        except requests.Timeout:
            print('竞彩数据请求超时')
            return {}
        except requests.RequestException as e:
            print(f'竞彩数据网络请求失败: {e}')
            return {}
        except Exception as e:
            print(f'竞彩数据爬取失败: {e}')
            import traceback
            traceback.print_exc()
            return {}
    
    @staticmethod
    def merge_jczq_data(matches, jczq_data):
        """将竞彩数据合并到比赛数据中"""
        if not matches or not jczq_data:
            return matches
        
        for match in matches:
            # 获取比赛ID（fid）
            fid = match.get('fid')
            if fid and fid in jczq_data:
                # 添加竞彩标识
                match['jczq_identifier'] = jczq_data[fid]
            else:
                # 非竞彩比赛，设置为空
                match['jczq_identifier'] = ''
        
        return matches
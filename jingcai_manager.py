import asyncio
import aiohttp
import random
from bs4 import BeautifulSoup

# 禁用aiohttp的SSL警告
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

class JingcaiManager:
    """竞彩标识管理器，负责竞彩标识的抓取、处理和渲染"""
    
    def __init__(self):
        self.jingcai_matches = {}  # 存储竞彩标识数据，key为match_id，value为竞彩标识
    
    async def crawl_jingcai_ids(self, url='https://live.500.com/'):
        """从目标URL异步抓取竞彩标识数据"""
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
        await asyncio.sleep(random.uniform(0.2, 0.8))
        
        try:
            # 创建aiohttp会话
            async with aiohttp.ClientSession() as session:
                # 发送请求
                async with session.get(url, headers=headers, timeout=15, ssl=False) as response:
                    # 读取响应内容
                    content = await response.read()
                    
                    # 处理编码问题
                    try:
                        html = content.decode('gbk')
                    except UnicodeDecodeError:
                        try:
                            html = content.decode('gb2312')
                        except UnicodeDecodeError:
                            html = content.decode('utf-8')
                    
                    # 解析HTML
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 找到所有比赛行
                    match_rows = soup.find_all('tr', attrs={'id': lambda x: x and x.startswith('a')})
                    
                    jingcai_data = {}
                    
                    for row in match_rows:
                        match_id = row.get('id')
                        if not match_id:
                            continue
                        
                        # 提取竞彩标识（来自第一列的文本，例如"周二011"）
                        tds = row.find_all('td')
                        if len(tds) > 0:
                            first_td = tds[0]
                            # 提取td中的文本，过滤掉复选框相关内容
                            jingcai_id = first_td.text.strip()
                            # 移除可能的空格和特殊字符
                            jingcai_id = jingcai_id.replace('\n', '').replace('\r', '').replace(' ', '')
                            
                            if jingcai_id:
                                jingcai_data[match_id] = jingcai_id
                    
                    self.jingcai_matches = jingcai_data
                    return jingcai_data
                    
        except asyncio.TimeoutError:
            print('请求超时，请稍后重试')
            return {}
        except aiohttp.ClientError as e:
            print(f'网络请求失败: {e}')
            return {}
        except Exception as e:
            print(f'抓取竞彩标识失败: {e}')
            import traceback
            traceback.print_exc()
            return {}
    
    def get_jingcai_id(self, match_id):
        """根据比赛ID获取竞彩标识"""
        return self.jingcai_matches.get(match_id, '')
    
    def render_jingcai_badge(self, match_id):
        """渲染竞彩标识徽章"""
        jingcai_id = self.get_jingcai_id(match_id)
        if not jingcai_id:
            return ''
        
        # 返回HTML格式的竞彩标识徽章（极简格式，避免被解析为代码块）
        return f'<span style="background:#F75000;color:white;padding:2px 6px;border-radius:4px;font-size:0.8em;font-weight:bold;">{jingcai_id}</span>'
    
    def update_matches_with_jingcai(self, matches):
        """将竞彩标识添加到比赛数据列表中"""
        if not matches:
            return matches
        
        updated_matches = []
        for match in matches:
            match_id = match.get('match_id', '')
            match['jingcai_id'] = self.get_jingcai_id(match_id)
            updated_matches.append(match)
        
        return updated_matches

# 创建全局实例，方便使用
global_jingcai_manager = JingcaiManager()

# 提供便捷函数
def crawl_jingcai_ids(url='https://live.500.com/'):
    """便捷函数：抓取竞彩标识（同步版本，内部调用异步实现）"""
    return asyncio.run(global_jingcai_manager.crawl_jingcai_ids(url))

async def async_crawl_jingcai_ids(url='https://live.500.com/'):
    """便捷函数：异步抓取竞彩标识"""
    return await global_jingcai_manager.crawl_jingcai_ids(url)

def get_jingcai_id(match_id):
    """便捷函数：获取竞彩标识"""
    return global_jingcai_manager.get_jingcai_id(match_id)

def render_jingcai_badge(match_id):
    """便捷函数：渲染竞彩标识徽章"""
    return global_jingcai_manager.render_jingcai_badge(match_id)

def update_matches_with_jingcai(matches):
    """便捷函数：将竞彩标识添加到比赛数据中"""
    return global_jingcai_manager.update_matches_with_jingcai(matches)

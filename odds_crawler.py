import re
import time
import requests
from bs4 import BeautifulSoup

# 配置参数
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1


def keep_only_chinese(text):
    """
    使用正则表达式筛选并只保留中文字符。
    """
    if not isinstance(text, str):
        return ""
    pattern = re.compile(r'[\u4e00-\u9fa5]')
    chinese_chars = pattern.findall(text)
    return ''.join(chinese_chars)


def make_request_with_retries(url, headers, retries=MAX_RETRIES, delay=RETRY_DELAY_SECONDS, timeout=15):
    """
    带有重试机制的同步请求函数。
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, verify=False)
            response.raise_for_status()
            # 读取内容并手动处理编码
            content = response.content
            try:
                text = content.decode('gb18030')
            except UnicodeDecodeError:
                text = content.decode('utf-8', errors='ignore')
            return text
        except requests.RequestException:
            if attempt < retries - 1:
                time.sleep(delay)
    return None


def fetch_oupei_data(match_id):
    """
    获取欧赔数据。
    """
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    url = f'https://odds.500.com/fenxi/ouzhi-{match_id}.shtml'
    res_text = make_request_with_retries(url, headers)
    if not res_text or "百家欧赔" not in res_text:
        return None

    try:
        soup = BeautifulSoup(res_text, 'lxml')
        data_table = soup.find('table', id='datatb')
        if not data_table:
            return None

        extracted_data = {}

        company_rows = data_table.find_all('tr', id=re.compile(r'^\d+$'))
        for row in company_rows:
            company_td = row.find('td', class_='tb_plgs')
            if not company_td or not company_td.has_attr('title'):
                continue
            # 直接使用网页中提取的公司名称，不再进行硬编码映射
            clean_company_name = company_td['title']
            odds_table = row.find('table', class_='pl_table_data')
            if odds_table:
                odds_rows = odds_table.find_all('tr')
                if len(odds_rows) == 2:
                    initial_tds = odds_rows[0].find_all('td')
                    instant_tds = odds_rows[1].find_all('td')
                    extracted_data[clean_company_name] = {
                        'initial': [d.get_text(strip=True) for d in initial_tds],
                        'instant': [d.get_text(strip=True) for d in instant_tds]
                    }
        return extracted_data
    except Exception:
        return None


def fetch_yapan_data(match_id):
    """
    获取亚盘数据。
    """
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    url = f'https://odds.500.com/fenxi/yazhi-{match_id}.shtml'
    res_text = make_request_with_retries(url, headers)
    if not res_text or "亚盘对比" not in res_text:
        return None

    try:
        soup = BeautifulSoup(res_text, 'lxml')
        data_table = soup.find('table', id='datatb')
        if not data_table:
            return None

        extracted_data = {}

        company_rows = data_table.find_all('tr', id=re.compile(r'^\d+$'))
        for row in company_rows:
            try:
                all_tds = row.find_all('td', recursive=False)
                if len(all_tds) < 6: continue
                company_link = all_tds[1].find('a')
                if not company_link or not company_link.has_attr('title'): continue
                # 直接使用网页中提取的公司名称，不再进行硬编码映射
                clean_company_name = company_link['title']
                instant_table = all_tds[2].find('table')
                initial_table = all_tds[4].find('table')

                if instant_table and initial_table:
                    instant_data = [d.get_text(strip=True) for d in instant_table.find_all('td')[:3]]
                    initial_data = [d.get_text(strip=True) for d in initial_table.find_all('td')[:3]]
                    if len(instant_data) == 3 and len(initial_data) == 3:
                        extracted_data[clean_company_name] = {
                            'initial': initial_data,
                            'instant': instant_data
                        }
            except (AttributeError, IndexError):
                continue
        return extracted_data
    except Exception:
        return None


def fetch_daxiao_data(match_id):
    """
    获取大小球数据。
    """
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    url = f'https://odds.500.com/fenxi/daxiao-{match_id}.shtml'
    res_text = make_request_with_retries(url, headers)
    if not res_text or "大小指数" not in res_text:
        return None

    try:
        soup = BeautifulSoup(res_text, 'lxml')
        data_table = soup.find('table', id='datatb')
        if not data_table:
            return None

        extracted_data = {}

        company_rows = data_table.find_all('tr', id=re.compile(r'^\d+$'))
        for row in company_rows:
            try:
                all_tds = row.find_all('td', recursive=False)
                if len(all_tds) < 6: continue
                company_link = all_tds[1].find('a')
                if not company_link or not company_link.has_attr('title'): continue
                # 直接使用网页中提取的公司名称，不再进行硬编码映射
                clean_company_name = company_link['title']
                instant_table = all_tds[2].find('table')
                initial_table = all_tds[4].find('table')

                if instant_table and initial_table:
                    instant_data = [d.get_text(strip=True) for d in instant_table.find_all('td')[:3]]
                    initial_data = [d.get_text(strip=True) for d in initial_table.find_all('td')[:3]]
                    if len(instant_data) == 3 and len(initial_data) == 3:
                        extracted_data[clean_company_name] = {
                            'initial': initial_data,
                            'instant': instant_data
                        }
            except (AttributeError, IndexError):
                continue
        return extracted_data
    except Exception:
        return None


def fetch_all_odds_data(match_id):
    """
    为单个ID获取所有赔率数据。
    """
    # 顺序获取所有赔率数据
    oupei_data = fetch_oupei_data(match_id)
    yapan_data = fetch_yapan_data(match_id)
    daxiao_data = fetch_daxiao_data(match_id)

    return {
        'oupei': oupei_data,
        'yapan': yapan_data,
        'daxiao': daxiao_data
    }

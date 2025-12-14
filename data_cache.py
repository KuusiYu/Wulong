"""
数据缓存模块 - 减少网络请求，提高性能
"""
import time
import json
import os
from typing import Dict, Any, Optional

class DataCache:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.cache_duration = 3600  # 缓存1小时
        
        # 确保缓存目录存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        # 移除特殊字符，避免文件名问题
        safe_key = ''.join(c for c in cache_key if c.isalnum() or c in ('-', '_'))
        return os.path.join(self.cache_dir, f"{safe_key}.json")
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """检查缓存是否有效"""
        if not os.path.exists(cache_path):
            return False
        
        # 检查文件修改时间
        file_age = time.time() - os.path.getmtime(cache_path)
        return file_age < self.cache_duration
    
    def get(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        cache_path = self._get_cache_path(cache_key)
        
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"从缓存加载数据: {cache_key}")
                return data
        except (IOError, json.JSONDecodeError) as e:
            print(f"缓存读取失败: {e}")
            return None
    
    def set(self, cache_key: str, data: Any) -> None:
        """保存数据到缓存"""
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"数据已缓存: {cache_key}")
        except (IOError, TypeError) as e:
            print(f"缓存保存失败: {e}")
    
    def clear(self) -> None:
        """清空所有缓存"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            print("缓存已清空")
        except IOError as e:
            print(f"清空缓存失败: {e}")
    
    def clear_old_cache(self) -> None:
        """清理过期缓存"""
        try:
            current_time = time.time()
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    cache_path = os.path.join(self.cache_dir, filename)
                    if current_time - os.path.getmtime(cache_path) > self.cache_duration:
                        os.remove(cache_path)
                        print(f"清理过期缓存: {filename}")
        except IOError as e:
            print(f"清理缓存失败: {e}")

# 全局缓存实例
global_cache = DataCache()

def get_cache_key(prefix: str, *args) -> str:
    """生成缓存键"""
    return f"{prefix}_{'_'.join(str(arg) for arg in args)}"
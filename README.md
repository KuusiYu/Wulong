# Wulong Football 2.0.0

一个足球赛事数据爬虫和可视化展示系统，使用Streamlit框架开发。

## 功能特性

- 实时爬取足球赛事数据
- 支持按日期查询历史赛事
- 展示比赛赔率数据
- 支持联赛和状态筛选
- 竞彩赛事标识
- 响应式设计，美观的比赛卡片展示

## 安装步骤

1. 克隆仓库到本地
   ```bash
   git clone <仓库地址>
   cd Wulong Football 2.0.0
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 运行应用
   ```bash
   streamlit run app.py
   ```

## 部署到GitHub Pages

由于Streamlit应用需要服务器运行，无法直接部署到GitHub Pages。建议使用以下方式部署：

### 方式1：使用Streamlit Cloud（推荐）

1. Fork本仓库到你的GitHub账号
2. 访问 [Streamlit Cloud](https://share.streamlit.io/)
3. 点击 "New app" 
4. 选择你的GitHub仓库
5. 选择分支（通常为main）
6. 选择主文件为 `app.py`
7. 点击 "Deploy"

### 方式2：使用Heroku

1. 创建Heroku账号
2. 安装Heroku CLI
3. 登录Heroku
   ```bash
   heroku login
   ```
4. 创建Heroku应用
   ```bash
   heroku create your-app-name
   ```
5. 部署应用
   ```bash
   git push heroku main
   ```

## 使用说明

1. 应用启动后，会自动爬取最新的足球赛事数据
2. 可以通过侧边栏选择联赛和比赛状态进行筛选
3. 可以勾选"只显示竞彩赛事"来筛选竞彩比赛
4. 点击"清除筛选条件"可以重置所有筛选
5. 点击"刷新"按钮可以重新爬取数据
6. 可以通过日期选择器查询历史赛事

## 项目结构

```
Wulong Football 2.0.0/
├── app.py              # 主应用文件
├── crawler.py          # 爬虫模块
├── date_manager.py     # 日期管理模块
├── history_crawler.py  # 历史数据爬虫模块
├── jczq_crawler.py     # 竞彩足球爬虫模块
├── jingcai_manager.py  # 竞彩标识管理模块
├── league_data.py      # 联赛数据模块
├── odds_crawler.py     # 赔率爬虫模块
├── ui.py               # UI组件模块
├── requirements.txt    # 依赖列表
└── README.md           # 项目说明
```

## 注意事项

1. 本项目仅用于学习和研究，请勿用于商业用途
2. 爬虫频率请勿过高，以免给目标网站造成压力
3. 数据来源可能随时变化，导致爬虫失效
4. 如有问题，请提交Issue或Pull Request

## 许可证

MIT License

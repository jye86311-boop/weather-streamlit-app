# 城市气象预警大屏 | City Weather Warning Dashboard

一个基于 Python 和 Streamlit 构建的城市气象查询与重点预警展示应用，支持城市天气查询、动态背景展示和全国重点预警信号看板。

A Streamlit-based weather dashboard for city-level weather lookup, dynamic visual backgrounds, and a national key-warning display.

---

## 在线体验 | Live Demo



[在线体验 / Live Demo](https://weather-app-app-xh6zah5padrzxe7bqoab9w.streamlit.app/)

---

## 项目截图 | Screenshot

> 在这里放一张项目运行截图。  
> Add a screenshot of the running app here.

<img width="2559" height="1344" alt="image" src="https://github.com/user-attachments/assets/c452957c-f882-41fc-bd5c-8b241ca0d3fd" />
<img width="2559" height="1341" alt="image" src="https://github.com/user-attachments/assets/d67dcdf0-5804-421d-8425-f571870bb1cf" />

---

## 功能特点 | Features

- 输入中文城市名，查询该城市实时天气信息
- 展示天气状况、体感温度、湿度、风速、降水量、能见度和气压
- 根据未来 3 天预报生成城市风险提示
- 首页展示全国红色、橙色重点预警信号，并按省份归类展示
- 同类区县预警合并显示，减少重复信息
- 根据北京时间自动切换白天 / 夜晚动态背景
- 使用玻璃拟态布局，适合气象监控大屏展示

- Search weather by Chinese city name
- Display current condition, feels-like temperature, humidity, wind speed, precipitation, visibility, and pressure
- Generate city-level risk hints from the next 3-day forecast
- Show national red and orange key warning signals on the home screen
- Merge similar county-level warning records to reduce duplicated information
- Automatically switch daytime / nighttime video backgrounds based on Beijing time
- Use a glassmorphism-style interface suitable for weather monitoring displays

---

## 技术栈 | Tech Stack

- Python
- Streamlit
- 和风天气 API / QWeather API
- Requests
- HTML / CSS
- GitHub
- Streamlit Community Cloud

---

## 本地运行 | Run Locally

### 1. 克隆或下载项目 | Clone or Download

```bash
git clone https://github.com/your-username/weather-streamlit-app.git
cd weather-streamlit-app
```

如果你是直接下载 ZIP 文件，解压后进入项目文件夹即可。  
If you download the ZIP file directly, unzip it and open the project folder.

### 2. 安装依赖 | Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. 配置天气 API | Configure Weather API

当前演示版本已经在 `app.py` 顶部设置了默认的和风天气 API 配置，因此下载后可以直接运行。  
The current demo version includes default QWeather API configuration near the top of `app.py`, so it can run directly after downloading.

如果你希望长期公开部署，建议改用 Streamlit Secrets 保存 API Key，避免额度被他人占用。  
For long-term public deployment, using Streamlit Secrets is recommended to avoid exposing or overusing your API quota.

可选的 Secrets 格式如下：  
Optional Secrets format:

```toml
QWEATHER_API_KEY = "your_qweather_api_key"
QWEATHER_API_HOST = "your_qweather_api_host"
```

### 4. 启动应用 | Start the App

```bash
streamlit run app.py
```

运行后，浏览器会自动打开本地页面。  
After running the command, the app will open in your browser.

---

## 部署说明 | Deployment

本项目可部署到 Streamlit Community Cloud。部署时填写：  
This project can be deployed on Streamlit Community Cloud. Use the following main file path:

```text
app.py
```

如果你使用代码中的默认 API 配置，一般不需要额外填写 Secrets。  
If you use the default API configuration in the code, extra Secrets are usually not required.

如果你改回安全模式，请在 Streamlit Cloud 的 `Settings -> Secrets` 中填写：  
If you switch back to the safer configuration, add the following values in `Settings -> Secrets`:

```toml
QWEATHER_API_KEY = "your_qweather_api_key"
QWEATHER_API_HOST = "your_qweather_api_host"
```

---

## 项目结构 | Project Structure

```text
weather-streamlit-app/
├── app.py
├── requirements.txt
├── README.md
└── assets/
    └── backgrounds/
        ├── 白天.mp4
        └── 夜晚_无缝循环.mp4
```

---

## 说明 | Notes

本项目使用和风天气 API 获取城市天气数据，并结合公开预警信息源展示全国重点预警信号。不同账号权限、网络环境或数据源可用性可能影响部分接口结果。  
This project uses QWeather API for city weather data and public warning sources for national key warning signals. API permissions, network conditions, and data source availability may affect some results.

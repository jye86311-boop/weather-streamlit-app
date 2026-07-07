[README.md](https://github.com/user-attachments/files/29733593/README.md)
# 城市气象预警大屏 | City Weather Warning Dashboard

一个基于 Streamlit 构建的城市天气查询与预警展示应用，支持实时天气、未来天气风险提示和动态背景展示。

A Streamlit-based weather dashboard for city-level weather lookup, real-time conditions, forecast-based alerts, and dynamic visual backgrounds.

---

## 在线体验 | Live Demo


https://weather-app-app-xh6zah5padrzxe7bqoab9w.streamlit.app/

---

## 项目截图 | Screenshot

<img width="2559" height="1344" alt="image" src="https://github.com/user-attachments/assets/58292320-a235-470c-84c6-2b172958de98" />




---

## 功能特点 | Features

- 输入中文城市名，查询该城市天气信息
- 展示当前天气状况、体感温度、湿度、风速、降水量、能见度和气压
- 根据未来 3 天天气预报生成城市风险提示
- 支持城市级天气预警信息展示
- 根据北京时间自动切换白天 / 夜晚动态背景
- 使用玻璃拟态卡片设计，适合展示型气象大屏

- Search weather by Chinese city name
- Display current weather, feels-like temperature, humidity, wind speed, precipitation, visibility, and pressure
- Generate city-level risk hints from the next 3-day forecast
- Show city weather warning information
- Automatically switch daytime / nighttime video backgrounds based on Beijing time
- Glassmorphism-style layout suitable for a weather monitoring dashboard

---

## 技术栈 | Tech Stack

- Python
- Streamlit
- 和风天气 API / QWeather API
- Plotly
- Requests
- HTML / CSS

---

## 本地运行 | Run Locally

### 1. 克隆或下载项目 | Clone or Download

`ash
git clone https://github.com/your-username/weather-streamlit-app.git
cd weather-streamlit-app
`

如果你是直接下载 ZIP 文件，解压后进入项目文件夹即可。  
If you download the ZIP file directly, unzip it and open the project folder.

### 2. 安装依赖 | Install Dependencies

`ash
pip install -r requirements.txt
`

### 3. 配置 API Key | Configure API Key

本项目不会把 API Key 写死在代码里。请在本地创建 .streamlit/secrets.toml 文件：  
This project does not hard-code the API key. Create a .streamlit/secrets.toml file locally:

`	oml
QWEATHER_API_KEY =  your_qweather_api_key
QWEATHER_API_HOST = your_qweather_api_host
`

示例：  
Example:

`	oml
QWEATHER_API_HOST = your-host.qweatherapi.com
`

请不要把真实 API Key 上传到 GitHub。  
Do not upload your real API key to GitHub.

### 4. 启动应用 | Start the App

`ash
streamlit run app.py
`

运行后，浏览器会自动打开本地页面。  
After running the command, the app will open in your browser.

---

## 部署说明 | Deployment

本项目可部署到 Streamlit Community Cloud。部署时请在应用设置的 Secrets 中填写：  
This project can be deployed on Streamlit Community Cloud. Add the following values in app Secrets:

`	oml
QWEATHER_API_KEY = your_qweather_api_key
QWEATHER_API_HOST = your_qweather_api_host
`

主文件路径填写：  
Main file path:

`	xt
app.py
`

---

## 项目结构 | Project Structure

`	xt
weather-streamlit-app/
├── app.py
├── requirements.txt
├── README.md
└── assets/
    └── backgrounds/
        ├── 白天.mp4
        └── 夜晚_无缝循环.mp4
`

---

## 说明 | Notes

本项目使用和风天气 API 获取天气数据。不同账号权限可能影响部分预警接口的可用性。  
This project uses QWeather API for weather data. Some warning endpoints may depend on your account permissions.

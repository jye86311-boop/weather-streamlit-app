# ===================== 可调参数 =====================
# 全国预警面板透明度：数值越大越不透明，越小越透明。
# 建议试验范围：0.35 - 0.75
NATIONAL_WARNING_GLASS_ALPHA = 0.1
# ====================================================

import os
import json
import html
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import streamlit as st



def 读取配置值(name, default=""):
    """优先从 Streamlit Secrets 读取配置，本地开发时再读取环境变量。"""
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


API_KEY = 读取配置值("QWEATHER_API_KEY","6054ace77ba14cd884a209cac9d696f2")
API_HOST = 读取配置值("QWEATHER_API_HOST", "m457rn9bm8.re.qweatherapi.com")


VIDEO_DIR = Path(__file__).parent / "assets" / "backgrounds"
DAY_VIDEO = VIDEO_DIR / "白天.mp4"
NIGHT_VIDEO = VIDEO_DIR / "夜晚_无缝循环.mp4"



@st.cache_data(show_spinner=False)
def 读取视频为_base64(video_path):
    """读取本地视频文件并转成网页能直接播放的 base64。"""
    # Streamlit 页面不能直接把本地路径当网页地址，所以这里转成内嵌视频数据。
    path = Path(video_path)
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def 选择背景视频():
    """根据当前时间选择白天或夜晚背景视频。"""
    # 早上 6 点到晚上 6 点用白天背景，其余时间用夜晚背景。
    china_time = datetime.now(timezone(timedelta(hours=8)))
    hour = china_time.hour
    if 6 <= hour < 18:
        return DAY_VIDEO
    return NIGHT_VIDEO


def 渲染动态背景():
    """在页面底层渲染循环播放的视频背景。"""
    # 视频设置为静音、自动播放、循环播放，作为网页背景使用。
    video_path = 选择背景视频()
    video_data = 读取视频为_base64(str(video_path))
    if not video_data:
        return

    st.markdown(
        f'''
<video class="page-bg-video" autoplay muted loop playsinline>
  <source src="data:video/mp4;base64,{video_data}" type="video/mp4">
</video>
<div class="page-bg-overlay"></div>
        ''',
        unsafe_allow_html=True,
    )


def 整理接口地址(host):
    """把 API Host 整理成可访问的网址。"""
    # 如果只写了域名，自动补上 https://。
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    return host


def 获取城市查询地址(host):
    """获取城市查询接口使用的地址。"""
    # 新版和风天气的专属 Host 可以同时用于 GeoAPI 和天气 API。
    return 整理接口地址(host)


def 检查接口配置(api_key, api_host):
    """检查 API Key 和 API Host 是否已经填写。"""
    # 如果还是占位文字，就不发起请求。
    return (
        api_key
        and api_host
        and "[粘贴你的Key]" not in api_key
        and "[粘贴你的Host]" not in api_host
    )


def 请求和风天气接口(base_url, path, params, api_key):
    """请求和风天气接口，并返回 JSON 数据。"""
    # 和风天气 API 需要把 key 放在请求参数里。
    response = requests.get(
        f"{base_url}{path}",
        params={**params, "key": api_key},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("接口返回的数据格式不正确。")

    if data.get("code") != "200":
        raise ValueError(f"和风天气接口返回错误：{data.get('code')}")

    return data


@st.cache_data(ttl=86400, show_spinner=False)
def 查询城市位置(city_name, api_key, api_host):
    """用中文城市名查询城市 LocationID。"""
    # 先把“北京”这样的城市名转换成接口能识别的城市 ID。
    data = 请求和风天气接口(
        获取城市查询地址(api_host),
        "/geo/v2/city/lookup",
        {"location": city_name, "range": "cn", "number": 1},
        api_key,
    )
    locations = data.get("location", [])
    if not locations:
        raise ValueError("没有找到这个城市，请检查城市名是否正确。")
    return locations[0]


@st.cache_data(ttl=300, show_spinner=False)
def 获取实时天气(location_id, api_key, api_host):
    """根据城市 LocationID 获取实时天气。"""
    # 实时天气包含温度、天气状况、湿度、风速、降水量等信息。
    data = 请求和风天气接口(
        整理接口地址(api_host),
        "/v7/weather/now",
        {"location": location_id},
        api_key,
    )
    return data["now"]




@st.cache_data(ttl=300, show_spinner=False)
def 获取三天预报(location_id, api_key, api_host):
    """根据城市 LocationID 获取未来 3 天预报。"""
    # 当官方预警接口没有权限时，用 3 天预报做简单风险提示。
    data = 请求和风天气接口(
        整理接口地址(api_host),
        "/v7/weather/3d",
        {"location": location_id},
        api_key,
    )
    return data.get("daily", [])

@st.cache_data(ttl=300, show_spinner=False)
def 获取城市预警(location_id, api_key, api_host):
    """根据城市 LocationID 获取当前生效的预警信号。"""
    # 这里使用官方预警接口，拿到的是气象部门发布的真实预警。
    data = 请求和风天气接口(
        整理接口地址(api_host),
        "/v7/warning/now",
        {"location": location_id},
        api_key,
    )
    return data.get("warning", [])


@st.cache_data(ttl=300, show_spinner=False)
def 获取全国重点预警():
    """从中国天气网预警频道读取全国红色和橙色预警，并按省份合并。"""
    # 这个接口是中国天气网预警页面使用的数据源，返回全国当前生效预警列表。
    url = f"https://product.weather.com.cn/alarm/grepalarm_cn.php?_={int(datetime.now(timezone.utc).timestamp() * 1000)}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.weather.com.cn/alarm/",
    }

    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        text = response.content.decode("utf-8", errors="ignore").strip()
        if text.startswith("var alarminfo="):
            text = text[len("var alarminfo="):]
        text = text.rstrip(";")
        data = json.loads(text)
    except Exception as error:
        return {
            "groups": [],
            "warnings": [],
            "total": 0,
            "red": 0,
            "orange": 0,
            "error": f"全国预警数据暂时无法读取：{error}",
        }

    rows = data.get("data", [])
    warnings = []
    red_count = 0
    orange_count = 0

    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            continue

        title = str(row[6])
        if "红色" in title:
            level = "红色"
            red_count += 1
        elif "橙色" in title:
            level = "橙色"
            orange_count += 1
        else:
            continue

        province, area = 提取省份和地区(str(row[0]))
        file_name = str(row[1])
        publish_time, sort_time = 解析预警发布时间(file_name)
        warnings.append(
            {
                "province": province,
                "area": area,
                "location": str(row[0]),
                "title": title,
                "level": level,
                "type": 提取预警类型(title, level),
                "publish_time": publish_time,
                "sort_time": sort_time,
            }
        )

    groups = 合并全国重点预警(warnings)

    return {
        "groups": groups,
        "warnings": warnings,
        "total": int(data.get("count") or len(rows)),
        "red": red_count,
        "orange": orange_count,
        "error": "",
    }


PROVINCE_PATTERNS = [
    ("内蒙古自治区", "内蒙古"),
    ("黑龙江省", "黑龙江"),
    ("广西壮族自治区", "广西"),
    ("宁夏回族自治区", "宁夏"),
    ("新疆维吾尔自治区", "新疆"),
    ("西藏自治区", "西藏"),
    ("香港特别行政区", "香港"),
    ("澳门特别行政区", "澳门"),
    ("北京市", "北京"),
    ("天津市", "天津"),
    ("上海市", "上海"),
    ("重庆市", "重庆"),
    ("河北省", "河北"),
    ("山西省", "山西"),
    ("辽宁省", "辽宁"),
    ("吉林省", "吉林"),
    ("江苏省", "江苏"),
    ("浙江省", "浙江"),
    ("安徽省", "安徽"),
    ("福建省", "福建"),
    ("江西省", "江西"),
    ("山东省", "山东"),
    ("河南省", "河南"),
    ("湖北省", "湖北"),
    ("湖南省", "湖南"),
    ("广东省", "广东"),
    ("海南省", "海南"),
    ("四川省", "四川"),
    ("贵州省", "贵州"),
    ("云南省", "云南"),
    ("陕西省", "陕西"),
    ("甘肃省", "甘肃"),
    ("青海省", "青海"),
    ("台湾省", "台湾"),
]

PROVINCE_PINYIN_ORDER = [
    "安徽",
    "北京",
    "重庆",
    "福建",
    "甘肃",
    "广东",
    "广西",
    "贵州",
    "海南",
    "河北",
    "河南",
    "黑龙江",
    "湖北",
    "湖南",
    "吉林",
    "江苏",
    "江西",
    "辽宁",
    "内蒙古",
    "宁夏",
    "青海",
    "山东",
    "山西",
    "陕西",
    "上海",
    "四川",
    "天津",
    "西藏",
    "新疆",
    "云南",
    "浙江",
    "香港",
    "澳门",
    "台湾",
]

PROVINCE_SORT_INDEX = {province: index for index, province in enumerate(PROVINCE_PINYIN_ORDER)}


def 提取省份和地区(location):
    """把完整地区名拆成省份和具体市县。"""
    # 例如“湖北省孝感市大悟县”会拆成“湖北”和“孝感市大悟县”。
    text = str(location).strip()
    for full_name, short_name in PROVINCE_PATTERNS:
        if text.startswith(full_name):
            area = text[len(full_name):].strip()
            return short_name, area or text
    return "其他", text


def 获取省份排序值(province):
    """按照省份拼音顺序返回排序值。"""
    return PROVINCE_SORT_INDEX.get(province, 999), province


def 合并全国重点预警(warnings):
    """把同省份、同类型、同等级的预警合并成一条展示卡片。"""
    grouped = {}
    for warning in warnings:
        key = (warning["province"], warning["type"], warning["level"])
        if key not in grouped:
            grouped[key] = {
                "province": warning["province"],
                "type": warning["type"],
                "level": warning["level"],
                "areas": [],
                "area_set": set(),
                "latest_time": warning["publish_time"],
                "sort_time": warning["sort_time"],
            }

        group = grouped[key]
        area = warning["area"] or warning["location"]
        if area not in group["area_set"]:
            group["areas"].append(area)
            group["area_set"].add(area)
        if warning["sort_time"] > group["sort_time"]:
            group["sort_time"] = warning["sort_time"]
            group["latest_time"] = warning["publish_time"]

    result = []
    for group in grouped.values():
        group.pop("area_set", None)
        group["count"] = len(group["areas"])
        result.append(group)

    result.sort(
        key=lambda item: (
            *获取省份排序值(item["province"]),
            -item["sort_time"],
            item["type"],
            item["level"],
        )
    )
    return result


def 解析预警发布时间(file_name):
    """从预警详情文件名中解析发布时间。"""
    # 文件名通常类似 1010413-20260717152420-0201.html，中间 14 位是发布时间。
    for part in str(file_name).split("-"):
        candidate = part[:14]
        if len(candidate) == 14 and candidate.isdigit():
            try:
                dt = datetime.strptime(candidate, "%Y%m%d%H%M%S")
                return dt.strftime("%m-%d %H:%M"), int(candidate)
            except ValueError:
                pass
    return "时间未知", 0


def 提取预警类型(title, level):
    """从预警标题中提取暴雨、高温、强对流等类型名称。"""
    # 标题通常是“某地发布暴雨橙色预警信号”，这里保留中间的天气灾害类型。
    text = str(title)
    if "发布" in text:
        text = text.split("发布", 1)[1]
    text = text.replace(level, "")
    text = text.replace("预警信号", "")
    text = text.replace("预警", "")
    return text.strip() or "气象"


def 获取天气图标(weather_text):
    """根据天气文字选择一个简单图标。"""
    # 用轻量 emoji 做视觉提示，不需要额外素材。
    if "雷" in weather_text:
        return "⛈️"
    if "雨" in weather_text:
        return "🌧️"
    if "雪" in weather_text:
        return "❄️"
    if "阴" in weather_text:
        return "☁️"
    if "云" in weather_text:
        return "🌤️"
    if "晴" in weather_text:
        return "☀️"
    if "雾" in weather_text or "霾" in weather_text:
        return "🌫️"
    return "🌡️"


def 获取预警颜色(warning):
    """根据预警级别选择展示颜色。"""
    # 和风天气通常会返回 severityColor；如果没有，就从标题文字里猜一个颜色。
    color_text = str(warning.get("severityColor") or warning.get("level") or warning.get("title") or "")
    color_text = color_text.lower()
    if "red" in color_text or "红" in color_text:
        return "#ef4444"
    if "orange" in color_text or "橙" in color_text:
        return "#f97316"
    if "yellow" in color_text or "黄" in color_text:
        return "#eab308"
    if "blue" in color_text or "蓝" in color_text:
        return "#3b82f6"
    return "#64748b"




def 根据三天预报生成风险提示(daily_forecasts):
    """官方预警接口不可用时，用未来 3 天预报生成简单风险提示。"""
    # 这不是气象部门正式预警，只是基于预报字段做的辅助提示。
    risk_items = []
    rain_keywords = ["暴雨", "大雨", "雷暴"]

    for day in daily_forecasts[:3]:
        date_text = day.get("fxDate", "未来日期")
        day_text = day.get("textDay", "")
        night_text = day.get("textNight", "")
        max_temp = 转成小数(day.get("tempMax"), default=-999)

        if max_temp >= 35:
            risk_items.append(
                {
                    "title": f"高温风险提示：{date_text} 最高气温 {max_temp:g}℃",
                    "sender": "",
                    "pubTime": "",
                    "severityColor": "yellow",
                }
            )

        weather_text = f"{day_text} {night_text}"
        if any(keyword in weather_text for keyword in rain_keywords):
            risk_items.append(
                {
                    "title": f"降水风险提示：{date_text} {day_text}/{night_text}",
                    "sender": "",
                    "pubTime": "",
                    "severityColor": "blue",
                }
            )

    return risk_items

def 转成小数(value, default=0.0):
    """把接口里的数字安全转成小数。"""
    # 降水量、风速等字段可能是字符串。
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def 判断降水状态(now):
    """根据天气文字和降水量生成更接近体感的降水描述。"""
    # 单看 precip 可能显示 0.0，所以同时参考天气现象文字。
    precip = 转成小数(now.get("precip"))
    weather_text = now.get("text", "")
    if precip > 0:
        return f"有降水 · {precip:g} mm"
    if "雨" in weather_text:
        return "有降水迹象"
    return "无明显降水"




def 清空查询状态():
    """清空当前查询状态，回到初始输入页面。"""
    # 关闭结果页时，同时清掉网址里的城市参数，避免页面重新触发查询。
    st.session_state.show_weather_card = False
    st.session_state.last_city_name = ""
    st.session_state.city_input = ""
    try:
        st.query_params.clear()
    except Exception:
        pass
def 渲染预警列表(warnings, source_note=""):
    """把城市预警或风险提示列表整理成左侧卡片里的 HTML。"""
    # 官方接口可用时显示正式预警；不可用时显示规则推算的风险提示。
    parts = []
    if source_note:
        parts.append(f'<div class="warning-source">{html.escape(source_note)}</div>')

    if not warnings:
        parts.append('<div class="warning-empty">暂无生效预警或明显风险</div>')
        return "".join(parts)

    for warning in warnings[:3]:
        title = html.escape(warning.get("title") or f"{warning.get('typeName', '天气')}预警")
        sender = html.escape(warning.get("sender") or "气象部门")
        pub_time = html.escape(warning.get("pubTime") or warning.get("startTime") or "")
        color = 获取预警颜色(warning)
        parts.append(
            f'<div class="warning-item" style="border-left-color: {color};">'
            f'<div class="warning-name">{title}</div>'
            f'{f"<div class=\"warning-meta\">{sender}</div>" if sender else ""}'
            f'{f"<div class=\"warning-meta\">{pub_time}</div>" if pub_time else ""}'
            f'</div>'
        )

    if len(warnings) > 3:
        parts.append(f'<div class="warning-more">另有 {len(warnings) - 3} 条预警或风险</div>')

    return "".join(parts)

def 应用极简样式():
    """设置极简居中页面样式。"""
    # 初始页保持干净，结果面板做成浮层式白色大卡片。
    st.markdown(
        """
<style>
.stApp {
    background: transparent;
    color: #0f172a;
}
.page-bg-video {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    object-fit: cover;
    z-index: -3;
}
.page-bg-overlay {
    position: fixed;
    inset: 0;
    background: linear-gradient(120deg, rgba(255,255,255,0.50), rgba(226,232,240,0.18));
    backdrop-filter: blur(1px);
    z-index: -2;
    pointer-events: none;
}
[data-testid="stHeader"] {
    background: transparent;
}
.block-container {
    max-width: 1080px !important;
    width: 100% !important;
    min-height: 100vh !important;
    padding: 0 !important;
    position: relative;
    z-index: 1;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stAppViewBlockContainer"] {
    min-height: 100vh !important;
    padding: 0 !important;
}
section[data-testid="stMain"] > div {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
div[data-testid="stTextInput"] label {
    display: none;
}
.st-key-search_glass {
    width: min(820px, calc(100vw - 56px));
    margin: 0 auto;
    padding: 46px 54px 34px 54px;
    border-radius: 34px;
    background: rgba(255, 255, 255, 0.42);
    border: 1px solid rgba(255, 255, 255, 0.72);
    box-shadow: 0 30px 90px rgba(15, 23, 42, 0.18);
    backdrop-filter: blur(18px) saturate(140%);
}
.st-key-search_glass [data-testid="stHorizontalBlock"] {
    align-items: center;
    gap: 18px;
}
.st-key-search_glass [data-testid="column"] {
    display: flex;
    flex-direction: column;
    align-items: center;
}
.st-key-search_glass [data-testid="column"]:nth-of-type(2) {
    justify-content: flex-start;
}
.st-key-search_glass .search-title {
    color: #08111f;
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    text-shadow: 0 2px 18px rgba(255, 255, 255, 0.55);
    font-size: 40px;
    line-height: 1.16;
    font-weight: 900;
    letter-spacing: 0;
    text-align: left;
    white-space: nowrap;
}
.st-key-search_glass div[data-testid="stTextInput"] {
    width: 240px !important;
    max-width: 240px !important;
    min-height: 58px;
    margin: 0 !important;
    overflow: visible;
}
.st-key-search_glass div[data-testid="stTextInput"] > div,
.st-key-search_glass div[data-baseweb="input"] {
    width: 240px !important;
    height: 58px !important;
    border-radius: 9999px !important;
}
.st-key-search_glass div[data-baseweb="input"] {
    overflow: hidden !important;
    background: rgba(255, 255, 255, 0.88) !important;
    border: 1px solid rgba(255, 255, 255, 0.94) !important;
    box-shadow: 0 18px 46px rgba(15, 23, 42, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.90) !important;
}
.st-key-search_glass div[data-testid="stTextInput"] input {
    width: 240px !important;
    height: 58px !important;
    border: 0 !important;
    border-radius: 9999px !important;
    background: transparent !important;
    color: #0f172a !important;
    text-align: center !important;
    font-size: 22px !important;
    line-height: 58px !important;
    padding: 0 22px !important;
    box-shadow: none !important;
}
.st-key-search_glass div[data-testid="stTextInput"] input::placeholder {
    color: #9ca3af !important;
}
.st-key-search_glass div[data-testid="stTextInput"] input:focus {
    outline: none !important;
    box-shadow: none !important;
}
.st-key-search_glass .hint-text {
    color: #64748b;
    text-align: center;
    font-size: 15px;
    margin-top: 0;
}
.weather-panel {
    margin: 0 auto;
    max-width: 980px;
    border-radius: 42px;
    background: #f7f7fb;
    box-shadow: 0 34px 90px rgba(15, 23, 42, 0.22);
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.88);
}
.weather-panel-grid {
    display: grid;
    grid-template-columns: 33% 67%;
    min-height: 520px;
}
.weather-panel-left {
    background: #ffffff;
    padding: 42px 44px;
}
.weather-panel-right {
    background: #f4f4f8;
    padding: 48px 44px 42px 44px;
}
.weather-basic-card {
    background: #ffffff;
    border-radius: 28px;
    padding: 2px 0 8px 0;
}
.weather-location {
    color: #0f172a;
    font-size: 21px;
    font-weight: 800;
    margin-bottom: 30px;
}
.weather-hero-icon {
    font-size: 138px;
    line-height: 1;
    text-align: center;
    margin: 18px 0 28px 0;
}
.weather-basic-info {
    display: grid;
    gap: 14px;
    margin-top: 8px;
}
.weather-main-text {
    color: #020617;
    font-size: 34px;
    line-height: 1.1;
    font-weight: 900;
    text-align: center;
}
.weather-sub-text {
    color: #64748b;
    font-size: 17px;
    line-height: 1.4;
    font-weight: 700;
    text-align: center;
}
.weather-divider {
    height: 1px;
    background: #e5e7eb;
    margin: 28px 0;
}
.warning-title {
    color: #0f172a;
    font-size: 20px;
    font-weight: 900;
    margin: 0 0 14px 0;
}
.warning-source {
    color: #64748b;
    font-size: 13px;
    font-weight: 700;
    margin: -4px 0 12px 0;
}
.warning-empty {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    color: #64748b;
    font-size: 15px;
    font-weight: 700;
    padding: 18px 20px;
}
.warning-item {
    background: #f8fafc;
    border-left: 6px solid #64748b;
    border-radius: 16px;
    padding: 14px 16px;
    margin: 12px 0;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}
.warning-name {
    color: #0f172a;
    font-size: 15px;
    font-weight: 900;
    line-height: 1.35;
}
.warning-meta,
.warning-more {
    color: #64748b;
    font-size: 12px;
    margin-top: 6px;
    line-height: 1.35;
}
.highlight-title {
    color: #0f172a;
    font-size: 23px;
    font-weight: 900;
    margin: 0 0 22px 0;
}
.highlight-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
}
.highlight-card {
    background: #ffffff;
    border-radius: 24px;
    padding: 24px;
    min-height: 138px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.04);
}
.highlight-label {
    color: #a1a1aa;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 20px;
}
.highlight-value {
    color: #020617;
    font-size: 40px;
    line-height: 1;
    font-weight: 400;
}
.highlight-unit {
    font-size: 18px;
    color: #111827;
    margin-left: 4px;
}
.highlight-note {
    color: #64748b;
    font-size: 14px;
    margin-top: 18px;
}
.st-key-weather_close_button {
    max-width: 980px;
    height: 58px;
    margin: 0 auto -58px auto;
    padding: 18px 26px 0 0;
    position: relative;
    z-index: 30;
}
.st-key-weather_close_button div[data-testid="stButton"] {
    display: flex;
    justify-content: flex-end;
}
.st-key-weather_close_button button {
    border-radius: 999px !important;
    width: 42px !important;
    height: 42px !important;
    min-height: 42px !important;
    padding: 0 !important;
    font-size: 24px !important;
    line-height: 1 !important;
    border: 0 !important;
    background: #ffffff !important;
    color: #111827 !important;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.14) !important;
    pointer-events: auto !important;
    transform: translate(-18px, 0);
}
.st-key-weather_close_button button:hover {
    background: #f3f4f6 !important;
    color: #000000 !important;
}
@media (max-width: 760px) {
    .block-container { padding-top: 0; padding-bottom: 0; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .st-key-search_glass { width: min(94vw, 640px); padding: 30px 28px; border-radius: 26px; }
    .st-key-search_glass [data-testid="stHorizontalBlock"] { gap: 16px; }
    .st-key-search_glass .search-title { text-align: left; font-size: 30px; line-height: 1.18; white-space: normal; }
    .st-key-search_glass div[data-testid="stTextInput"] { width: 200px !important; max-width: 200px !important; margin: 0 !important; }
    .st-key-search_glass div[data-testid="stTextInput"] > div,
    .st-key-search_glass div[data-baseweb="input"],
    .st-key-search_glass div[data-testid="stTextInput"] input { width: 200px !important; }
    .st-key-search_glass .hint-text { margin-top: 18px; }
    .st-key-weather_close_button { margin: 0 auto -58px auto; padding-right: 18px; }
    .weather-panel { margin-top: 0; border-radius: 26px; }
    .weather-panel-grid { grid-template-columns: 1fr; }
    .weather-panel-left, .weather-panel-right { padding: 28px; }
    .highlight-grid { grid-template-columns: 1fr; }
}



/* National warning dashboard homepage */
.st-key-search_glass {
    position: fixed !important;
    top: 28px !important;
    left: 32px !important;
    z-index: 20 !important;
    width: 540px !important;
    max-width: calc(100vw - 64px) !important;
    margin: 0 !important;
    padding: 20px 24px 18px 24px !important;
    border-radius: 28px !important;
    background: rgba(255, 255, 255, 0.44) !important;
    border: 1px solid rgba(255, 255, 255, 0.78) !important;
    box-shadow: 0 24px 70px rgba(15, 23, 42, 0.18) !important;
    backdrop-filter: blur(18px) saturate(145%) !important;
}
.st-key-search_glass [data-testid="stHorizontalBlock"] {
    gap: 12px !important;
}
.st-key-search_glass .search-title {
    font-size: 24px !important;
    line-height: 1.16 !important;
    white-space: nowrap !important;
    text-align: left !important;
}
.st-key-search_glass div[data-testid="stTextInput"] {
    width: 150px !important;
    max-width: 150px !important;
    min-height: 48px !important;
}
.st-key-search_glass div[data-testid="stTextInput"] > div,
.st-key-search_glass div[data-baseweb="input"] {
    width: 150px !important;
    height: 48px !important;
}
.st-key-search_glass div[data-testid="stTextInput"] input {
    width: 150px !important;
    height: 48px !important;
    font-size: 18px !important;
    padding: 0 18px !important;
}
.st-key-search_glass .hint-text {
    margin-top: 8px !important;
    font-size: 12px !important;
    text-align: center !important;
}
.national-warning-glass {
    width: min(980px, calc(100vw - 96px));
    max-height: min(70vh, 700px);
    margin: 0 auto;
    padding: 26px;
    border-radius: 34px;
    background: rgba(255, 255, 255, 0.46);
    border: 1px solid rgba(255, 255, 255, 0.78);
    box-shadow: 0 30px 90px rgba(15, 23, 42, 0.20);
    backdrop-filter: blur(18px) saturate(145%);
}
.national-warning-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 18px;
}
.national-warning-title {
    color: #08111f;
    font-size: 32px;
    line-height: 1.1;
    font-weight: 900;
    letter-spacing: 0;
}
.national-warning-subtitle {
    margin-top: 8px;
    color: #475569;
    font-size: 14px;
    font-weight: 600;
}
.national-warning-counts {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
    min-width: 270px;
}
.national-badge {
    display: inline-flex;
    align-items: center;
    height: 30px;
    padding: 0 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 800;
    white-space: nowrap;
}
.badge-red {
    color: #991b1b;
    background: rgba(254, 226, 226, 0.86);
}
.badge-orange {
    color: #9a3412;
    background: rgba(255, 237, 213, 0.90);
}
.badge-total {
    color: #334155;
    background: rgba(248, 250, 252, 0.88);
}
.national-warning-list {
    margin-top: 20px;
    max-height: calc(min(70vh, 700px) - 128px);
    overflow-y: auto;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    padding: 2px 6px 2px 0;
}
.national-warning-list::-webkit-scrollbar {
    width: 8px;
}
.national-warning-list::-webkit-scrollbar-thumb {
    background: rgba(100, 116, 139, 0.35);
    border-radius: 999px;
}
.national-warning-item {
    min-height: 122px;
    padding: 13px 14px 12px 16px;
    border-radius: 18px;
    border-left: 6px solid #f97316;
    background: rgba(255, 255, 255, 0.72);
    box-shadow: 0 14px 36px rgba(15, 23, 42, 0.09);
}
.national-warning-item.level-red {
    border-left-color: #ef4444;
    background: rgba(254, 242, 242, 0.82);
}
.national-warning-item.level-orange {
    border-left-color: #f97316;
    background: rgba(255, 247, 237, 0.82);
}
.national-warning-item-top {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    color: #64748b;
    font-size: 12px;
    font-weight: 800;
}
.national-warning-province {
    color: #0f172a;
}
.national-warning-time {
    color: #64748b;
    white-space: nowrap;
}
.national-warning-type {
    margin-top: 8px;
    color: #0f172a;
    font-size: 17px;
    line-height: 1.2;
    font-weight: 900;
}
.national-warning-areas {
    margin-top: 9px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.national-warning-area-chip {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    min-height: 24px;
    padding: 3px 9px;
    border-radius: 999px;
    color: #475569;
    background: rgba(255, 255, 255, 0.74);
    border: 1px solid rgba(226, 232, 240, 0.88);
    font-size: 12px;
    line-height: 1.25;
    font-weight: 700;
}
.national-warning-area-chip.more {
    color: #0f172a;
    background: rgba(241, 245, 249, 0.88);
}
.national-warning-empty {
    margin-top: 20px;
    padding: 28px;
    border-radius: 20px;
    color: #475569;
    background: rgba(255, 255, 255, 0.72);
    text-align: center;
    font-weight: 800;
}
@media (max-width: 980px), (max-height: 760px) {
    .st-key-search_glass {
        position: relative !important;
        top: auto !important;
        left: auto !important;
        width: min(94vw, 560px) !important;
        margin: 20px auto 18px auto !important;
    }
    .national-warning-glass {
        width: min(94vw, 760px);
        max-height: 62vh;
    }
    .national-warning-head {
        align-items: flex-start;
        flex-direction: column;
    }
    .national-warning-counts {
        justify-content: flex-start;
        min-width: 0;
    }
    .national-warning-list {
        grid-template-columns: 1fr;
        max-height: calc(62vh - 152px);
    }
}

/* Cloud layout overrides */
.block-container {
    max-width: 1080px !important;
    width: 100% !important;
    min-height: 100vh !important;
    padding: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stAppViewBlockContainer"] {
    min-height: 100vh !important;
    padding: 0 !important;
}
.weather-panel {
    width: min(980px, calc(100vw - 48px)) !important;
    max-width: min(980px, calc(100vw - 48px)) !important;
    margin: 0 auto !important;
}
.st-key-weather_close_button {
    width: min(980px, calc(100vw - 48px)) !important;
    max-width: min(980px, calc(100vw - 48px)) !important;
    height: 0 !important;
    margin: 0 auto -42px auto !important;
    padding: 0 !important;
    position: relative !important;
    top: 24px !important;
    z-index: 1000 !important;
    pointer-events: none !important;
}
.st-key-weather_close_button div[data-testid="stButton"] {
    width: 100% !important;
    display: flex !important;
    justify-content: flex-end !important;
    pointer-events: none !important;
}
.st-key-weather_close_button button {
    pointer-events: auto !important;
    transform: translate(-18px, 0) !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def 渲染天气浮层(city, now, warnings, warning_source_note=""):
    """把城市实时天气和预警信号渲染成浮层式天气面板。"""
    # 少量 HTML 用于完成类似参考图的左右分栏视觉。
    city_name = html.escape(city.get("name", "未知城市"))
    province = html.escape(city.get("adm1", ""))
    weather_text = html.escape(now.get("text", "-"))
    icon = 获取天气图标(now.get("text", ""))
    rain_state = html.escape(判断降水状态(now))
    warning_html = 渲染预警列表(warnings, warning_source_note)


    panel_html = (
        '<div class="weather-panel"><div class="weather-panel-grid">'
        '<section class="weather-panel-left">'
        '<div class="weather-basic-card">'
        f'<div class="weather-location">⌕ {province} {city_name}</div>'
        f'<div class="weather-hero-icon">{icon}</div>'
        '<div class="weather-basic-info">'
        f'<div class="weather-main-text">{weather_text}</div>'
        f'<div class="weather-sub-text">💧 {rain_state}</div>'
        '</div></div>'
        '<div class="weather-divider"></div>'
        '<div class="warning-title">当前城市预警</div>'
        f'{warning_html}'
        '</section>'
        '<section class="weather-panel-right">'
        '<div class="highlight-title">当前天气详情</div>'
        '<div class="highlight-grid">'
        '<div class="highlight-card">'
        '<div class="highlight-label">Feels Like</div>'
        f'<div class="highlight-value">{html.escape(str(now.get("feelsLike", "-")))}<span class="highlight-unit">°C</span></div>'
        '<div class="highlight-note">体感温度</div>'
        '</div>'
        '<div class="highlight-card">'
        '<div class="highlight-label">Wind Status</div>'
        f'<div class="highlight-value">{html.escape(str(now.get("windSpeed", "-")))}<span class="highlight-unit">km/h</span></div>'
        f'<div class="highlight-note">{html.escape(str(now.get("windDir", "-")))}</div>'
        '</div>'
        '<div class="highlight-card">'
        '<div class="highlight-label">Humidity</div>'
        f'<div class="highlight-value">{html.escape(str(now.get("humidity", "-")))}<span class="highlight-unit">%</span></div>'
        '<div class="highlight-note">相对湿度</div>'
        '</div>'
        '<div class="highlight-card">'
        '<div class="highlight-label">Precipitation</div>'
        f'<div class="highlight-value">{html.escape(str(now.get("precip", "-")))}<span class="highlight-unit">mm</span></div>'
        '<div class="highlight-note">当前站点降水</div>'
        '</div>'
        '<div class="highlight-card">'
        '<div class="highlight-label">Visibility</div>'
        f'<div class="highlight-value">{html.escape(str(now.get("vis", "-")))}<span class="highlight-unit">km</span></div>'
        '<div class="highlight-note">能见度</div>'
        '</div>'
        '<div class="highlight-card">'
        '<div class="highlight-label">Pressure</div>'
        f'<div class="highlight-value">{html.escape(str(now.get("pressure", "-")))}<span class="highlight-unit">hPa</span></div>'
        '<div class="highlight-note">大气压</div>'
        '</div>'
        '</div></section></div></div>'
    )
    st.markdown(panel_html, unsafe_allow_html=True)


def 渲染全国预警首页(result):
    """在首页中间渲染全国红色和橙色预警列表。"""
    groups = result.get("groups", [])
    total = result.get("total", 0)
    red_count = result.get("red", 0)
    orange_count = result.get("orange", 0)
    error = result.get("error", "")
    key_count = red_count + orange_count

    if error:
        body_html = f'<div class="national-warning-empty">{html.escape(error)}</div>'
    elif not groups:
        body_html = '<div class="national-warning-empty">当前暂无红色或橙色预警信号</div>'
    else:
        items = []
        for group in groups:
            level_class = "level-red" if group["level"] == "红色" else "level-orange"
            areas = group.get("areas", [])
            visible_areas = areas[:12]
            area_chips = "".join(
                f'<span class="national-warning-area-chip">{html.escape(area)}</span>'
                for area in visible_areas
            )
            if len(areas) > len(visible_areas):
                area_chips += f'<span class="national-warning-area-chip more">+{len(areas) - len(visible_areas)} 个地区</span>'

            items.append(
                f'<article class="national-warning-item {level_class}">'
                f'<div class="national-warning-item-top">'
                f'<span class="national-warning-province">{html.escape(group["province"])}</span>'
                f'<span class="national-warning-time">涉及 {group["count"]} 地 · 最新 {html.escape(group["latest_time"])}</span>'
                f'</div>'
                f'<div class="national-warning-type">{html.escape(group["type"])}{html.escape(group["level"])}预警</div>'
                f'<div class="national-warning-areas">{area_chips}</div>'
                f'</article>'
            )
        body_html = '<div class="national-warning-list">' + "".join(items) + "</div>"

    panel_html = (
        f'<section class="national-warning-glass" style="background: rgba(255, 255, 255, {NATIONAL_WARNING_GLASS_ALPHA});">'
        '<div class="national-warning-head">'
        '<div>'
        '<div class="national-warning-title">全国预警信号</div>'
        '<div class="national-warning-subtitle">按省份拼音排序</div>'
        '</div>'
        '<div class="national-warning-counts">'
        f'<span class="national-badge badge-red">红色 {red_count}</span>'
        f'<span class="national-badge badge-orange">橙色 {orange_count}</span>'
        f'<span class="national-badge badge-total">重点 {key_count} / 全部 {total}</span>'
        '</div>'
        '</div>'
        f'{body_html}'
        '</section>'
    )
    st.markdown(panel_html, unsafe_allow_html=True)


def 主程序():
    """运行极简天气查询网页。"""
    # 输入城市后保存查询结果；关闭按钮只隐藏卡片，不清空输入框。
    st.set_page_config(page_title="极简天气", page_icon="☁️", layout="centered")
    渲染动态背景()
    应用极简样式()

    if "show_weather_card" not in st.session_state:
        st.session_state.show_weather_card = False
    if "last_city_name" not in st.session_state:
        st.session_state.last_city_name = ""
    if "city_input" not in st.session_state:
        st.session_state.city_input = ""

    query_city = st.query_params.get("city", "")
    if isinstance(query_city, list):
        query_city = query_city[0] if query_city else ""
    query_city = str(query_city).strip()

    if query_city and not st.session_state.show_weather_card:
        st.session_state.show_weather_card = True
        st.session_state.last_city_name = query_city

    if st.session_state.show_weather_card and st.session_state.last_city_name:
        st.markdown(
            "<style>.block-container { padding: 0 !important; min-height: 100vh !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; }</style>",
            unsafe_allow_html=True,
        )
        city_name = st.session_state.last_city_name
    else:
        with st.container(key="search_glass"):
            title_col, input_col = st.columns([0.64, 0.36], vertical_alignment="center")
            with title_col:
                st.markdown('<div class="search-title">想看哪座城市的天气？</div>', unsafe_allow_html=True)
            with input_col:
                st.text_input("城市", placeholder="例如：厦门", label_visibility="collapsed", key="city_input")
            st.markdown('<div class="hint-text">输入城市后按 Enter 查看天气</div>', unsafe_allow_html=True)
            city_name = st.session_state.city_input

        if not city_name.strip():
            st.session_state.show_weather_card = False
            st.session_state.last_city_name = ""
            national_warning_result = 获取全国重点预警()
            渲染全国预警首页(national_warning_result)
            return

        st.session_state.show_weather_card = True
        st.session_state.last_city_name = city_name.strip()
        st.rerun()

    if not 检查接口配置(API_KEY, API_HOST):
        st.error("请先在 app.py 顶部填写你的和风天气 API Key 和 API Host。")
        return

    if st.session_state.show_weather_card:
        try:
            with st.spinner("正在查询天气..."):
                city = 查询城市位置(city_name.strip(), API_KEY, API_HOST)
                now = 获取实时天气(city["id"], API_KEY, API_HOST)
                try:
                    warnings = 获取城市预警(city["id"], API_KEY, API_HOST)
                    warning_source_note = "官方预警接口"
                except Exception:
                    daily_forecasts = 获取三天预报(city["id"], API_KEY, API_HOST)
                    warnings = 根据三天预报生成风险提示(daily_forecasts)
                    warning_source_note = ""
            with st.container(key="weather_close_button"):
                st.button("×", key="close_weather_card", help="关闭天气卡片", on_click=清空查询状态)
            渲染天气浮层(city, now, warnings, warning_source_note)
        except requests.exceptions.RequestException as error:
            st.error(f"网络请求失败：{error}")
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"程序遇到未知错误：{error}")
    else:
        st.markdown('<div class="hint-text">天气卡片已关闭，修改城市名可重新打开</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    主程序()
"""
ESP32C3 + SSD1306 OLED 时钟
- 第一行：日期      2026-10-24
- 第二行：星期      星期六
- 第三行：大号时间  12:34（冒号每秒闪烁）
- 开机通过 WiFi + NTP 自动校时（东八区）

接线：SCL = GPIO 6, SDA = GPIO 5, I2C 地址 0x3C
"""

import time
import network
import ntptime
from machine import SoftI2C, Pin, RTC
import framebuf

# ====== 加载 OLED 驱动（使用独立命名空间，避免触发测试代码） ======
_ns = dict(globals())
_ns['__name__'] = 'oled_driver'
exec(open('oled_driver.py').read(), _ns)
SSD1306_I2C = _ns['SSD1306_I2C']

# ====== 加载字库：中文 16x16 + 时钟数字 24x32 ======
from fonts_zh import FONT_ZH, FONT_TIME24

# ====== 配置 ======
WIFI_SSID = "你的WiFi名称"
WIFI_PASSWORD = "你的WiFi密码"
TZ_OFFSET = 8 * 3600                                   # 东八区 UTC+8
FALLBACK_TIME = (2026, 1, 1, 3, 0, 0, 0, 0)            # 校时失败时的显示时间（周四）
WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

# WiFi 对象（主循环中要读取信号强度，保持全局）
wlan = network.WLAN(network.STA_IF)
wlan.active(True)


def _utf8_key(char):
    """获取字符的 UTF-8 编码值（用作字库字典的 key）"""
    cp = ord(char)
    if cp < 0x80:
        return cp
    elif cp < 0x800:
        b1 = 0xC0 | (cp >> 6)
        b2 = 0x80 | (cp & 0x3F)
        return (b1 << 8) | b2
    else:
        b1 = 0xE0 | (cp >> 12)
        b2 = 0x80 | ((cp >> 6) & 0x3F)
        b3 = 0x80 | (cp & 0x3F)
        return (b1 << 16) | (b2 << 8) | b3


def show_chinese(text, x, y):
    """显示 16x16 中文字符串"""
    for char in text:
        data = FONT_ZH.get(_utf8_key(char))
        if data:
            fb = framebuf.FrameBuffer(bytearray(data), 16, 16, framebuf.MONO_VLSB)
            oled.blit(fb, x, y)
        x += 16


def show_time(text, x, y, show_colon=True):
    """显示 24x32 大号时间，冒号可按秒闪烁"""
    for char in text:
        if char == ':' and not show_colon:
            x += 24
            continue
        data = FONT_TIME24.get(ord(char))
        if data:
            fb = framebuf.FrameBuffer(bytearray(data), 24, 32, framebuf.MONO_VLSB)
            oled.blit(fb, x, y)
        x += 24


def wifi_level():
    """按 RSSI 返回信号格数 0~4（0 表示未连接）"""
    if not wlan.isconnected():
        return 0
    try:
        rssi = wlan.status('rssi')
    except Exception:
        return 3
    if rssi >= -55:
        return 4
    if rssi >= -67:
        return 3
    if rssi >= -78:
        return 2
    return 1


def draw_wifi(level):
    """右上角绘制 4 格 WiFi 信号条"""
    for i in range(level):
        h = (i + 1) * 2
        oled.fill_rect(111 + i * 4, 8 - h, 3, h, 1)


def render(now, show_colon):
    """绘制整屏：日期 / 信号 / 星期 / 时间"""
    oled.fill(0)

    date = "%04d-%02d-%02d" % (now[0], now[1], now[2])
    oled.text(date, (128 - len(date) * 8) // 2, 0)
    draw_wifi(wifi_level())

    week = WEEKDAYS[now[6]]
    show_chinese(week, (128 - len(week) * 16) // 2, 9)

    clock = "%02d:%02d" % (now[3], now[4])
    show_time(clock, (128 - len(clock) * 24) // 2, 30, show_colon)

    oled.show()


def sync_time():
    """连接 WiFi 并用 NTP 校时，成功返回 True"""
    if not wlan.isconnected():
        print("正在连接 WiFi:", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(40):                 # 最多等待 20 秒
            if wlan.isconnected():
                break
            time.sleep(0.5)

    if not wlan.isconnected():
        print("WiFi 连接失败")
        return False

    print("WiFi 已连接:", wlan.ifconfig()[0])
    for _ in range(3):
        try:
            ntptime.settime()
            print("NTP 校时成功")
            return True
        except Exception as e:
            print("NTP 校时失败:", e)
            time.sleep(1)
    return False


# ====== 初始化 OLED ======
i2c = SoftI2C(scl=Pin(6), sda=Pin(5), freq=400000)
oled = SSD1306_I2C(i2c)

# ====== 校时 ======
synced = sync_time()
if not synced:
    print("未校时，使用默认时间")
    RTC().datetime(FALLBACK_TIME)

# ====== 主循环：每秒刷新一次 ======
last_sec = None
while True:
    t = time.time()
    if synced:
        t += TZ_OFFSET                       # NTP 时间为 UTC，换算为北京时间
    now = time.localtime(t)

    if now[5] != last_sec:
        last_sec = now[5]
        render(now, show_colon=(now[5] % 2 == 0))

    time.sleep(0.1)

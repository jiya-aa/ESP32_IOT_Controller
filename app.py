"""
ESP32 AI Controller — Streamlit Dashboard

Run with:  streamlit run app.py
"""

import time
from datetime import datetime

import requests
import streamlit as st

import config
from configuration_page import render_configuration
from controller import Controller
from esp32_client import ESP32Client

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ESP32 AI Controller",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.glass-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
}
.badge-online  { background:#22c55e22; color:#22c55e; border:1px solid #22c55e55;
                 border-radius:999px; padding:2px 14px; font-size:.78rem; font-weight:600; }
.badge-offline { background:#ef444422; color:#ef4444; border:1px solid #ef444455;
                 border-radius:999px; padding:2px 14px; font-size:.78rem; font-weight:600; }

/* Sensor cards */
.sensor-card {
    background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15));
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    text-align: center;
    margin-bottom: 1rem;
}
.sensor-value {
    font-size: 2.4rem;
    font-weight: 700;
    line-height: 1.1;
    margin: .3rem 0;
}
.sensor-label {
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #94a3b8;
}
.sensor-sub {
    font-size: .82rem;
    color: #64748b;
    margin-top: .2rem;
}

/* LED buttons */
.bubble-user {
    background: linear-gradient(135deg,#6366f1,#8b5cf6);
    color:#fff; border-radius:18px 18px 4px 18px;
    padding:.6rem 1rem; margin:.3rem 0; display:inline-block;
    max-width:80%; float:right; clear:both;
}
.bubble-ai {
    background: rgba(255,255,255,0.08);
    color:#e2e8f0; border-radius:18px 18px 18px 4px;
    padding:.6rem 1rem; margin:.3rem 0; display:inline-block;
    max-width:80%; float:left; clear:both;
}
.bubble-wrap { overflow:hidden; margin:.2rem 0; }

.section-title {
    font-size:.75rem; font-weight:600; letter-spacing:.1em;
    text-transform:uppercase; color:#94a3b8; margin-bottom:.6rem;
}

.oled-preview {
    background:#000; color:#22c55e;
    font-family:'Courier New',monospace; font-size:.85rem;
    border-radius:8px; padding:.8rem 1rem;
    min-height:3.5rem; border:1px solid #22c55e44;
    word-break:break-all;
}

/* Temp colour coding */
.temp-cool   { color: #38bdf8; }
.temp-normal { color: #a3e635; }
.temp-warm   { color: #fb923c; }
.temp-hot    { color: #f87171; }

/* Configuration tutorial */
.guide-hero {
    padding: 1.5rem 1.6rem; margin-bottom: 1.2rem; border-radius: 20px;
    background: linear-gradient(135deg, rgba(37,99,235,.24), rgba(124,58,237,.18));
    border: 1px solid rgba(129,140,248,.32);
}
.guide-hero h1 { margin:.25rem 0 .35rem; font-size:2rem; }
.guide-hero p { margin:0; color:#cbd5e1; }
.guide-kicker { color:#a5b4fc; font-size:.72rem; font-weight:700; letter-spacing:.12em; }
.tutorial-step {
    display:flex; gap:1rem; align-items:flex-start; padding:1rem 1.1rem; margin:.65rem 0;
    background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.09); border-radius:14px;
}
.step-number {
    flex:0 0 32px; height:32px; display:grid; place-items:center; border-radius:50%;
    background:#4f46e5; color:white; font-weight:700;
}
.tutorial-step span:last-child { color:#cbd5e1; font-size:.9rem; }
.diagram-shell {
    overflow-x:auto; padding:.5rem; margin:.5rem 0 1.5rem; border-radius:18px;
    background:#0b1120; border:1px solid rgba(129,140,248,.25);
}
.wiring-diagram { width:100%; min-width:780px; height:auto; display:block; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "history":      [],
        "led_state":    None,
        "relay_state":  None,
        "pump_state":   None,
        "oled_text":    "",
        "esp32_online": None,
        "controller":   None,
        "recording":    False,
        "sensor":       None,
        "last_poll":    0,
        "page":          "dashboard",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_controller() -> Controller:
    if st.session_state.controller is None:
        st.session_state.controller = Controller()
    return st.session_state.controller


def get_esp32() -> ESP32Client:
    return get_controller().esp32


def poll_sensor(force: bool = False):
    """Fetch /status from ESP32 at most once every 10 s."""
    now = time.time()
    if not force and now - st.session_state.last_poll < 10:
        return
    data = get_esp32().get_status()
    st.session_state.sensor = data
    st.session_state.last_poll = now
    if data is not None:
        st.session_state.esp32_online = True
        # Sync device states from the ESP32's own pin readings
        st.session_state.led_state   = data.get("led")   == "on"
        st.session_state.relay_state = data.get("relay") == "on"
        st.session_state.pump_state  = data.get("pump")  == "on"


def add_history(role: str, text: str):
    st.session_state.history.append({"role": role, "text": text, "ts": time.time()})


def run_command(text: str):
    if not text.strip():
        return
    add_history("user", text)
    result = get_controller().handle_text(text)
    reply = result.get("reply", "")
    if reply:
        add_history("ai", reply)
    for action in result.get("actions", []):
        if action["mode"] == "LED_ON"    and action["ok"]: st.session_state.led_state   = True
        if action["mode"] == "LED_OFF"   and action["ok"]: st.session_state.led_state   = False
        if action["mode"] == "RELAY_ON"  and action["ok"]: st.session_state.relay_state = True
        if action["mode"] == "RELAY_OFF" and action["ok"]: st.session_state.relay_state = False
        if action["mode"] == "PUMP_ON"   and action["ok"]: st.session_state.pump_state  = True
        if action["mode"] == "PUMP_OFF"  and action["ok"]: st.session_state.pump_state  = False
        if action["mode"] in ("DISPLAY", "CHAT") and action.get("text"):
            st.session_state.oled_text = action["text"][:80]


def temp_color_class(c: float) -> str:
    if c < 20: return "temp-cool"
    if c < 28: return "temp-normal"
    if c < 34: return "temp-warm"
    return "temp-hot"


# Poll sensor on every page load
poll_sensor()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.session_state.page == "dashboard":
        if st.button("🛠️ Configuration", use_container_width=True, type="primary"):
            st.session_state.page = "configuration"
            st.rerun()
    else:
        if st.button("← Back to Dashboard", use_container_width=True, type="primary"):
            st.session_state.page = "dashboard"
            st.rerun()
        st.caption("Hardware & software setup guide")
        st.markdown("---")

    st.markdown("## ⚙️ Settings")
    st.markdown("---")
    st.markdown('<p class="section-title">ESP32 Connection</p>', unsafe_allow_html=True)
    esp32_ip = st.text_input("ESP32 IP", value=config.ESP32_IP)
    if st.button("🔌 Check Connection", use_container_width=True):
        config.ESP32_URL = f"http://{esp32_ip}"
        with st.spinner("Pinging..."):
            poll_sensor(force=True)
        st.session_state.esp32_online = st.session_state.sensor is not None

    if st.session_state.esp32_online is True:
        st.markdown('<span class="badge-online">● Online</span>', unsafe_allow_html=True)
    elif st.session_state.esp32_online is False:
        st.markdown('<span class="badge-offline">● Offline</span>', unsafe_allow_html=True)
    else:
        st.caption("Status unknown — click Check Connection")

    st.markdown("---")
    st.markdown('<p class="section-title">Audio Device</p>', unsafe_allow_html=True)
    audio_device = st.selectbox("Input / Output", ["pc", "esp32"],
        index=0 if config.AUDIO_DEVICE == "pc" else 1)
    config.AUDIO_DEVICE = audio_device

    st.markdown("---")
    st.markdown('<p class="section-title">Auto-Refresh</p>', unsafe_allow_html=True)
    auto_refresh = st.toggle("Refresh sensor every 10 s", value=True)

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.history = []
        st.rerun()


if st.session_state.page == "configuration":
    render_configuration()
    st.stop()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.2rem">
  <span style="font-size:2.2rem">🤖</span>
  <div>
    <h1 style="margin:0;font-size:1.6rem;font-weight:700">ESP32 AI Controller</h1>
    <p style="margin:0;color:#94a3b8;font-size:.88rem">Voice &amp; text smart home control</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Row 1: Sensor cards + devices + OLED ─────────────────────────────────────
col_time, col_temp, col_led, col_relay, col_pump = st.columns([1, 1, 1, 1, 1])

sensor = st.session_state.sensor

# ── Time card ─────────────────────────────────────────────────────────────────
with col_time:
    esp_time = sensor.get("time", "--:--") if sensor else datetime.now().strftime("%H:%M")
    esp_date = sensor.get("date", "")       if sensor else datetime.now().strftime("%d %b %Y")
    st.markdown(
        f'<div class="sensor-card">'
        f'<div class="sensor-label">🕐 ESP32 Time</div>'
        f'<div class="sensor-value">{esp_time}</div>'
        f'<div class="sensor-sub">{esp_date}</div>'
        f'{"" if sensor else "<div style=\"font-size:.7rem;color:#ef4444;margin-top:.3rem\">PC clock</div>"}'
        f'</div>',
        unsafe_allow_html=True
    )

# ── Temperature card ──────────────────────────────────────────────────────────
with col_temp:
    if sensor:
        tc   = sensor.get("temp_c", 0.0)
        tf   = sensor.get("temp_f", 0.0)
        cls  = temp_color_class(tc)
        t_display = f'<span class="{cls}">{tc:.1f}°C</span>'
        t_sub     = f"{tf:.1f}°F"
        t_note    = ""
    else:
        t_display = '<span style="color:#64748b">--°C</span>'
        t_sub     = "No data"
        t_note    = '<div style="font-size:.7rem;color:#ef4444;margin-top:.3rem">ESP32 offline</div>'
    st.markdown(
        f'<div class="sensor-card">'
        f'<div class="sensor-label">🌡️ Temperature</div>'
        f'<div class="sensor-value">{t_display}</div>'
        f'<div class="sensor-sub">{t_sub}</div>{t_note}'
        f'</div>',
        unsafe_allow_html=True
    )
    if st.button("🔄", key="btn_refresh", use_container_width=True, help="Refresh sensor"):
        poll_sensor(force=True); st.rerun()

# ── Device card helper ────────────────────────────────────────────────────────
def device_card(col, label: str, icon_on: str, icon_off: str,
                state, cmd_on: str, cmd_off: str, btn_key: str):
    with col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f'<p class="section-title">{label}</p>', unsafe_allow_html=True)
        icon  = icon_on  if state else icon_off
        lbl   = "ON"     if state else "OFF"
        st.markdown(
            f"<div style='text-align:center;font-size:2.2rem;margin:.3rem 0'>{icon}</div>"
            f"<div style='text-align:center;color:#94a3b8;font-size:.78rem;margin-bottom:.5rem'>{lbl}</div>",
            unsafe_allow_html=True
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("ON",  use_container_width=True, key=f"{btn_key}_on"):
                run_command(cmd_on);  st.rerun()
        with c2:
            if st.button("OFF", use_container_width=True, key=f"{btn_key}_off"):
                run_command(cmd_off); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

device_card(col_led,   "💡 LED",   "💡", "🔦",
            st.session_state.led_state,
            "turn on led",   "turn off led",   "led")
device_card(col_relay, "⚡ Relay", "🔴", "⚫",
            st.session_state.relay_state,
            "turn on relay", "turn off relay", "relay")
device_card(col_pump,  "💧 Pump",  "🟦", "⬜",
            st.session_state.pump_state,
            "start pump",    "stop pump",      "pump")

# ── OLED + Status row ────────────────────────────────────────────────────────
col_oled, col_status = st.columns([3, 1])

with col_oled:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">🖥️ OLED Display</p>', unsafe_allow_html=True)

    if st.session_state.oled_text:
        preview = st.session_state.oled_text
    elif sensor:
        preview = f"🕐 {sensor.get('time','--:--')}   🌡 {sensor.get('temp_c',0):.1f}°C   ⚡ Relay {sensor.get('relay','?')}   💧 Pump {sensor.get('pump','?')}"
    else:
        preview = "— idle (clock + temp) —"

    st.markdown(f'<div class="oled-preview">{preview}</div>', unsafe_allow_html=True)

    oled_input = st.text_input("Send to OLED", placeholder="Type text to scroll on the display…",
                                label_visibility="collapsed", key="oled_in")
    c1, c2 = st.columns([3, 1])
    with c1:
        if st.button("📺 Send", use_container_width=True, key="btn_oled"):
            if oled_input:
                run_command(f"display {oled_input}"); st.rerun()
    with c2:
        if st.button("✖ Clear", use_container_width=True, key="btn_oled_clear"):
            st.session_state.oled_text = ""
    st.markdown('</div>', unsafe_allow_html=True)

with col_status:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">📡 System Status</p>', unsafe_allow_html=True)
    rows = [
        ("ESP32",  "🟢 Online"  if st.session_state.esp32_online else ("🔴 Offline" if st.session_state.esp32_online is False else "⚪ Unknown")),
        ("LED",    f"{'💡 ON' if st.session_state.led_state else '🔦 OFF'}"),
        ("Relay",  f"{'🔴 ON' if st.session_state.relay_state else '⚫ OFF'}"),
        ("Pump",   f"{'🟦 ON' if st.session_state.pump_state  else '⬜ OFF'}"),
        ("Audio",  f"🎤 {config.AUDIO_DEVICE.upper()}"),
        ("Whisper",f"📝 {config.WHISPER_MODEL}"),
    ]
    for label, val in rows:
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;margin:.35rem 0;"
            f"font-size:.82rem'><span style='color:#94a3b8'>{label}</span>"
            f"<span>{val}</span></div>",
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Row 2: Chat + Voice + Quick actions ───────────────────────────────────────
col_chat, col_voice = st.columns([3, 1])

with col_chat:
    st.markdown('<p class="section-title">💬 Command Chat</p>', unsafe_allow_html=True)

    chat_html = ""
    for msg in st.session_state.history[-30:]:
        ts = time.strftime("%H:%M", time.localtime(msg["ts"]))
        if msg["role"] == "user":
            chat_html += (
                f'<div class="bubble-wrap"><div class="bubble-user">{msg["text"]}'
                f'<div style="font-size:.65rem;opacity:.6;margin-top:.2rem;text-align:right">{ts}</div>'
                f'</div></div>'
            )
        else:
            chat_html += (
                f'<div class="bubble-wrap"><div class="bubble-ai">🤖 {msg["text"]}'
                f'<div style="font-size:.65rem;opacity:.6;margin-top:.2rem">{ts}</div>'
                f'</div></div>'
            )

    if chat_html:
        st.markdown(f'<div style="height:300px;overflow-y:auto;padding:.4rem .2rem">{chat_html}</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="height:300px;display:flex;align-items:center;justify-content:center;'
            'color:#475569;font-size:.9rem">No commands yet — type below or use the voice button.</div>',
            unsafe_allow_html=True
        )

    with st.form("chat_form", clear_on_submit=True):
        text_cmd  = st.text_input("Command", placeholder="Ask anything or say 'turn on LED'…",
                                   label_visibility="collapsed")
        submitted = st.form_submit_button("Send ➤", use_container_width=True)
        if submitted and text_cmd:
            run_command(text_cmd); st.rerun()

with col_voice:
    st.markdown('<p class="section-title">🎙️ Voice Command</p>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card" style="text-align:center">', unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:3rem;margin:.4rem 0'>🎙️</div>"
        "<p style='color:#94a3b8;font-size:.82rem;margin-bottom:.8rem'>"
        "Click and speak for 5 s.</p>",
        unsafe_allow_html=True
    )
    if st.button("🔴 Record 5s", use_container_width=True, key="btn_record",
                 disabled=st.session_state.recording):
        st.session_state.recording = True; st.rerun()

    if st.session_state.recording:
        with st.spinner("Recording… 🎤"):
            import speech as _speech
            _speech.record("command.wav", esp32=get_esp32())
        with st.spinner("Transcribing…"):
            transcript = _speech.transcribe("command.wav")
        st.session_state.recording = False
        if transcript:
            st.success(f"Heard: *{transcript}*")
            run_command(transcript); st.rerun()
        else:
            st.warning("Nothing detected."); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<br><p class="section-title">⚡ Quick Actions</p>', unsafe_allow_html=True)
    quick = [
        ("💡 LED On",        "turn on led"),
        ("🌑 LED Off",       "turn off led"),
        ("🕐 What time?",    "what time is it"),
        ("🌡️ Temperature?", "what is the temperature"),
        ("😄 Tell a joke",   "tell me a joke"),
        ("☀️ Weather tip",   "give me a weather tip based on 28 degrees"),
    ]
    for label, cmd in quick:
        if st.button(label, use_container_width=True, key=f"q_{cmd[:8]}"):
            run_command(cmd); st.rerun()

# ── Full log ──────────────────────────────────────────────────────────────────
if st.session_state.history:
    with st.expander("📋 Full Command Log"):
        rows = [{"Time": time.strftime("%H:%M:%S", time.localtime(m["ts"])),
                 "Role": "🧑 You" if m["role"] == "user" else "🤖 AI",
                 "Message": m["text"]}
                for m in reversed(st.session_state.history)]
        st.dataframe(rows, use_container_width=True, hide_index=True)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(10)
    st.rerun()

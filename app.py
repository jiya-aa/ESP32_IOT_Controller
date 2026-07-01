"""
ESP32 AI Controller — Streamlit Dashboard

Run with:  streamlit run app.py
"""

import threading
import time
from pathlib import Path

import requests
import streamlit as st

import config
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

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark glassmorphism card */
.glass-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
}

/* Status badge */
.badge-online  { background:#22c55e22; color:#22c55e; border:1px solid #22c55e55;
                 border-radius:999px; padding:2px 14px; font-size:.78rem; font-weight:600; }
.badge-offline { background:#ef444422; color:#ef4444; border:1px solid #ef444455;
                 border-radius:999px; padding:2px 14px; font-size:.78rem; font-weight:600; }

/* LED buttons */
.led-on  { background: linear-gradient(135deg,#facc15,#f59e0b) !important;
           color:#000 !important; font-weight:700 !important; border:none !important; }
.led-off { background: linear-gradient(135deg,#6b7280,#4b5563) !important;
           color:#fff !important; font-weight:700 !important; border:none !important; }

/* Chat bubbles */
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

/* Section headers */
.section-title {
    font-size:.75rem; font-weight:600; letter-spacing:.1em;
    text-transform:uppercase; color:#94a3b8; margin-bottom:.6rem;
}

/* OLED preview */
.oled-preview {
    background:#000; color:#22c55e;
    font-family:'Courier New',monospace; font-size:.85rem;
    border-radius:8px; padding:.8rem 1rem;
    min-height:3.5rem; border:1px solid #22c55e44;
    word-break:break-all;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "history": [],        # list of {"role": "user"|"ai", "text": str, "ts": float}
        "led_state": None,    # True=ON, False=OFF, None=unknown
        "oled_text": "",
        "esp32_online": None,
        "controller": None,
        "recording": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_controller() -> Controller:
    if st.session_state.controller is None:
        st.session_state.controller = Controller()
    return st.session_state.controller


def check_esp32() -> bool:
    """Ping the ESP32 — returns True if reachable."""
    try:
        requests.get(f"{config.ESP32_URL}/led/on", timeout=2)
        # immediately restore LED to whatever state it was
        requests.get(
            f"{config.ESP32_URL}/led/{'on' if st.session_state.led_state else 'off'}",
            timeout=2
        )
        return True
    except Exception:
        return False


def add_history(role: str, text: str):
    st.session_state.history.append({"role": role, "text": text, "ts": time.time()})


def run_command(text: str):
    """Send a text command through the controller and update state."""
    if not text.strip():
        return
    add_history("user", text)
    ctrl = get_controller()
    result = ctrl.handle_text(text)
    reply = result.get("reply", "")
    if reply:
        add_history("ai", reply)
    # Sync LED state from actions
    for action in result.get("actions", []):
        if action["mode"] == "LED_ON" and action["ok"]:
            st.session_state.led_state = True
        elif action["mode"] == "LED_OFF" and action["ok"]:
            st.session_state.led_state = False
        elif action["mode"] in ("DISPLAY", "CHAT") and action.get("text"):
            st.session_state.oled_text = action["text"][:80]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")

    st.markdown("---")
    st.markdown('<p class="section-title">ESP32 Connection</p>', unsafe_allow_html=True)

    esp32_ip = st.text_input("ESP32 IP", value=config.ESP32_IP, key="esp32_ip_input")
    if st.button("🔌 Check Connection", use_container_width=True):
        with st.spinner("Pinging ESP32..."):
            # Override URL temporarily for the check
            config.ESP32_URL = f"http://{esp32_ip}"
            st.session_state.esp32_online = check_esp32()

    if st.session_state.esp32_online is True:
        st.markdown('<span class="badge-online">● Online</span>', unsafe_allow_html=True)
    elif st.session_state.esp32_online is False:
        st.markdown('<span class="badge-offline">● Offline</span>', unsafe_allow_html=True)
    else:
        st.caption("Status unknown — click Check Connection")

    st.markdown("---")
    st.markdown('<p class="section-title">Audio Device</p>', unsafe_allow_html=True)
    audio_device = st.selectbox(
        "Input / Output",
        ["pc", "esp32"],
        index=0 if config.AUDIO_DEVICE == "pc" else 1,
        help="'pc' = your laptop mic/speaker. 'esp32' = INMP441 mic + MAX98357A amp."
    )
    config.AUDIO_DEVICE = audio_device

    st.markdown("---")
    st.markdown('<p class="section-title">Whisper Model</p>', unsafe_allow_html=True)
    st.selectbox("Model size", ["tiny", "base", "small", "medium"],
                 index=["tiny","base","small","medium"].index(config.WHISPER_MODEL),
                 key="whisper_model", help="Larger = more accurate but slower.")

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.history = []
        st.rerun()


# ── Main layout ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;">
  <span style="font-size:2.2rem;">🤖</span>
  <div>
    <h1 style="margin:0;font-size:1.6rem;font-weight:700;">ESP32 AI Controller</h1>
    <p style="margin:0;color:#94a3b8;font-size:.88rem;">
        Voice &amp; text control for your smart home
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Top row: LED + OLED + Status ──────────────────────────────────────────────
col_led, col_oled, col_status = st.columns([1, 2, 1])

with col_led:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">💡 LED Control</p>', unsafe_allow_html=True)

    led_icon = "💡" if st.session_state.led_state else "🔦"
    led_label = "ON" if st.session_state.led_state else "OFF"
    st.markdown(
        f"<div style='text-align:center;font-size:2.5rem;margin:.4rem 0'>{led_icon}</div>"
        f"<div style='text-align:center;color:#94a3b8;font-size:.85rem;margin-bottom:.8rem'>GPIO 2 — {led_label}</div>",
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("ON ☀️", use_container_width=True, key="btn_led_on"):
            run_command("turn on led")
            st.rerun()
    with c2:
        if st.button("OFF 🌑", use_container_width=True, key="btn_led_off"):
            run_command("turn off led")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


with col_oled:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">🖥️ OLED Display</p>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="oled-preview">{st.session_state.oled_text or "— no text —"}</div>',
        unsafe_allow_html=True
    )
    oled_input = st.text_input(
        "Send to OLED", placeholder="Type something to show on the display…",
        label_visibility="collapsed", key="oled_input"
    )
    if st.button("📺 Send to Display", use_container_width=True, key="btn_oled"):
        if oled_input:
            run_command(f"display {oled_input}")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


with col_status:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">📡 System Status</p>', unsafe_allow_html=True)

    status_rows = [
        ("ESP32", "🟢 Online" if st.session_state.esp32_online else ("🔴 Offline" if st.session_state.esp32_online is False else "⚪ Unknown")),
        ("Gemini", "🟢 Ready"),
        ("Audio", f"🎤 {config.AUDIO_DEVICE.upper()}"),
        ("Whisper", f"📝 {config.WHISPER_MODEL}"),
        ("OLED max", f"📏 {config.OLED_MAX_CHARS} chars"),
    ]
    for label, val in status_rows:
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;margin:.3rem 0;"
            f"font-size:.82rem'><span style='color:#94a3b8'>{label}</span>"
            f"<span>{val}</span></div>",
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ── Chat Section ──────────────────────────────────────────────────────────────
st.markdown("---")
col_chat, col_voice = st.columns([3, 1])

with col_chat:
    st.markdown('<p class="section-title">💬 Command Chat</p>', unsafe_allow_html=True)

    # Chat history display
    chat_html = ""
    for msg in st.session_state.history[-30:]:   # show last 30
        ts = time.strftime("%H:%M", time.localtime(msg["ts"]))
        if msg["role"] == "user":
            chat_html += (
                f'<div class="bubble-wrap">'
                f'<div class="bubble-user">{msg["text"]}'
                f'<div style="font-size:.65rem;opacity:.6;margin-top:.2rem;text-align:right">{ts}</div>'
                f'</div></div>'
            )
        else:
            chat_html += (
                f'<div class="bubble-wrap">'
                f'<div class="bubble-ai">🤖 {msg["text"]}'
                f'<div style="font-size:.65rem;opacity:.6;margin-top:.2rem">{ts}</div>'
                f'</div></div>'
            )

    if chat_html:
        st.markdown(
            f'<div style="height:320px;overflow-y:auto;padding:.4rem .2rem">{chat_html}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="height:320px;display:flex;align-items:center;justify-content:center;'
            'color:#475569;font-size:.9rem">No commands yet — type below or use the voice button.</div>',
            unsafe_allow_html=True
        )

    # Text command input
    with st.form("chat_form", clear_on_submit=True):
        text_cmd = st.text_input(
            "Command", placeholder="Ask anything: 'What's the capital of France?' or 'Turn on LED'",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("Send ➤", use_container_width=True)
        if submitted and text_cmd:
            run_command(text_cmd)
            st.rerun()


with col_voice:
    st.markdown('<p class="section-title">🎙️ Voice Command</p>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card" style="text-align:center">', unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:3rem;margin:.5rem 0'>🎙️</div>"
        "<p style='color:#94a3b8;font-size:.82rem;margin-bottom:1rem'>"
        "Click and speak for 5 seconds. The assistant will transcribe and respond.</p>",
        unsafe_allow_html=True
    )

    if st.button("🔴 Record 5s", use_container_width=True, key="btn_record",
                 disabled=st.session_state.recording):
        st.session_state.recording = True
        st.rerun()

    if st.session_state.recording:
        with st.spinner("Recording… speak now 🎤"):
            import speech as _speech
            _speech.record("command.wav", esp32=get_controller().esp32)

        with st.spinner("Transcribing…"):
            import speech as _speech
            transcript = _speech.transcribe("command.wav")

        st.session_state.recording = False

        if transcript:
            st.success(f"Heard: *{transcript}*")
            run_command(transcript)
            st.rerun()
        else:
            st.warning("Nothing detected — try again.")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Quick actions panel
    st.markdown('<br><p class="section-title">⚡ Quick Actions</p>', unsafe_allow_html=True)
    quick_cmds = [
        ("💡 LED On",    "turn on led"),
        ("🌑 LED Off",   "turn off led"),
        ("🌡️ Ask Temp",  "what is room temperature"),
        ("⏰ Ask Time",  "what time is it"),
        ("😄 Joke",      "tell me a joke"),
    ]
    for label, cmd in quick_cmds:
        if st.button(label, use_container_width=True, key=f"quick_{cmd[:10]}"):
            run_command(cmd)
            st.rerun()


# ── Command History Table ─────────────────────────────────────────────────────
if st.session_state.history:
    with st.expander("📋 Full Command Log", expanded=False):
        rows = []
        for m in reversed(st.session_state.history):
            rows.append({
                "Time":   time.strftime("%H:%M:%S", time.localtime(m["ts"])),
                "Role":   "🧑 You" if m["role"] == "user" else "🤖 AI",
                "Message": m["text"]
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

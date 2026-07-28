"""Tutorial-style hardware and software configuration page."""

import streamlit as st


PIN_ROWS = [
    ("On-board LED", "GPIO 2", "Built in", "LED demo"),
    ("Relay module", "GPIO 5", "IN / SIG", "External load"),
    ("Pump relay", "GPIO 18", "IN / SIG", "Pump control"),
    ("OLED", "GPIO 4 / 15", "SDA / SCL", "I²C display"),
    ("INMP441", "GPIO 26 / 25 / 32 / 17", "SCK / WS / SD / L/R", "I²S microphone"),
    ("MAX98357A", "GPIO 14 / 27 / 33", "BCLK / LRC / DIN", "I²S amplifier"),
]


def _diagram() -> str:
    return """
<div class="diagram-shell">
<svg class="wiring-diagram" viewBox="0 0 1120 650" role="img"
 aria-label="ESP32 wiring diagram with relay, OLED, microphone and amplifier">
<defs><filter id="s"><feDropShadow dx="0" dy="5" stdDeviation="6" flood-opacity=".3"/></filter>
<style>
.bx{fill:#172033;stroke:#52617b;stroke-width:2;rx:16;filter:url(#s)}
.bd{fill:#202c46;stroke:#818cf8;stroke-width:3;rx:22;filter:url(#s)}
.t{fill:#f8fafc;font:700 18px Inter,Arial}.p{fill:#dbeafe;font:600 13px Inter,Arial}
.n{fill:#94a3b8;font:13px Inter,Arial}.w{stroke:#60a5fa;stroke-width:3;fill:none}
.g{stroke:#94a3b8;stroke-width:3;fill:none}.l{fill:#bfdbfe;font:600 11px Inter,Arial}
</style></defs>
<rect class="bd" x="410" y="72" width="300" height="500"/>
<text class="t" x="560" y="110" text-anchor="middle">ESP32 DevKit</text>
<text class="n" x="560" y="134" text-anchor="middle">3.3 V logic • USB powered</text>

<rect class="bx" x="35" y="45" width="250" height="130"/>
<text class="t" x="55" y="78">SSD1306 OLED</text><text class="n" x="55" y="103">3V3 • GND</text>
<text class="p" x="55" y="133">SDA → GPIO 4</text><text class="p" x="55" y="157">SCL → GPIO 15</text>
<rect class="bx" x="35" y="210" width="250" height="170"/>
<text class="t" x="55" y="243">INMP441 mic</text><text class="n" x="55" y="268">3V3 • GND</text>
<text class="p" x="55" y="298">SCK → 26 • WS → 25</text><text class="p" x="55" y="326">SD → 32</text>
<text class="p" x="55" y="354">L/R → 17 (LOW)</text>
<rect class="bx" x="35" y="425" width="250" height="150"/>
<text class="t" x="55" y="458">MAX98357A</text><text class="n" x="55" y="483">5V/VIN • GND</text>
<text class="p" x="55" y="513">BCLK → 14</text><text class="p" x="55" y="539">LRC → 27 • DIN → 33</text>
<text class="n" x="55" y="562">Speaker → SPK+ / SPK− only</text>

<rect class="bx" x="835" y="80" width="250" height="145"/>
<text class="t" x="855" y="113">Relay module</text><text class="n" x="855" y="138">Rated supply • common GND</text>
<text class="p" x="855" y="170">IN → GPIO 5</text>
<rect class="bx" x="835" y="280" width="250" height="145"/>
<text class="t" x="855" y="313">Pump relay</text><text class="n" x="855" y="338">Separate pump supply</text>
<text class="p" x="855" y="370">IN → GPIO 18</text>
<rect class="bx" x="835" y="480" width="250" height="95"/>
<text class="t" x="855" y="515">On-board LED</text><text class="p" x="855" y="545">GPIO 2 • no wiring</text>

<path class="w" d="M285 133 H355 V180 H410"/><text class="l" x="315" y="126">GPIO 4</text>
<path class="w" d="M285 157 H340 V215 H410"/><text class="l" x="292" y="174">GPIO 15</text>
<path class="w" d="M285 298 H340 V265 H410"/><text class="l" x="346" y="259">26</text>
<path class="w" d="M285 310 H355 V300 H410"/><text class="l" x="361" y="294">25</text>
<path class="w" d="M285 326 H370 V335 H410"/><text class="l" x="376" y="329">32</text>
<path class="w" d="M285 354 H350 V370 H410"/><text class="l" x="356" y="364">17</text>
<path class="w" d="M285 513 H335 V420 H410"/><text class="l" x="341" y="414">14</text>
<path class="w" d="M285 532 H350 V455 H410"/><text class="l" x="356" y="449">27</text>
<path class="w" d="M285 546 H370 V490 H410"/><text class="l" x="376" y="484">33</text>
<path class="w" d="M710 180 H780 V170 H835"/><text class="l" x="748" y="163">GPIO 5</text>
<path class="w" d="M710 350 H780 V370 H835"/><text class="l" x="740" y="344">GPIO 18</text>
<path class="w" d="M710 520 H835"/><text class="l" x="755" y="513">GPIO 2</text>
<path class="g" d="M710 550 H790 V610 H300"/><text class="l" x="455" y="632" style="fill:#cbd5e1">COMMON GROUND: ESP32 + every low-voltage module</text>
</svg></div>"""


def render_configuration() -> None:
    st.markdown("""
<div class="guide-hero"><div class="guide-kicker">START HERE · 20–30 MINUTES</div>
<h1>Build your ESP32 AI Controller</h1>
<p>Wire the core controller first, verify it, then add audio and the OLED one module at a time.</p></div>
""", unsafe_allow_html=True)
    st.warning("Disconnect all power before changing wiring. ESP32 GPIO is 3.3 V only—never feed 5 V into a GPIO. All low-voltage modules must share a common ground.")

    st.markdown("## 1. Gather the hardware")
    a, b = st.columns(2)
    with a:
        st.markdown("""**Required**

- ESP32 DevKit and data-capable USB cable
- Breadboard and jumper wires
- 3.3 V-compatible relay module
- Second relay and correctly rated pump supply
- Computer with Arduino IDE and Python 3.10+
""")
    with b:
        st.markdown("""**Optional upgrades**

- SSD1306 128×64 I²C OLED
- INMP441 I²S microphone
- MAX98357A amplifier and 4–8 Ω speaker
- Real temperature sensor (firmware currently simulates it)
""")

    st.markdown("## 2. Pin-connection table")
    st.table({"Device": [r[0] for r in PIN_ROWS], "ESP32 pin": [r[1] for r in PIN_ROWS],
              "Module pin": [r[2] for r in PIN_ROWS], "Purpose": [r[3] for r in PIN_ROWS]})
    st.caption("OLED and INMP441 use 3.3 V. MAX98357A commonly uses 5 V/VIN. Verify the labels and datasheet for your exact modules.")

    st.markdown("## 3. Follow the wiring diagram")
    st.markdown(_diagram(), unsafe_allow_html=True)

    st.markdown("## 4. Wire it step by step")
    steps = [
        ("Start powered off", "Unplug USB and external supplies. Place the ESP32 across the breadboard center gap."),
        ("Make a common ground", "Connect ESP32 GND and every low-voltage module GND to the same ground rail."),
        ("Connect relay controls", "Wire relay IN to GPIO 5 and pump-relay IN to GPIO 18. Power relays at their rated voltage."),
        ("Connect loads safely", "Use relay COM and NO contacts and a separate load supply. Never power a motor or pump from the ESP32."),
        ("Add optional modules", "Follow the table and add only one module at a time, testing after each addition."),
        ("Inspect, then power", "Check for reversed VCC/GND, shorts, loose strands, 5 V-to-GPIO connections, and missing ground."),
    ]
    for i, (title, body) in enumerate(steps, 1):
        st.markdown(f'<div class="tutorial-step"><span class="step-number">{i}</span><div><b>{title}</b><br><span>{body}</span></div></div>', unsafe_allow_html=True)

    st.markdown("## 5. Configure Wi-Fi and the API")
    a, b = st.columns(2)
    with a:
        st.markdown("**ESP32 Wi-Fi**")
        st.code('Copy esp32_sketch/secrets.h.example to secrets.h\n\n#define WIFI_SSID "your_wifi_name"\n#define WIFI_PASSWORD "your_wifi_password"', language="cpp")
        st.caption("Upload the sketch, open Serial Monitor at 115200 baud, and note the printed IP.")
    with b:
        st.markdown("**Dashboard and Gemini**")
        st.code("Copy .env.example to .env\n\nGEMINI_API_KEY=your_key_here\nESP32_IP=192.168.x.x\nAUDIO_DEVICE=pc", language="text")
        st.caption("Keep both secret files private. The computer and ESP32 must use the same Wi-Fi.")

    st.markdown("## 6. Optional modules")
    with st.expander("🎤 INMP441 microphone"):
        st.write("Use 3.3 V. Wire SCK→26, WS→25, SD→32, L/R→17. Firmware drives L/R LOW and records the left I²S channel at 16 kHz.")
    with st.expander("🔊 MAX98357A amplifier"):
        st.write("Wire BCLK→14, LRC→27, DIN→33, VIN→5 V, GND→common GND. Connect the speaker across SPK+ and SPK− only; neither speaker terminal goes to ground.")
    with st.expander("🖥️ SSD1306 OLED"):
        st.write("Wire SDA→4 and SCL→15, use 3.3 V, and address 0x3C. If it fails, scan the I²C bus; use 0x3D only if your module reports it.")

    st.markdown("## 7. Test in this order")
    st.markdown("""1. Power by USB and confirm Serial Monitor prints a Wi-Fi IP and `Server started.`
2. Open `http://<ESP32_IP>/status`; it should return JSON.
3. Return to the dashboard, enter that IP, and click **Check Connection**.
4. Test the on-board LED, then each relay with no load attached.
5. Send test text to the OLED.
6. Open `http://<ESP32_IP>/tone` for the speaker beep, then run `python esp32_audio_test.py record 3` for the microphone.
7. Connect the external low-voltage load only after every no-load test passes.
""")
    st.success("Ready when `/status` responds, dashboard controls work, and each module passes independently.")
    st.markdown("""### Final safety checklist

- [ ] GPIO pins receive no more than 3.3 V
- [ ] ESP32 and modules share common GND
- [ ] Pump/motor has a separate, correctly rated supply
- [ ] Relay contact rating exceeds the load voltage and current
- [ ] Power is off before wiring changes
- [ ] API keys and Wi-Fi passwords are not committed to Git
""")

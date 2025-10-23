# app.py
import re
import socket
from contextlib import contextmanager

import streamlit as st
from mcstatus import JavaServer, BedrockServer
from streamlit_autorefresh import st_autorefresh

# -------------------- Defaults --------------------
DEFAULT_HOST = "xaprosmp.xyz"
DEFAULT_EDITION = "Java"            # or "Bedrock" if your server is Bedrock
DEFAULT_JAVA_PORT = 25565
DEFAULT_BEDROCK_PORT = 19132
TIMEOUT_MS = 2500                   # fixed timeout (no UI slider)

st.set_page_config(page_title="Minecraft Server Status", page_icon="⛏️", layout="centered")
st.title("Minecraft Server Status")

# -------------------- Session defaults --------------------
if "host" not in st.session_state:
    st.session_state.host = DEFAULT_HOST
if "edition" not in st.session_state:
    st.session_state.edition = DEFAULT_EDITION
if "port" not in st.session_state:
    st.session_state.port = DEFAULT_JAVA_PORT if DEFAULT_EDITION == "Java" else DEFAULT_BEDROCK_PORT

# -------------------- Controls --------------------
with st.container():
    colA, colB, colC = st.columns([1, 1.4, 0.9])
    with colA:
        edition = st.radio(
            "Edition", ["Java", "Bedrock"], horizontal=True,
            index=0 if st.session_state.edition == "Java" else 1
        )
    with colB:
        host = st.text_input("Host / IP", value=st.session_state.host, placeholder="e.g., play.example.org")
    with colC:
        default_port = DEFAULT_JAVA_PORT if edition == "Java" else DEFAULT_BEDROCK_PORT
        port = st.number_input("Port", value=int(st.session_state.port or default_port),
                               min_value=1, max_value=65535, step=1)

    # One-click reset to your server
    if st.button(f"Use {DEFAULT_HOST}", key="use_default"):
        st.session_state.host = DEFAULT_HOST
        st.session_state.edition = DEFAULT_EDITION
        st.session_state.port = DEFAULT_JAVA_PORT if DEFAULT_EDITION == "Java" else DEFAULT_BEDROCK_PORT
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()

    auto = st.checkbox("Auto-refresh every 30 s", value=True)
    if auto:
        st_autorefresh(interval=30_000, key="mc_auto")

    # Manual check; pressing the button triggers a rerun
    st.button("Check now", type="primary")

# Persist any edits
st.session_state.host = host.strip() or DEFAULT_HOST
st.session_state.edition = edition
st.session_state.port = int(port) if port else (DEFAULT_JAVA_PORT if edition == "Java" else DEFAULT_BEDROCK_PORT)

# -------------------- Helpers --------------------
@contextmanager
def _temp_socket_timeout(seconds: float):
    prev = socket.getdefaulttimeout()
    socket.setdefaulttimeout(seconds)
    try:
        yield
    finally:
        socket.setdefaulttimeout(prev)

def _status_with_timeout(server, secs: float):
    """Call server.status() compatibly across mcstatus versions."""
    try:
        return server.status(timeout=secs)  # newer mcstatus
    except TypeError:
        with _temp_socket_timeout(secs):    # older mcstatus
            return server.status()

def _ping_with_timeout(server, secs: float):
    try:
        return server.ping(timeout=secs)
    except TypeError:
        with _temp_socket_timeout(secs):
            return server.ping()
    except Exception:
        return None

# Strip Minecraft formatting codes, including hex §x sequences
_MC_HEX_SEQ = re.compile(r"§x(§[0-9a-fA-F]){6}")
_MC_CODE_SEQ = re.compile(r"[§&][0-9a-fk-orA-FK-OR]")

def _strip_mc_codes(s: str) -> str:
    s = _MC_HEX_SEQ.sub("", s)
    s = _MC_CODE_SEQ.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _clean_motd(desc) -> str | None:
    if desc is None:
        return None
    try:
        text = str(desc)
    except Exception:
        return None
    return _strip_mc_codes(text)

def check_status(host: str, port: int, edition: str, timeout_ms: int):
    secs = max(0.1, timeout_ms / 1000.0)
    try:
        if edition == "Bedrock":
            server = BedrockServer.lookup(f"{host}:{port}")
            stat = _status_with_timeout(server, secs)

            # Normalize fields across mcstatus versions
            players_online = getattr(stat, "players_online", None)
            players_max    = getattr(stat, "players_max", None)
            latency        = getattr(stat, "latency", None) or _ping_with_timeout(server, secs)
            ver_obj        = getattr(stat, "version", None)  # BedrockStatusVersion
            version_name   = (getattr(ver_obj, "name", None) if ver_obj is not None else None) or (str(ver_obj) if ver_obj is not None else None)
            motd_clean     = _clean_motd(getattr(stat, "motd", None))

            return {
                "up": True, "edition": "bedrock",
                "latency_ms": latency,
                "players": {"online": players_online, "max": players_max},
                "version": {"name": version_name},
                "motd": motd_clean,
            }

        else:  # Java
            server = JavaServer.lookup(f"{host}:{port}")  # SRV-aware
            stat = _status_with_timeout(server, secs)

            players     = getattr(stat, "players", None)
            online      = getattr(players, "online", None) if players else None
            maxp        = getattr(players, "max", None) if players else None
            ver_obj     = getattr(stat, "version", None)
            version_name= (getattr(ver_obj, "name", None) if ver_obj is not None else None) or (str(ver_obj) if ver_obj is not None else None)
            latency     = getattr(stat, "latency", None) or _ping_with_timeout(server, secs)
            motd_clean  = _clean_motd(getattr(stat, "description", None))

            return {
                "up": True, "edition": "java",
                "latency_ms": latency,
                "players": {"online": online, "max": maxp},
                "version": {"name": version_name},
                "motd": motd_clean,
            }

    except Exception as e:
        return {"up": False, "error": str(e)}

# -------------------- Check & Render --------------------
with st.spinner("Pinging..."):
    result = check_status(st.session_state.host, st.session_state.port, st.session_state.edition, TIMEOUT_MS)

target = f"{st.session_state.edition.lower()}://{st.session_state.host}:{st.session_state.port}"
st.caption(f"Target: `{target}`")

if result.get("up"):
    st.success("UP")
    c1, c2, c3 = st.columns(3)
    c1.metric("Latency", f"{int(result.get('latency_ms') or 0)} ms")
    p = result.get("players") or {}
    c2.metric("Players", f"{p.get('online') or 0} / {p.get('max') or '?'}")
    v = (result.get("version") or {}).get("name")
    c3.metric("Version", str(v or "n/a"))   # ensure string (handles Bedrock object)
    motd = result.get("motd")
    if motd:
        st.caption(f"MOTD: `{motd}`")
else:
    st.error("DOWN")
    st.code(result.get("error", "unreachable"))

st.divider()
st.caption("Java → TCP 25565, Bedrock → UDP 19132. MOTD formatting codes stripped. Auto-refresh can be toggled above.")

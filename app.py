import streamlit as st
from mcstatus import JavaServer, BedrockServer
from streamlit_autorefresh import st_autorefresh
import socket
from contextlib import contextmanager
# ---- Defaults
DEFAULT_HOST = "xaprosmp.xyz"
DEFAULT_JAVA_PORT = 25565
DEFAULT_BEDROCK_PORT = 19132
DEFAULT_EDITION = "Java"  # or "Bedrock"

st.set_page_config(page_title="MC Status", page_icon="⛏️", layout="centered")
st.title("Minecraft Server Status")

# ---- Session defaults
if "host" not in st.session_state:
    st.session_state.host = DEFAULT_HOST
if "edition" not in st.session_state:
    st.session_state.edition = DEFAULT_EDITION
if "port" not in st.session_state:
    st.session_state.port = DEFAULT_JAVA_PORT if DEFAULT_EDITION == "Java" else DEFAULT_BEDROCK_PORT

# ---- Controls
with st.container():
    colA, colB, colC = st.columns([1,1,1])
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
        # rerun for immediate UI update (Streamlit ≥1.24 uses st.rerun)
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()

    timeout_ms = st.slider("Timeout (ms)", 500, 5000, 2500, 100)
    auto = st.checkbox("Auto-refresh every 30 s", value=True)
    if auto:
        st_autorefresh(interval=30_000, key="mc_auto")

    manual = st.button("Check now", type="primary")

# Persist any edits
st.session_state.host = host.strip() or DEFAULT_HOST
st.session_state.edition = edition
st.session_state.port = int(port) if port else (DEFAULT_JAVA_PORT if edition == "Java" else DEFAULT_BEDROCK_PORT)
# add near the top


@contextmanager
def temp_socket_timeout(seconds: float):
    prev = socket.getdefaulttimeout()
    socket.setdefaulttimeout(seconds)
    try:
        yield
    finally:
        socket.setdefaulttimeout(prev)

# ---- Helpers
def _clean_motd(desc):
    if desc is None:
        return None
    for attr in ("clean", "text"):
        v = getattr(desc, attr, None)
        if v:
            return v if isinstance(v, str) else str(v)
    try:
        return str(desc)
    except Exception:
        return None

def check_status(host: str, port: int, edition: str, timeout_ms: int):
    secs = max(0.1, timeout_ms / 1000.0)

    def _status_with_timeout(server):
        """Call server.status() compatibly across mcstatus versions."""
        try:
            # Newer mcstatus sometimes supports timeout=...
            return server.status(timeout=secs)
        except TypeError:
            # Older mcstatus: no timeout kwarg → use socket default timeout
            with temp_socket_timeout(secs):
                return server.status()

    def _ping_with_timeout(server):
        """Get latency if status() doesn’t provide it."""
        try:
            return server.ping(timeout=secs)
        except TypeError:
            with temp_socket_timeout(secs):
                return server.ping()
        except Exception:
            return None

    try:
        if edition == "Bedrock":
            server = BedrockServer.lookup(f"{host}:{port}")
            stat = _status_with_timeout(server)

            # mcstatus versions vary—grab fields defensively
            players_online = getattr(stat, "players_online", None)
            players_max    = getattr(stat, "players_max", None)
            latency        = getattr(stat, "latency", None)
            version        = getattr(stat, "version", None)
            motd           = getattr(stat, "motd", None)

            if latency is None:
                latency = _ping_with_timeout(server)

            return {
                "up": True, "edition": "bedrock",
                "latency_ms": latency,
                "players": {"online": players_online, "max": players_max},
                "version": {"name": version},
                "motd": motd,
            }

        else:  # Java
            server = JavaServer.lookup(f"{host}:{port}")  # SRV aware
            stat = _status_with_timeout(server)

            players     = getattr(stat, "players", None)
            online      = getattr(players, "online", None) if players else None
            maxp        = getattr(players, "max", None) if players else None
            version_obj = getattr(stat, "version", None)
            version     = getattr(version_obj, "name", None) if version_obj else None
            desc        = getattr(stat, "description", None)
            motd        = _clean_motd(desc)
            latency     = getattr(stat, "latency", None) or _ping_with_timeout(server)

            return {
                "up": True, "edition": "java",
                "latency_ms": latency,
                "players": {"online": online, "max": maxp},
                "version": {"name": version},
                "motd": motd,
            }

    except Exception as e:
        return {"up": False, "error": str(e)}

# ---- Run a check every rerun (initial, auto, or manual)
with st.spinner("Pinging..."):
    result = check_status(st.session_state.host, st.session_state.port, st.session_state.edition, timeout_ms)

# ---- UI
target = f"{st.session_state.edition.lower()}://{st.session_state.host}:{st.session_state.port}"
st.caption(f"Target: `{target}`")

if result.get("up"):
    st.success("UP")
    c1, c2, c3 = st.columns(3)
    c1.metric("Latency", f"{int(result.get('latency_ms') or 0)} ms")
    p = result.get("players") or {}
    c2.metric("Players", f"{p.get('online') or 0} / {p.get('max') or '?'}")
    v = (result.get("version") or {}).get("name") or "n/a"
    c3.metric("Version", v)
    motd = result.get("motd")
    if motd:
        st.caption(f"MOTD: `{motd}`")
else:
    st.error("DOWN")
    st.code(result.get("error", "unreachable"))

st.divider()
st.caption("Java → TCP 25565, Bedrock → UDP 19132. Bedrock status requires UDP reachability.")

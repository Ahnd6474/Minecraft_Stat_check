import streamlit as st
from mcstatus import JavaServer, BedrockServer
from streamlit_autorefresh import st_autorefresh

# ---- Defaults
DEFAULT_HOST = "xaprosmp.xyz"
DEFAULT_JAVA_PORT = 25565
DEFAULT_BEDROCK_PORT = 19132
DEFAULT_EDITION = "Java"  # change to "Bedrock" if your server is Bedrock

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
        edition = st.radio("Edition", ["Java", "Bedrock"], horizontal=True, index=0 if st.session_state.edition=="Java" else 1)
    with colB:
        host = st.text_input("Host / IP", value=st.session_state.host, placeholder="e.g., play.example.org")
    with colC:
        default_port = DEFAULT_JAVA_PORT if edition == "Java" else DEFAULT_BEDROCK_PORT
        port = st.number_input("Port", value=int(st.session_state.port or default_port),
                               min_value=1, max_value=65535, step=1)

    # One-click reset to your server
    if st.button(f"Use {DEFAULT_HOST}"):
        st.session_state.host = DEFAULT_HOST
        st.session_state.edition = DEFAULT_EDITION
        st.session_state.port = DEFAULT_JAVA_PORT if DEFAULT_EDITION == "Java" else DEFAULT_BEDROCK_PORT
        st.experimental_rerun()

    timeout_ms = st.slider("Timeout (ms)", 500, 5000, 2500, 100)
    auto = st.checkbox("Auto-refresh every 30 s", value=True)
    if auto:
        # triggers a rerun every 30s
        st_autorefresh(interval=30_000, key="mc_auto")

    manual = st.button("Check now", type="primary")

# Persist any edits
st.session_state.host = host.strip() or DEFAULT_HOST
st.session_state.edition = edition
st.session_state.port = int(port) if port else (DEFAULT_JAVA_PORT if edition=="Java" else DEFAULT_BEDROCK_PORT)

# ---- Helper
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
    try:
        if edition == "Bedrock":
            server = BedrockServer.lookup(f"{host}:{port}")
            stat = server.status(timeout=timeout_ms/1000.0)
            return {
                "up": True, "edition": "bedrock",
                "latency_ms": getattr(stat, "latency", None),
                "players": {"online": getattr(stat, "players_online", None),
                            "max": getattr(stat, "players_max", None)},
                "version": {"name": getattr(stat, "version", None)},
                "motd": getattr(stat, "motd", None),
            }
        else:
            server = JavaServer.lookup(f"{host}:{port}")  # resolves SRV if present
            stat = server.status(timeout=timeout_ms/1000.0)
            players = getattr(stat, "players", None)
            version_obj = getattr(stat, "version", None)
            return {
                "up": True, "edition": "java",
                "latency_ms": getattr(stat, "latency", None),
                "players": {"online": getattr(players, "online", None) if players else None,
                            "max": getattr(players, "max", None) if players else None},
                "version": {"name": getattr(version_obj, "name", None) if version_obj else None},
                "motd": _clean_motd(getattr(stat, "description", None)),
            }
    except Exception as e:
        return {"up": False, "error": str(e)}

# ---- Run a check every rerun (covers initial load, auto, and manual)
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

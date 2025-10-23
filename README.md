# Minecraft Server Status Checker

Minecraft Server Status Checker is a simple Streamlit app that tells you whether a Minecraft server is online and how many players are connected. It works with both **Java** and **Bedrock** editions, so you can use it for almost any public or private server.

## Try it online
Use the hosted version here: [minecraftstatuscheck.streamlit.app](https://minecraftstatuscheck.streamlit.app/)

1. Open the link above in your browser.
2. Choose the edition of the server (Java or Bedrock).
3. Enter the server's host name or IP address and the port if it is different from the default.
4. Click **Check now** or enable auto-refresh to let the page update every 30 seconds.

When the server is reachable, you will see:
- A green "UP" message.
- The current latency (ping) in milliseconds.
- The number of players online compared to the maximum.
- The server version and its MOTD (message of the day) with color codes removed for readability.

If the server is offline or unreachable, the app shows a red "DOWN" message along with the error it received. This can help you spot typos in the host name, wrong ports, or connectivity issues.

## Features
- Works for both Java (default port 25565) and Bedrock (default port 19132) servers.
- Auto-refresh option so you can keep the tab open while you wait for friends to log in.
- Built-in button to quickly switch back to the default server configured in the app.
- Strips Minecraft color formatting from MOTD text, making status messages easier to read.

## Run it on your computer
If you want to host the checker yourself or tinker with the code, follow these steps:

1. Install [Python 3.10+](https://www.python.org/downloads/) if you do not already have it.
2. Clone or download this repository.
3. Open a terminal in the project folder and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```
5. Streamlit will open a browser tab (usually at `http://localhost:8501`). Use the page exactly like the hosted version.

## Tips
- You do not need to know the difference between an IP address and a host name—just paste whatever you normally use in Minecraft's "Server Address" box.
- If your server uses a custom port, type the number provided by your host. Otherwise, leave the default in place.
- Bedrock servers often require you to double-check that the edition is set correctly. A Java server will not answer if you switch to Bedrock mode, and vice versa.

## Troubleshooting
- **Timeouts or "No connection" errors:** the server is probably offline, your firewall/router is blocking the connection, or the address is wrong. Try again later or confirm the details with your host.
- **App does not load locally:** make sure you installed the requirements and that you are running the command in the same Python environment.
- **Need to check another server quickly?** Use the "Use xaprosmp.xyz" button to reset to the default server, then enter the next address.

## License
This project is released under the [MIT License](LICENSE), so you are free to use and modify it for your own needs.

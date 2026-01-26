FROM node:20-bookworm

# A. INSTALL GUI & ADMIN TOOLS
# xfce4 = The Desktop
# tightvncserver = The Remote Access
# autocutsel = The Clipboard Fixer
# vim, curl, wget, git, ping, net-tools = Your Admin Tools
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    xfce4 xfce4-goodies tightvncserver autocutsel dbus-x11 \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libgbm1 libasound2 \
    libpangocairo-1.0-0 libxss1 libgtk-3-0 \
    wget curl vim iputils-ping git firefox-esr procps net-tools \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# B. INSTALL KENKU FM
WORKDIR /app
RUN wget https://github.com/owlbear-rodeo/kenku-fm/releases/download/v1.5.4/kenku-fm_1.5.4_amd64.deb -O kenku.deb && \
    apt-get install -y ./kenku.deb && \
    rm kenku.deb

# C. CREATE STARTUP SCRIPT
# This runs every time the container starts.
RUN echo '#!/bin/bash\n\
\n\
# 1. SETUP VNC PASSWORD\n\
mkdir -p /root/.vnc\n\
echo "${VNC_PASSWORD:-realmquest123}" | vncpasswd -f > /root/.vnc/passwd\n\
chmod 600 /root/.vnc/passwd\n\
\n\
# 2. CLEANUP LOCKS (Fixes "black screen" on restart)\n\
rm -rf /tmp/.X1-lock /tmp/.X11-unix/X1 /var/run/dbus/pid\n\
mkdir -p /var/run/dbus\n\
\n\
# 3. ENABLE CLIPBOARD SYNC (Text Copy/Paste)\n\
# We run it twice to sync both Primary and Clipboard buffers\n\
autocutsel -fork\n\
autocutsel -selection PRIMARY -fork\n\
\n\
# 4. START VNC SERVER\n\
USER=root vncserver :1 -geometry 1280x720 -depth 24\n\
\n\
# 5. LINK MAGIC FOLDERS\n\
# Ensure the Desktop shows our mapped files\n\
ln -sfn /root/Desktop_Host /root/Desktop\n\
\n\
# 6. LAUNCH KENKU (Visual Mode)\n\
export DISPLAY=:1\n\
echo "🚀 Starting Kenku FM..."\n\
/usr/bin/kenku-fm --no-sandbox &\n\
\n\
# 7. KEEP ALIVE\n\
tail -f /root/.vnc/*.log\n\
' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    USER=agent \
    HOME=/home/agent \
    WORKSPACE=/workspace \
    DISPLAY=:0 \
    VNC_PORT=5900 \
    NOVNC_PORT=6080 \
    JUPYTER_PORT=8888 \
    API_PORT=3000 \
    VNC_RESOLUTION=1280x800 \
    VNC_COL_DEPTH=24

# Application environment variables (can be overridden at runtime)
ENV NODE_ENV=production \
    ENV=production \
    DEBUG=false \
    PORT=3000 \
    LOG_LEVEL=INFO \
    LOG_TO_FILE=true \
    LOG_TO_CONSOLE=true \
    LOG_FORMAT=detailed

# Install essential packages including fluxbox and supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    xvfb x11vnc fluxbox \
    xdot \
    supervisor \
    curl wget git netcat-openbsd \
    gedit xterm libcanberra-gtk-module \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC and websockify
RUN wget -O /tmp/novnc.tar.gz https://github.com/novnc/noVNC/archive/v1.4.0.tar.gz && \
    tar -xzf /tmp/novnc.tar.gz -C /opt && \
    mv /opt/noVNC-1.4.0 /opt/novnc && \
    ln -s /opt/novnc/vnc.html /opt/novnc/index.html && \
    rm /tmp/novnc.tar.gz && \
    git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify

# Create user and workspace
RUN useradd -m $USER && \
    mkdir -p $WORKSPACE && \
    mkdir -p /home/$USER/.vnc && \
    mkdir -p /opt/agent/workspace && \
    chown -R $USER:$USER $WORKSPACE /opt /home/$USER

# Copy requirements and install Python packages
WORKDIR /opt/agent
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code and configuration
COPY src ./src
COPY scripts ./scripts
# Copy .env file if it exists (use .env.example as template)
COPY .env* ./
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY conf.d /app/conf.d
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
# Copy workspace files
COPY workspace/runable.txt /opt/agent/workspace/runable.txt

# Set permissions and ownership
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chown -R $USER:$USER /opt/agent /usr/local/bin/entrypoint.sh && \
    mkdir -p /opt/agent/context_storage /opt/agent/jobs /opt/agent/logs && \
    chown -R $USER:$USER /opt/agent/context_storage /opt/agent/jobs /opt/agent/logs /opt/agent/workspace && \
    chmod -R 755 /opt/agent/context_storage /opt/agent/jobs /opt/agent/logs /opt/agent/workspace

EXPOSE 6080 8888 3000

USER $USER
CMD ["/usr/local/bin/entrypoint.sh"]

# SETUP INSTRUCTIONS:
# 1. Create a .env file in the project root with your API keys:
#    echo "GOOGLE_API_KEY=your_actual_gemini_api_key_here" > .env
#    echo "X_API_KEY=your_x_api_key_here" >> .env
#    echo "DEBUG=true" >> .env
#
# 2. Build: docker build -f Dockerfile -t runable .
# 3. Run: docker run -d --name runable -p 6080:6080 -p 8888:8888 -p 3000:3000 runable
# 
# Alternative: Override environment variables at runtime:
# docker run -d --name runable -p 6080:6080 -p 8888:8888 -p 3000:3000 -e GOOGLE_API_KEY="your_key" runable 
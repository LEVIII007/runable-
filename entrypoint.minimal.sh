#!/bin/bash

set -e

echo "🚀 Starting Minimal Runable AI Container..."

# Start Xvfb (virtual display)
echo "📺 Starting virtual display..."
Xvfb :0 -screen 0 1280x800x24 &
XVFB_PID=$!
sleep 2

# Start VNC server (no password)
echo "🔗 Starting VNC server..."
x11vnc -display :0 -forever -shared -rfbport 5900 -nopw -quiet &
VNC_PID=$!
sleep 2

# Start noVNC web interface
echo "🌐 Starting web VNC interface..."
cd /opt/novnc
python3 -m websockify --web . 6080 localhost:5900 &
NOVNC_PID=$!
sleep 3

echo "💡 noVNC should be accessible at: http://localhost:6080/vnc.html"

# Start Jupyter Lab
echo "📓 Starting Jupyter Lab..."
cd /workspace
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password='' &
JUPYTER_PID=$!
sleep 2

# Start API service
echo "🤖 Starting API service..."
cd /opt/agent
PYTHONPATH=/opt/agent/src python3 -m src.runable.main &
API_PID=$!

echo ""
echo "✅ All services started!"
echo ""
echo "🌐 Access Points:"
echo "  📺 VNC Desktop: http://localhost:6080"
echo "  📓 Jupyter Lab: http://localhost:8888"  
echo "  🤖 API Server: http://localhost:3000"
echo ""
echo "🎯 Ready for coding tasks!"

# Cleanup function
cleanup() {
    echo "🛑 Shutting down..."
    kill $API_PID $JUPYTER_PID $NOVNC_PID $VNC_PID $XVFB_PID 2>/dev/null || true
    exit 0
}

# Handle shutdown signals
trap cleanup SIGTERM SIGINT

# Keep container alive
wait 
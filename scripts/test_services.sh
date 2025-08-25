#!/bin/bash

echo "🧪 Testing all services..."

# Test VNC server
echo "1. Testing VNC server on port 5900..."
if nc -z localhost 5900; then
    echo "   ✅ VNC server is running"
else
    echo "   ❌ VNC server is not responding"
fi

# Test noVNC web interface
echo "2. Testing noVNC web interface on port 6080..."
if nc -z localhost 6080; then
    echo "   ✅ noVNC web interface is running"
    echo "   🌐 Access: http://localhost:6080"
else
    echo "   ❌ noVNC web interface is not responding"
fi

# Test Jupyter Lab
echo "3. Testing Jupyter Lab on port 8888..."
if nc -z localhost 8888; then
    echo "   ✅ Jupyter Lab is running"
    echo "   📓 Access: http://localhost:8888"
else
    echo "   ❌ Jupyter Lab is not responding"
fi

# Test API server
echo "4. Testing API server on port 3000..."
if nc -z localhost 3000; then
    echo "   ✅ API server is running"
    echo "   🤖 Access: http://localhost:3000"
else
    echo "   ❌ API server is not responding"
fi

# Test X11 display
echo "5. Testing X11 display..."
if DISPLAY=:0 xdpyinfo > /dev/null 2>&1; then
    echo "   ✅ X11 display is working"
else
    echo "   ❌ X11 display is not working"
fi

# Test xdot
echo "6. Testing xdot availability..."
if command -v xdot >/dev/null 2>&1; then
    echo "   ✅ xdot is available"
else
    echo "   ❌ xdot is not available"
fi

echo ""
echo "🎯 Service Summary:"
echo "   VNC Desktop: http://localhost:6080 (no password)"
echo "   Jupyter Lab: http://localhost:8888 (no token required)"
echo "   API Server: http://localhost:3000"

echo ""
echo "💡 To test xdot visualization:"
echo "   python3 /opt/agent/scripts/test_xdot.py" 
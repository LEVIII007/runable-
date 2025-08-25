#!/bin/bash
set -e

# Set permissive umask for file creation
umask 022

echo "🚀 Starting Runable AI Container with Supervisord..."

# Ensure all application directories exist with correct permissions
mkdir -p /opt/agent/workspace /opt/agent/context_storage /opt/agent/jobs /opt/agent/logs
chown -R agent:agent /opt/agent/workspace /opt/agent/context_storage /opt/agent/jobs /opt/agent/logs
chmod -R 755 /opt/agent/workspace /opt/agent/context_storage /opt/agent/jobs /opt/agent/logs

# Ensure runable.txt exists and has correct permissions
if [ ! -f /opt/agent/workspace/runable.txt ]; then
    echo "HELLO USER" > /opt/agent/workspace/runable.txt
    echo "" >> /opt/agent/workspace/runable.txt
    echo "Please wait while the agent is generating the code..." >> /opt/agent/workspace/runable.txt
    echo "" >> /opt/agent/workspace/runable.txt
    echo "This file will be automatically updated as the AI agent works on your project." >> /opt/agent/workspace/runable.txt
fi
chown agent:agent /opt/agent/workspace/runable.txt
chmod 644 /opt/agent/workspace/runable.txt

echo "🎯 Starting services via supervisord..."
echo ""
echo "🌐 Access Points:"
echo "  📺 VNC Desktop: http://localhost:6080"
echo "  📓 Jupyter Lab: http://localhost:8888"  
echo "  🤖 API Server: http://localhost:3000"
echo ""

# Start supervisord which will manage all services
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf 
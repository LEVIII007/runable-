#!/usr/bin/env python3
"""
Test script to verify xdot visualization works
Usage: python3 test_xdot.py
"""

import subprocess
import tempfile
import os

def create_test_graph():
    """Create a simple DOT graph for testing"""
    dot_content = """
    digraph TestGraph {
        rankdir=LR;
        node [shape=circle];
        
        A -> B -> C;
        A -> D;
        D -> C;
        
        A [label="Start"];
        B [label="Process"];
        C [label="End"];
        D [label="Alternative"];
    }
    """
    return dot_content

def test_xdot():
    """Test xdot visualization"""
    print("🧪 Testing xdot visualization...")
    
    # Create temporary DOT file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as f:
        f.write(create_test_graph())
        dot_file = f.name
    
    try:
        # Set display
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        
        # Launch xdot
        print(f"🖥️ Opening graph visualization with xdot...")
        print(f"   File: {dot_file}")
        print(f"   Access via VNC: http://localhost:6080")
        
        subprocess.Popen(['xdot', dot_file], env=env)
        print("✅ xdot launched successfully!")
        print("💡 You should see the graph in the VNC viewer")
        
    except Exception as e:
        print(f"❌ Error launching xdot: {e}")
    finally:
        # Clean up
        try:
            os.unlink(dot_file)
        except:
            pass

if __name__ == "__main__":
    test_xdot() 
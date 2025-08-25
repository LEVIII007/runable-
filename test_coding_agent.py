#!/usr/bin/env python3
"""
Test script for the coding agent functionality.
"""

import asyncio
import requests
import json
import time
from pathlib import Path

# Test the API endpoints
BASE_URL = "http://localhost:3000/api/coding-agent"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Active jobs: {data['active_jobs']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False

def test_schedule_task():
    """Test scheduling a simple coding task"""
    print("\n🔍 Testing task scheduling...")
    
    task_data = {
        "task": "Write a Python function to calculate the factorial of 5 and print the result. Include proper error handling.",
        "language": "python",
        "max_iterations": 3,
        "timeout": 120,
        "debug_mode": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/schedule", json=task_data)
        if response.status_code == 200:
            data = response.json()
            job_id = data["job_id"]
            print(f"✅ Task scheduled successfully!")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {data['status']}")
            print(f"   Estimated completion: {data.get('estimated_completion', 'Unknown')} seconds")
            return job_id
        else:
            print(f"❌ Task scheduling failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Task scheduling error: {str(e)}")
        return None

def test_job_status(job_id):
    """Test getting job status"""
    print(f"\n🔍 Testing job status for {job_id}...")
    
    max_attempts = 30  # Wait up to 5 minutes
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{BASE_URL}/status/{job_id}")
            if response.status_code == 200:
                data = response.json()
                status = data["status"]
                progress = data["progress"]
                
                print(f"   Status: {status} ({progress}%)")
                print(f"   Iteration: {data['current_iteration']}/{data['max_iterations']}")
                
                if status == "completed":
                    print("✅ Job completed successfully!")
                    print(f"   Final output: {data.get('final_output', 'No output')[:200]}...")
                    print(f"   Files created: {data.get('files_created', [])}")
                    if data.get('download_link'):
                        print(f"   Download link: {data['download_link']}")
                    return True
                elif status == "failed":
                    print(f"❌ Job failed: {data.get('error_message', 'Unknown error')}")
                    return False
                elif status in ["pending", "running"]:
                    print(f"   ⏳ Job still {status}, waiting...")
                    time.sleep(10)
                    attempt += 1
                else:
                    print(f"❌ Unknown status: {status}")
                    return False
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Status check error: {str(e)}")
            return False
    
    print(f"❌ Job did not complete within {max_attempts * 10} seconds")
    return False

def test_list_jobs():
    """Test listing jobs"""
    print("\n🔍 Testing job listing...")
    
    try:
        response = requests.get(f"{BASE_URL}/jobs?page=1&page_size=5")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Jobs listed successfully!")
            print(f"   Total jobs: {data['total']}")
            print(f"   Jobs on this page: {len(data['jobs'])}")
            
            for i, job in enumerate(data['jobs'][:3]):  # Show first 3
                print(f"   Job {i+1}: {job['job_id']} - {job['status']}")
            
            return True
        else:
            print(f"❌ Job listing failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Job listing error: {str(e)}")
        return False

def test_direct_workflow():
    """Test the workflow directly without API"""
    print("\n🔍 Testing workflow directly...")
    
    try:
        from src.ai.workflows.coding_agent_workflow import run_coding_task
        
        task = "Write a Python function that calculates the sum of squares of numbers 1 to 10"
        
        print(f"   Running task: {task}")
        result = run_coding_task(task, max_iterations=3, debug_mode=True)
        
        if result["success"]:
            print("✅ Direct workflow test passed!")
            print(f"   Session ID: {result['session_id']}")
            print(f"   Iterations: {result['iterations']}")
            print(f"   Output: {result.get('final_output', 'No output')[:200]}...")
            return True
        else:
            print(f"❌ Direct workflow test failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Direct workflow test error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Coding Agent Tests...\n")
    
    # Test 1: Direct workflow (doesn't require API server)
    direct_success = test_direct_workflow()
    
    # Test 2: API tests (requires server to be running)
    print("\n" + "="*50)
    print("API Tests (requires server running on localhost:3000)")
    print("="*50)
    
    health_success = test_health_check()
    
    if health_success:
        job_id = test_schedule_task()
        
        if job_id:
            status_success = test_job_status(job_id)
            list_success = test_list_jobs()
        else:
            status_success = False
            list_success = False
    else:
        print("\n⚠️  Server not running. Skipping API tests.")
        print("   To test API endpoints, run: python -m src.trench_ai.main")
        job_id = None
        status_success = False
        list_success = False
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Direct Workflow: {'✅ PASS' if direct_success else '❌ FAIL'}")
    print(f"Health Check: {'✅ PASS' if health_success else '❌ FAIL'}")
    print(f"Task Scheduling: {'✅ PASS' if job_id else '❌ FAIL'}")
    print(f"Job Status: {'✅ PASS' if status_success else '❌ FAIL'}")
    print(f"Job Listing: {'✅ PASS' if list_success else '❌ FAIL'}")
    
    overall_success = direct_success and (not health_success or (health_success and job_id and status_success and list_success))
    print(f"\nOverall: {'✅ SUCCESS' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if not health_success:
        print("\n💡 To run the full test suite:")
        print("   1. Start the server: python -m src.trench_ai.main")
        print("   2. In another terminal, run: python test_coding_agent.py")

if __name__ == "__main__":
    main() 
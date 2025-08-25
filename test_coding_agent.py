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

def test_schedule_task():
    """Test scheduling a practical coding task"""
    print("\n🔍 Testing task scheduling...")
    
    task_data = {
        "task": """Solve this algorithmic problem:

Given an array of integers, find the length of the longest subarray with sum equal to zero.

Example:
Input: [15, -2, 2, -8, 1, 7, 10, 23]
Output: 5 (subarray [-2, 2, -8, 1, 7] has sum = 0)

Requirements:
1. Implement an efficient solution (O(n) time complexity)
2. Handle edge cases (empty array, no zero-sum subarray)
3. Print the subarray elements along with the length
4. Test with multiple test cases including the example above
5. Add comments explaining your approach

Bonus: Also find and print all subarrays with zero sum.""",
        "language": "python",
        "max_iterations": 10,
        "timeout": 300,
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

def main():
    """Run all tests"""
    print("🚀 Starting Coding Agent Tests...\n")
    
    # Test 1: API tests (requires server to be running)
    print("\n" + "="*50)
    print("API Tests (requires server running on localhost:3000)")
    print("="*50)
    

    job_id = test_schedule_task()
    
    if job_id:
        status_success = test_job_status(job_id)
        list_success = test_list_jobs()
    else:
        status_success = False
        list_success = False
    
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Task Scheduling: {'✅ PASS' if job_id else '❌ FAIL'}")
    print(f"Job Status: {'✅ PASS' if status_success else '❌ FAIL'}")
    print(f"Job Listing: {'✅ PASS' if list_success else '❌ FAIL'}")
    
    overall_success = job_id and status_success and list_success
    print(f"\nOverall: {'✅ SUCCESS' if overall_success else '❌ SOME TESTS FAILED'}")
    

if __name__ == "__main__":
    main() 
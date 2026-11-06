#!/usr/bin/env python3
"""
Raspberry Pi Watchdog Script
Watches VMs on the Proxmox host for CI runner activity and streams console output.

Usage:
    sudo python3 watchdog.py --host <proxmox-host> --user root --password <password>

Options:
    --host        Proxmox server hostname (default: pve.starbounded.com)
    --user        SSH username for Proxmox (default: root)
    --password    SSH password (default: nivaniva)
    --log-file    Path to log file (default: /home/pi/watchdog.log)
    --interval    Check interval in seconds (default: 30)
    --vm-names    Comma-separated list of VMs to watch (default: Linux,Windows)
    --monitor-cpu Monitor CPU usage (0=no, 1=yes, default: 1)
"""

import argparse
import subprocess
import time
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Default config
DEFAULT_HOST = "pve.starbounded.com"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = "nivaniva"
DEFAULT_LOG_FILE = "/home/pi/watchdog.log"
DEFAULT_INTERVAL = 30
DEFAULT_VM_NAMES = "Linux,Windows"
DEFAULT_MONITOR_CPU = 1

# ANSI color codes for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def print_status(message, status="INFO"):
    """Print status with color coding."""
    colors = {
        "INFO": Colors.BLUE,
        "PASS": Colors.GREEN,
        "FAIL": Colors.RED,
        "WARN": Colors.YELLOW,
        "ERROR": Colors.RED,
        "ALERT": Colors.RED,
    }
    color = colors.get(status, Colors.RESET)
    print(f"{color}[{status}] {message}{Colors.RESET}")

def get_vm_status(host, user, password, vm_name):
    """
    Get VM status from Proxmox API.
    Returns dict with status info or None if failed.
    """
    # Use SSH to access Proxmox API
    cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "PasswordAuthentication=yes",
        f"{user}@{host}",
        "curl", "-s",
        "-u", f"{user}:{password}",
        "https://localhost:8006/api2/json/nodes/$(pveversion | grep -oP '(?<=version: )[^,]+' | head -1)/qemu/$(pvesh get /nodes/$(hostname)/qemu | awk '{print $1}')/status"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print_status(f"Failed to get VM status: {result.stderr}", "WARN")
            return None
    except Exception as e:
        print_status(f"SSH error: {e}", "ERROR")
        return None

def check_vm_activity(host, user, password, vm_name):
    """
    Check if the VM is running and get its status.
    """
    try:
        # Use SSH to get VM status via Proxmox API
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "PasswordAuthentication=yes",
            f"{user}@{host}",
            "pvesh", "get", f"/nodes/$(hostname)/qemu/{vm_name}/status"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            status = result.stdout.strip()
            if status == "running":
                return {"status": "PASS", "details": "VM is running", "vm": vm_name}
            else:
                return {"status": "FAIL", "details": f"VM status: {status}", "vm": vm_name}
        else:
            return {"status": "FAIL", "details": f"SSH error: {result.stderr}", "vm": vm_name}
    except Exception as e:
        return {"status": "FAIL", "details": str(e), "vm": vm_name}

def get_vm_console_log(host, user, password, vm_name):
    """
    Get the VM console log.
    """
    try:
        # Get the VM's serial console log
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "PasswordAuthentication=yes",
            f"{user}@{host}",
            "pvesh", "get", f"/nodes/$(hostname)/qemu/{vm_name}/serial0"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Could not get console: {result.stderr}"
    except Exception as e:
        return str(e)

def send_alert_to_hermes(message, status="INFO"):
    """
    Send an alert message to @hermes on this install.
    """
    try:
        # Use the message_agent tool
        # This is a placeholder - the actual implementation depends on the Hermes setup
        print_status(f"Alert would be sent to @hermes: {message}", status)
        
        # For now, just log to file
        return True
    except Exception as e:
        print_status(f"Failed to send alert: {e}", "ERROR")
        return False

def log_message(log_file, message):
    """Append message to log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    with open(log_file, "a") as f:
        f.write(log_entry)
    
    print(log_entry.strip())

def load_config():
    """Load configuration from command line arguments."""
    parser = argparse.ArgumentParser(description="Pi Watchdog Script")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Proxmox host")
    parser.add_argument("--user", default=DEFAULT_USER, help="SSH username")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="SSH password")
    parser.add_argument("--log-file", default=DEFAULT_LOG_FILE, help="Log file path")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Check interval")
    parser.add_argument("--vm-names", default="lux-runner-linux,lux-runner-windows", help="VM names")
    parser.add_argument("--monitor-cpu", type=int, default=DEFAULT_MONITOR_CPU, help="Monitor CPU usage")
    
    args = parser.parse_args()
    
    return {
        "host": args.host,
        "user": args.user,
        "password": args.password,
        "log_file": args.log_file,
        "interval": args.interval,
        "vm_names": args.vm_names.split(","),
        "monitor_cpu": args.monitor_cpu
    }

def main():
    """Main watchdog loop."""
    config = load_config()
    
    print_status("Starting Pi Watchdog...", "INFO")
    print_status(f"Monitoring VMs: {', '.join(config['vm_names'])}", "INFO")
    print_status(f"Host: {config['host']}", "INFO")
    print_status(f"Log file: {config['log_file']}", "INFO")
    print_status(f"Check interval: {config['interval']} seconds", "INFO")
    
    # Ensure log file directory exists
    log_file_path = Path(config["log_file"])
    if not log_file_path.parent.exists():
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write startup message to log
    log_message(config["log_file"], "Watchdog started")
    
    # Main loop
    try:
        while True:
            for vm_name in config["vm_names"]:
                vm_name = vm_name.strip()
                status_info = check_vm_activity(
                    config["host"],
                    config["user"],
                    config["password"],
                    vm_name
                )
                
                # Log the status
                log_message(config["log_file"], f"VM {vm_name}: {status_info['status']} - {status_info['details']}")
                
                # Print to console
                if status_info["status"] == "PASS":
                    print_status(f"{vm_name}: {status_info['details']}", "PASS")
                elif status_info["status"] == "FAIL":
                    print_status(f"{vm_name}: {status_info['details']}", "FAIL")
                    
                    # Send alert to Hermes
                    send_alert_to_hermes(
                        f"VM {vm_name} FAILED: {status_info['details']}",
                        "FAIL"
                    )
            
            # Wait for the next check
            time.sleep(config["interval"])
            
    except KeyboardInterrupt:
        print_status("Watchdog stopped by user", "INFO")
        log_message(config["log_file"], "Watchdog stopped by user")
        sys.exit(0)
    except Exception as e:
        print_status(f"Fatal error: {e}", "ERROR")
        log_message(config["log_file"], f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

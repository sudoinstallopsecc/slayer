#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLAYER - HTTP Load Testing Tool
A professional, simple, and effective load testing solution.
"""

import os
import sys
import time
import threading
import requests
from datetime import datetime
from collections import defaultdict
from statistics import mean, median
from queue import Queue
from urllib.parse import urlparse


class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'


class ProgressBar:
    """Display a text-based progress bar."""
    
    def __init__(self, total_seconds, width=50):
        self.total_seconds = total_seconds
        self.width = width
        self.start_time = time.time()
        
    def render(self, current_second):
        """Render progress bar with percentage."""
        percent = min(100, int((current_second / self.total_seconds) * 100))
        filled = int((percent / 100) * self.width)
        bar = '█' * filled + '░' * (self.width - filled)
        return f"[{bar}] {percent}%"


class Statistics:
    """Collect and analyze load test statistics."""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.status_codes = defaultdict(int)
        self.response_times = []
        self.errors = defaultdict(int)
        self.start_time = None
        self.end_time = None
        self.lock = threading.Lock()
        
    def record_request(self, status_code, response_time, error=None, validation_failed=False):
        """Record a single request result."""
        with self.lock:
            self.total_requests += 1
            self.response_times.append(response_time)
            self.status_codes[status_code] += 1
            
            if 200 <= status_code < 300:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                
            if validation_failed:
                self.errors['validation_failed'] += 1
            elif error:
                self.errors[error] += 1
                
    def get_statistics(self):
        """Return current statistics summary."""
        if not self.response_times:
            return None
            
        latencies = sorted(self.response_times)
        n = len(latencies)
        
        return {
            'total': self.total_requests,
            'successful': self.successful_requests,
            'failed': self.failed_requests,
            'error_rate': (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            'min_latency': min(latencies),
            'max_latency': max(latencies),
            'avg_latency': mean(latencies),
            'median_latency': median(latencies),
            'p95_latency': latencies[int(n * 0.95)] if n > 0 else 0,
            'p99_latency': latencies[int(n * 0.99)] if n > 0 else 0,
            'status_codes': dict(self.status_codes),
            'errors': dict(self.errors),
        }


class LoadTester:
    """Main load testing engine."""
    
    def __init__(self):
        self.config = {}
        self.statistics = Statistics()
        self.running = False
        self.stop_event = threading.Event()
        self.request_queue = Queue()
        
    def print_header(self):
        """Display welcome header."""
        print("\n" + "=" * 70)
        print(f"{Colors.BOLD}SLAYER - HTTP Load Testing Tool{Colors.RESET}")
        print(f"{Colors.DIM}A professional load testing solution{Colors.RESET}")
        print("=" * 70 + "\n")
        
    def print_separator(self, char="─", length=70):
        """Print a visual separator."""
        print(Colors.DIM + char * length + Colors.RESET)
        
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def prompt(self, message, default=None, options=None):
        """Display a prompt and get user input."""
        if options:
            print(f"\n{Colors.CYAN}{message}{Colors.RESET}")
            for i, option in enumerate(options, 1):
                print(f"  {i}. {option}")
            while True:
                choice = input(f"\nSelect option (1-{len(options)}): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(options):
                    return options[int(choice) - 1]
                print(f"{Colors.RED}Invalid selection. Please try again.{Colors.RESET}")
        else:
            if default:
                prompt_text = f"{Colors.CYAN}{message} [{default}]: {Colors.RESET}"
            else:
                prompt_text = f"{Colors.CYAN}{message}: {Colors.RESET}"
            response = input(prompt_text).strip()
            return response if response else default
            
    def validate_url(self, url):
        """Validate if URL is properly formatted."""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False
            
    def configure_test(self):
        """Interactive configuration wizard."""
        self.clear_screen()
        self.print_header()
        print("Test Configuration")
        self.print_separator()
        
        # Target URL
        while True:
            url = self.prompt("Enter target URL")
            if self.validate_url(url):
                self.config['url'] = url
                break
            print(f"{Colors.RED}Invalid URL format. Please try again.{Colors.RESET}")
            
        # HTTP Method
        method = self.prompt(
            "Select HTTP method",
            default="GET",
            options=["GET", "POST", "PUT", "DELETE"]
        )
        self.config['method'] = method
        
        # Number of threads
        while True:
            threads = self.prompt("Number of concurrent threads", default="50")
            if threads.isdigit() and 1 <= int(threads) <= 1000:
                self.config['threads'] = int(threads)
                break
            print(f"{Colors.RED}Please enter a number between 1 and 1000.{Colors.RESET}")
            
        # Duration
        while True:
            duration = self.prompt("Test duration in seconds", default="60")
            if duration.isdigit() and 1 <= int(duration) <= 3600:
                self.config['duration'] = int(duration)
                break
            print(f"{Colors.RED}Please enter a number between 1 and 3600.{Colors.RESET}")
            
        # Traffic pattern
        pattern = self.prompt(
            "Select traffic pattern",
            default="Constant",
            options=["Constant", "Ramp-up", "Spike"]
        )
        self.config['pattern'] = pattern
        
        # Target RPS (Requests Per Second)
        while True:
            rps = self.prompt("Target requests per second (RPS)", default="100")
            if rps.isdigit() and 1 <= int(rps) <= 100000:
                self.config['target_rps'] = int(rps)
                break
            print(f"{Colors.RED}Please enter a number between 1 and 100000.{Colors.RESET}")
            
        # Pattern-specific configuration
        if pattern == "Ramp-up":
            while True:
                start_rps = self.prompt("Starting RPS", default="10")
                if start_rps.isdigit() and 1 <= int(start_rps) <= int(self.config['target_rps']):
                    self.config['start_rps'] = int(start_rps)
                    break
                print(f"{Colors.RED}Starting RPS must be less than target RPS.{Colors.RESET}")
                
        elif pattern == "Spike":
            while True:
                spike_duration = self.prompt("Spike duration in seconds", default="10")
                if spike_duration.isdigit() and 1 <= int(spike_duration) < self.config['duration']:
                    self.config['spike_duration'] = int(spike_duration)
                    break
                print(f"{Colors.RED}Spike duration must be less than test duration.{Colors.RESET}")
                
        # Response validation
        validation = self.prompt(
            "Enable response validation",
            options=["No", "Check status code", "Validate response content"]
        )
        
        if validation != "No":
            self.config['validation_enabled'] = True
            self.config['validation_type'] = validation
            if validation == "Validate response content":
                keyword = self.prompt("Enter keyword to search in response")
                self.config['validation_keyword'] = keyword
        else:
            self.config['validation_enabled'] = False
            
        # Timeout
        while True:
            timeout = self.prompt("Request timeout in seconds", default="10")
            if timeout.isdigit() and 1 <= int(timeout) <= 60:
                self.config['timeout'] = int(timeout)
                break
            print(f"{Colors.RED}Please enter a number between 1 and 60.{Colors.RESET}")
        
    def display_configuration(self):
        """Show current test configuration."""
        self.clear_screen()
        self.print_header()
        print("Current Configuration")
        self.print_separator()
        
        for key, value in self.config.items():
            formatted_key = key.replace('_', ' ').title()
            print(f"  {formatted_key:.<40} {Colors.BLUE}{value}{Colors.RESET}")
            
        self.print_separator()
        print("\n")
        
    def calculate_rps_for_second(self, current_second):
        """Calculate RPS for current second based on traffic pattern."""
        pattern = self.config.get('pattern', 'Constant')
        target_rps = self.config['target_rps']
        duration = self.config['duration']
        
        if pattern == "Constant":
            return target_rps
            
        elif pattern == "Ramp-up":
            start_rps = self.config.get('start_rps', 10)
            rps_increase = (target_rps - start_rps) / duration
            return start_rps + (rps_increase * current_second)
            
        elif pattern == "Spike":
            spike_duration = self.config.get('spike_duration', 10)
            if current_second < spike_duration:
                return target_rps * 2
            else:
                return target_rps
                
        return target_rps
        
    def validate_response(self, response):
        """Validate response based on configuration."""
        if not self.config.get('validation_enabled', False):
            return True
            
        validation_type = self.config.get('validation_type')
        
        if validation_type == "Check status code":
            return 200 <= response.status_code < 300
            
        elif validation_type == "Validate response content":
            keyword = self.config.get('validation_keyword', '')
            try:
                return keyword.lower() in response.text.lower()
            except:
                return False
                
        return True
        
    def worker(self, thread_id):
        """Worker thread that makes HTTP requests."""
        url = self.config['url']
        method = self.config['method']
        timeout = self.config['timeout']
        
        while self.running:
            try:
                request_count = self.request_queue.qsize()
                if request_count <= 0:
                    time.sleep(0.001)
                    continue
                    
                self.request_queue.get()
                
                start_time = time.time()
                
                try:
                    if method == "GET":
                        response = requests.get(url, timeout=timeout)
                    elif method == "POST":
                        response = requests.post(url, timeout=timeout)
                    elif method == "PUT":
                        response = requests.put(url, timeout=timeout)
                    elif method == "DELETE":
                        response = requests.delete(url, timeout=timeout)
                        
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    validation_ok = self.validate_response(response)
                    
                    self.statistics.record_request(
                        response.status_code,
                        response_time,
                        validation_failed=not validation_ok
                    )
                    
                except requests.exceptions.Timeout:
                    response_time = (time.time() - start_time) * 1000
                    self.statistics.record_request(0, response_time, error="timeout")
                except requests.exceptions.ConnectionError:
                    response_time = (time.time() - start_time) * 1000
                    self.statistics.record_request(0, response_time, error="connection_error")
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    self.statistics.record_request(0, response_time, error="unknown_error")
                    
            except Exception as e:
                pass
                
    def print_report(self, elapsed_seconds):
        """Print current test report."""
        stats = self.statistics.get_statistics()
        if not stats:
            return
            
        progress_bar = ProgressBar(self.config['duration'])
        print(f"\n{progress_bar.render(elapsed_seconds)}")
        print(f"Time: {elapsed_seconds}s / {self.config['duration']}s | ", end="")
        print(f"Requests: {stats['total']} | ", end="")
        print(f"Current RPS: {int(stats['total'] / max(elapsed_seconds, 1))}")
        
        self.print_separator()
        
        # Request Summary
        print(f"\n{Colors.BOLD}Request Summary{Colors.RESET}")
        print(f"  Total Requests............ {Colors.BLUE}{stats['total']}{Colors.RESET}")
        print(f"  Successful (2xx)......... {Colors.GREEN}{stats['successful']}{Colors.RESET}")
        print(f"  Failed (other)........... {Colors.RED}{stats['failed']}{Colors.RESET}")
        print(f"  Error Rate............... {Colors.YELLOW}{stats['error_rate']:.2f}%{Colors.RESET}")
        
        # Latency Statistics
        print(f"\n{Colors.BOLD}Latency Statistics (ms){Colors.RESET}")
        print(f"  Minimum.................. {stats['min_latency']:.2f} ms")
        print(f"  Maximum.................. {stats['max_latency']:.2f} ms")
        print(f"  Average.................. {stats['avg_latency']:.2f} ms")
        print(f"  Median (p50)............. {stats['median_latency']:.2f} ms")
        print(f"  95th Percentile (p95).... {stats['p95_latency']:.2f} ms")
        print(f"  99th Percentile (p99).... {stats['p99_latency']:.2f} ms")
        
        # HTTP Status Codes
        if stats['status_codes']:
            print(f"\n{Colors.BOLD}HTTP Status Codes{Colors.RESET}")
            for code in sorted(stats['status_codes'].keys()):
                count = stats['status_codes'][code]
                percentage = (count / stats['total']) * 100
                color = Colors.GREEN if 200 <= code < 300 else Colors.RED
                print(f"  {code}........................ {color}{count}{Colors.RESET} ({percentage:.1f}%)")
                
        # Errors
        if stats['errors']:
            print(f"\n{Colors.BOLD}Error Details{Colors.RESET}")
            for error_type, count in stats['errors'].items():
                print(f"  {error_type}.............. {Colors.RED}{count}{Colors.RESET}")
                
        self.print_separator()
        
    def execute_test(self):
        """Execute the load test."""
        self.clear_screen()
        self.print_header()
        print(f"Starting test on {Colors.BLUE}{self.config['url']}{Colors.RESET}")
        self.print_separator()
        
        num_threads = self.config['threads']
        duration = self.config['duration']
        
        # Start worker threads
        threads = []
        self.running = True
        
        for i in range(num_threads):
            t = threading.Thread(target=self.worker, args=(i,), daemon=True)
            t.start()
            threads.append(t)
            
        self.statistics.start_time = time.time()
        
        try:
            last_report_time = 0
            
            for second in range(duration):
                current_time = time.time() - self.statistics.start_time
                
                # Calculate requests needed for this second
                target_rps = self.calculate_rps_for_second(second)
                requests_this_second = int(target_rps)
                
                # Queue requests
                for _ in range(requests_this_second):
                    self.request_queue.put(1)
                    
                time.sleep(1)
                
                # Print report every 10 seconds
                if current_time - last_report_time >= 10 or second == 0:
                    self.print_report(int(current_time))
                    last_report_time = current_time
                    
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Test interrupted by user.{Colors.RESET}")
            
        finally:
            self.running = False
            self.statistics.end_time = time.time()
            
            # Wait for queued requests to complete
            time.sleep(2)
            
    def print_final_report(self):
        """Print final test report."""
        self.clear_screen()
        self.print_header()
        print(f"{Colors.BOLD}Final Test Report{Colors.RESET}")
        self.print_separator()
        
        stats = self.statistics.get_statistics()
        if not stats:
            print("No data collected.")
            return
            
        elapsed = self.statistics.end_time - self.statistics.start_time
        
        # Test Summary
        print(f"\n{Colors.BOLD}Test Summary{Colors.RESET}")
        print(f"  Duration.................. {elapsed:.1f} seconds")
        print(f"  Total Requests............ {Colors.BLUE}{stats['total']}{Colors.RESET}")
        print(f"  Throughput................ {stats['total']/elapsed:.2f} requests/sec")
        print(f"  Successful Requests....... {Colors.GREEN}{stats['successful']}{Colors.RESET}")
        print(f"  Failed Requests........... {Colors.RED}{stats['failed']}{Colors.RESET}")
        print(f"  Error Rate................ {Colors.YELLOW}{stats['error_rate']:.2f}%{Colors.RESET}")
        
        # Latency Statistics
        print(f"\n{Colors.BOLD}Latency Statistics (ms){Colors.RESET}")
        print(f"  Minimum.................. {stats['min_latency']:.2f} ms")
        print(f"  Maximum.................. {stats['max_latency']:.2f} ms")
        print(f"  Average.................. {stats['avg_latency']:.2f} ms")
        print(f"  Median (p50)............. {stats['median_latency']:.2f} ms")
        print(f"  95th Percentile (p95).... {stats['p95_latency']:.2f} ms")
        print(f"  99th Percentile (p99).... {stats['p99_latency']:.2f} ms")
        
        # HTTP Status Codes
        if stats['status_codes']:
            print(f"\n{Colors.BOLD}HTTP Status Codes Distribution{Colors.RESET}")
            for code in sorted(stats['status_codes'].keys()):
                count = stats['status_codes'][code]
                percentage = (count / stats['total']) * 100
                color = Colors.GREEN if 200 <= code < 300 else Colors.RED
                print(f"  HTTP {code}................. {color}{count}{Colors.RESET} ({percentage:.1f}%)")
                
        # Errors
        if stats['errors']:
            print(f"\n{Colors.BOLD}Error Summary{Colors.RESET}")
            for error_type, count in stats['errors'].items():
                error_display = error_type.replace('_', ' ').title()
                print(f"  {error_display}.............. {Colors.RED}{count}{Colors.RESET}")
                
        self.print_separator()
        print("\n")
        
    def run_interactive(self):
        """Main interactive loop."""
        while True:
            self.clear_screen()
            self.print_header()
            
            if not self.config:
                print("Welcome to SLAYER Load Testing Tool.")
                print("Please configure your test to begin.\n")
                action = self.prompt(
                    "What would you like to do",
                    options=["Configure New Test", "Exit"]
                )
                
                if action == "Configure New Test":
                    self.configure_test()
                else:
                    print(f"\n{Colors.BLUE}Thank you for using SLAYER. Goodbye.{Colors.RESET}\n")
                    sys.exit(0)
            else:
                action = self.prompt(
                    "What would you like to do",
                    options=[
                        "View Configuration",
                        "Modify Configuration",
                        "Run Test",
                        "Reset Configuration",
                        "Exit"
                    ]
                )
                
                if action == "View Configuration":
                    self.display_configuration()
                    input("Press Enter to continue...")
                    
                elif action == "Modify Configuration":
                    self.configure_test()
                    
                elif action == "Run Test":
                    confirm = self.prompt(
                        "Are you sure you want to start the test",
                        options=["Yes", "No"]
                    )
                    if confirm == "Yes":
                        self.execute_test()
                        self.print_final_report()
                        input("Press Enter to continue...")
                        
                elif action == "Reset Configuration":
                    self.config = {}
                    self.statistics = Statistics()
                    
                elif action == "Exit":
                    print(f"\n{Colors.BLUE}Thank you for using SLAYER. Goodbye.{Colors.RESET}\n")
                    sys.exit(0)


def main():
    """Entry point."""
    tester = LoadTester()
    
    try:
        tester.run_interactive()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Application terminated by user.{Colors.RESET}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}An error occurred: {e}{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

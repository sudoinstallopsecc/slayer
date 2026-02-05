#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLAYER - Advanced HTTP Load Testing Tool
"""

import os
import sys
import time
import random
import threading
import requests
import json
from datetime import datetime
from contextlib import contextmanager

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

class ProgressBar:
    def __init__(self, total=100, width=40):
        self.total = total
        self.width = width
        self.current = 0
        
    def update(self, value):
        self.current = value
        
    def display(self, rps=0, avg_time=0, errors=0):
        if self.total == 0:
            percentage = 0
        else:
            percentage = min(100, (self.current / self.total) * 100)
        
        filled = int(self.width * percentage / 100)
        bar = '█' * filled + '▓' * (self.width - filled)
        
        print(f'\r{Colors.CYAN}[{bar}] {percentage:5.1f}% '
              f'{Colors.WHITE}({self.current}/{self.total}) '
              f'{Colors.GREEN}RPS: {rps:6.1f} '
              f'{Colors.YELLOW}Avg: {avg_time:5.0f}ms '
              f'{Colors.RED}Errors: {errors:4d}{Colors.RESET}', end='', flush=True)

class HTTPLoader:
    def __init__(self):
        self.target_url = ""
        self.method = "GET"
        self.delay = 0.1
        self.threads = 10
        self.max_requests = None
        self.max_time = None
        self.data = None
        self.headers = {}
        
        # Runtime stats
        self.running = False
        self.requests_count = 0
        self.success_count = 0
        self.error_count = 0
        self.start_time = None
        self.response_times = []
        self.lock = threading.Lock()
        
        # Session
        self.session = self._create_session()
        
    def _create_session(self):
        session = requests.Session() 
        session.headers.update({
            'User-Agent': 'SLAYER-LoadTester/1.0',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        })
        return session

    def banner(self):
        os.system('clear' if os.name == 'posix' else 'cls')
        print(f"""
{Colors.BOLD}{Colors.WHITE}
╔══════════════════════════════════════╗
║              SLAYER                  ║
╚══════════════════════════════════════╝{Colors.RESET}


""")
        print(f"""
{Colors.YELLOW}Current Configuration:{Colors.RESET}
  Target:     {Colors.WHITE}{self.target_url or 'not set'}{Colors.RESET}
  Method:     {Colors.WHITE}{self.method}{Colors.RESET}
  Threads:    {Colors.WHITE}{self.threads}{Colors.RESET}
  Delay:      {Colors.WHITE}{self.delay}s{Colors.RESET}
""")

    def get_random_user_agent(self):
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        ]
        return random.choice(agents)

    def worker_thread(self, thread_id):
        while self.running:
            try:
                start_time = time.time()
                
                # Randomize headers
                headers = self.headers.copy()
                headers['User-Agent'] = self.get_random_user_agent()
                
                # Make request
                response = self.session.request(
                    self.method,
                    self.target_url,
                    headers=headers,
                    data=self.data,
                    timeout=10,
                    allow_redirects=True
                )
                
                response_time = (time.time() - start_time) * 1000
                
                with self.lock:
                    self.requests_count += 1
                    self.response_times.append(response_time)
                    
                    if 200 <= response.status_code < 400:
                        self.success_count += 1
                    else:
                        self.error_count += 1
                        
                    # Check limits
                    if self.max_requests and self.requests_count >= self.max_requests:
                        self.running = False
                        break
                        
                    if self.max_time and (time.time() - self.start_time) >= self.max_time:
                        self.running = False
                        break
                        
            except Exception as e:
                with self.lock:
                    self.error_count += 1
                    self.requests_count += 1
                    
            time.sleep(self.delay)

    def run_test(self, config):
        if not config['target_url']:
            print(f"{Colors.RED}Error: Target URL required{Colors.RESET}")
            return
            
        # Setup
        target = config['target_url']
        if not target.startswith(('http://', 'https://')):
            target = 'http://' + target
            
        self.target_url = target
        self.method = config.get('method', 'GET')
        self.threads = config.get('threads', 10)
        self.delay = config.get('delay', 0.1)
        self.max_requests = config.get('max_requests')
        self.max_time = config.get('max_time')
        self.data = config.get('data')
        
        # Reset stats
        self.requests_count = 0
        self.success_count = 0
        self.error_count = 0
        self.response_times = []
        self.running = True
        self.start_time = time.time()
        
        # Display test info
        print(f"{Colors.CYAN}Starting benchmark...{Colors.RESET}")
        print(f"Target: {Colors.WHITE}{target}{Colors.RESET}")
        print(f"Method: {Colors.WHITE}{self.method}{Colors.RESET} | "
              f"Threads: {Colors.WHITE}{self.threads}{Colors.RESET} | "
              f"Delay: {Colors.WHITE}{self.delay}s{Colors.RESET}")
        
        if self.max_requests:
            print(f"Requests: {Colors.WHITE}{self.max_requests}{Colors.RESET}")
        if self.max_time:
            print(f"Duration: {Colors.WHITE}{self.max_time}s{Colors.RESET}")
            
        print()
        
        # Start threads
        threads = []
        for i in range(self.threads):
            t = threading.Thread(target=self.worker_thread, args=(i,))
            t.daemon = True
            threads.append(t)
            t.start()
            
        # Monitor progress
        progress = ProgressBar(self.max_requests or 1000)
        last_count = 0
        last_time = time.time()
        
        try:
            while self.running:
                time.sleep(0.5)
                
                current_time = time.time()
                elapsed = current_time - self.start_time
                
                # Calculate RPS
                rps = 0
                if elapsed > 0:
                    # Real-time RPS (last 0.5s)
                    new_requests = self.requests_count - last_count
                    time_diff = current_time - last_time
                    if time_diff > 0:
                        rps = new_requests / time_diff
                    last_count = self.requests_count
                    last_time = current_time
                
                # Calculate average response time
                avg_time = 0
                if self.response_times:
                    with self.lock:
                        avg_time = sum(self.response_times) / len(self.response_times)
                
                # Update progress
                progress.total = self.max_requests or max(1000, self.requests_count + 100)
                progress.update(self.requests_count)
                progress.display(rps, avg_time, self.error_count)
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
            
        finally:
            self.running = False
            print(f"\n{Colors.CYAN}Stopping threads...{Colors.RESET}")
            
            # Wait for threads to finish
            for t in threads:
                t.join(timeout=1)
                
            self.display_results()

    def display_results(self):
        elapsed = time.time() - self.start_time
        
        print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
        print("=" * 50)
        
        # Basic stats
        success_rate = (self.success_count / self.requests_count * 100) if self.requests_count > 0 else 0
        rps = self.requests_count / elapsed if elapsed > 0 else 0
        
        print(f"Requests:      {Colors.WHITE}{self.requests_count:8d}{Colors.RESET}")
        print(f"Duration:      {Colors.WHITE}{elapsed:8.2f}s{Colors.RESET}")
        print(f"Rate:          {Colors.WHITE}{rps:8.2f} req/s{Colors.RESET}")
        print(f"Success:       {Colors.GREEN}{self.success_count:8d}{Colors.RESET} ({success_rate:5.1f}%)")
        print(f"Errors:        {Colors.RED}{self.error_count:8d}{Colors.RESET}")
        
        # Response time stats
        if self.response_times:
            times = sorted(self.response_times)
            count = len(times)
            
            avg = sum(times) / count
            median = times[count // 2]
            p95 = times[int(count * 0.95)] if count > 20 else times[-1]
            p99 = times[int(count * 0.99)] if count > 100 else times[-1]
            
            print(f"\n{Colors.BOLD}Response Times (ms):{Colors.RESET}")
            print(f"Average:       {Colors.WHITE}{avg:8.0f}{Colors.RESET}")
            print(f"Median:        {Colors.WHITE}{median:8.0f}{Colors.RESET}")
            print(f"95th %ile:     {Colors.WHITE}{p95:8.0f}{Colors.RESET}")
            print(f"99th %ile:     {Colors.WHITE}{p99:8.0f}{Colors.RESET}")
        
        print()

def main():
    slayer = HTTPLoader()
    config = {
        'target_url': '',
        'method': 'GET',
        'threads': 10,
        'delay': 0.1,
        'max_requests': None,
        'max_time': None,
        'data': None
    }
    
    slayer.banner()
    
    while True:
        try:
            command = input(f"{Colors.BOLD}slayer{Colors.RESET}> ").strip()
            
            if not command:
                continue
                
            parts = command.split()
            cmd = parts[0].lower()
            
            if cmd in ['exit', 'quit']:
                print(f"{Colors.CYAN}Goodbye!{Colors.RESET}")
                break
                
            elif cmd == 'help':
                print(f"""
{Colors.BOLD}Commands:{Colors.RESET}
  {Colors.GREEN}target <url>{Colors.RESET}           - Set target URL  
  {Colors.GREEN}method <GET|POST|PUT|DELETE>{Colors.RESET} - Set HTTP method
  {Colors.GREEN}threads <num>{Colors.RESET}          - Set concurrent threads
  {Colors.GREEN}delay <seconds>{Colors.RESET}        - Set request delay
  {Colors.GREEN}data <text>{Colors.RESET}            - Set request body
  
  {Colors.GREEN}run{Colors.RESET}                    - Start test
  {Colors.GREEN}run -n <count>{Colors.RESET}         - Run specific number of requests
  {Colors.GREEN}run -t <time>s{Colors.RESET}         - Run for specific time
  
  {Colors.GREEN}status{Colors.RESET}                 - Show config
  {Colors.GREEN}help{Colors.RESET}                   - Show this help
  {Colors.GREEN}clear{Colors.RESET}                  - Clear screen
  {Colors.GREEN}exit{Colors.RESET}                   - Exit

{Colors.BOLD}Examples:{Colors.RESET}
  {Colors.CYAN}target https://httpbin.org/get{Colors.RESET}
  {Colors.CYAN}threads 50{Colors.RESET}
  {Colors.CYAN}run -n 1000{Colors.RESET}
""")
                
            elif cmd == 'clear':
                slayer.banner()
                
            elif cmd == 'status':
                slayer.display_config()
                
            elif cmd == 'target':
                if len(parts) > 1:
                    config['target_url'] = parts[1]
                    print(f"{Colors.GREEN}Target set: {parts[1]}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}Usage: target <url>{Colors.RESET}")
                    
            elif cmd == 'method':
                if len(parts) > 1:
                    method = parts[1].upper()
                    if method in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH']:
                        config['method'] = method
                        print(f"{Colors.GREEN}Method set: {method}{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}Invalid method{Colors.RESET}")
                else:
                    print(f"{Colors.RED}Usage: method <GET|POST|PUT|DELETE>{Colors.RESET}")
                    
            elif cmd == 'threads':
                if len(parts) > 1:
                    try:
                        threads = int(parts[1])
                        if threads > 0:
                            config['threads'] = threads
                            print(f"{Colors.GREEN}Threads set: {threads}{Colors.RESET}")
                        else:
                            print(f"{Colors.RED}Threads must be > 0{Colors.RESET}")
                    except ValueError:
                        print(f"{Colors.RED}Threads must be a number{Colors.RESET}")
                else:
                    print(f"{Colors.RED}Usage: threads <number>{Colors.RESET}")
                    
            elif cmd == 'delay':
                if len(parts) > 1:
                    try:
                        delay = float(parts[1])
                        if delay >= 0:
                            config['delay'] = delay
                            print(f"{Colors.GREEN}Delay set: {delay}s{Colors.RESET}")
                        else:
                            print(f"{Colors.RED}Delay must be >= 0{Colors.RESET}")
                    except ValueError:
                        print(f"{Colors.RED}Delay must be a number{Colors.RESET}")
                else:
                    print(f"{Colors.RED}Usage: delay <seconds>{Colors.RESET}")
                    
            elif cmd == 'data':
                if len(parts) > 1:
                    config['data'] = ' '.join(parts[1:])
                    print(f"{Colors.GREEN}Data set{Colors.RESET}")
                else:
                    config['data'] = None
                    print(f"{Colors.GREEN}Data cleared{Colors.RESET}")
                    
            elif cmd == 'run':
                # Parse run options
                run_config = config.copy()
                
                i = 1
                while i < len(parts):
                    if parts[i] == '-n' and i + 1 < len(parts):
                        try:
                            run_config['max_requests'] = int(parts[i + 1])
                            i += 2
                        except ValueError:
                            print(f"{Colors.RED}Invalid request count{Colors.RESET}")
                            break
                    elif parts[i] == '-t' and i + 1 < len(parts):
                        try:
                            time_str = parts[i + 1]
                            if time_str.endswith('s'):
                                run_config['max_time'] = int(time_str[:-1])
                            else:
                                run_config['max_time'] = int(time_str)
                            i += 2
                        except ValueError:
                            print(f"{Colors.RED}Invalid time format{Colors.RESET}")
                            break
                    else:
                        i += 1
                
                slayer.run_test(run_config)
                
            else:
                print(f"{Colors.RED}Unknown command: {cmd}{Colors.RESET}")
                print(f"Type '{Colors.GREEN}help{Colors.RESET}' for available commands")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Command interrupted{Colors.RESET}")
        except EOFError:
            print(f"\n{Colors.CYAN}Goodbye!{Colors.RESET}")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")

if __name__ == "__main__":
    main()
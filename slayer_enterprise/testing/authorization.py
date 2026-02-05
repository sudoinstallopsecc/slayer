"""
Target Authorization System for SLAYER Enterprise
================================================

Critical safety component that ensures load testing is only performed
against authorized targets with proper safeguards and verification.

This module implements multiple layers of authorization:
1. Explicit target authorization checks
2. Domain ownership verification
3. Rate limiting compliance
4. Safety warnings and confirmations
"""

import asyncio
import dns.resolver
import hashlib
import os
import urllib.parse
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import requests
import socket
import ssl
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AuthorizationConfig:
    """Configuration for target authorization system."""
    
    # Ownership verification methods
    enable_dns_verification: bool = True
    enable_file_verification: bool = True 
    enable_header_verification: bool = True
    
    # Safety limits
    max_rps_without_verification: int = 10
    max_concurrent_without_verification: int = 50
    require_explicit_confirmation: bool = True
    
    # Verification timeouts
    dns_timeout: float = 5.0
    file_verification_timeout: float = 10.0
    
    # Allowed verification file paths
    verification_paths: List[str] = field(default_factory=lambda: [
        '/.well-known/slayer-loadtest-authorization.txt',
        '/robots.txt',
        '/.well-known/security.txt'
    ])
    
    # Warning thresholds
    high_intensity_rps: int = 100
    high_intensity_duration: int = 300  # 5 minutes


class VerificationMethod:
    """Base class for authorization verification methods."""
    
    async def verify(self, target_url: str, verification_token: str) -> Tuple[bool, str]:
        """
        Verify authorization for target.
        
        Returns:
            Tuple of (success, reason/error_message)
        """
        raise NotImplementedError


class DNSVerificationMethod(VerificationMethod):
    """Verify authorization via DNS TXT records."""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
    
    async def verify(self, target_url: str, verification_token: str) -> Tuple[bool, str]:
        """
        Check for authorization via DNS TXT record.
        
        Looks for TXT record: slayer-loadtest-auth=<token>
        """
        try:
            parsed = urllib.parse.urlparse(target_url)
            domain = parsed.netloc.split(':')[0]  # Remove port if present
            
            # Query DNS TXT records
            try:
                answers = dns.resolver.query(domain, 'TXT')
                for rdata in answers:
                    txt_value = str(rdata).strip('"')
                    if txt_value.startswith('slayer-loadtest-auth='):
                        recorded_token = txt_value.split('=', 1)[1]
                        if recorded_token == verification_token:
                            return True, f"DNS verification successful for {domain}"
            except dns.resolver.NXDOMAIN:
                return False, f"Domain {domain} not found"
            except Exception as e:
                return False, f"DNS query failed: {str(e)}"
            
            return False, f"No valid authorization TXT record found for {domain}"
            
        except Exception as e:
            return False, f"DNS verification error: {str(e)}"


class FileVerificationMethod(VerificationMethod):
    """Verify authorization via file on target server."""
    
    def __init__(self, paths: List[str], timeout: float = 10.0):
        self.paths = paths
        self.timeout = timeout
    
    async def verify(self, target_url: str, verification_token: str) -> Tuple[bool, str]:
        """
        Check for authorization file on target server.
        
        Looks for verification token in specified file paths.
        """
        try:
            parsed = urllib.parse.urlparse(target_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            for path in self.paths:
                try:
                    verification_url = f"{base_url}{path}"
                    response = requests.get(
                        verification_url, 
                        timeout=self.timeout,
                        headers={'User-Agent': 'SLAYER-LoadTest-Verification/1.0'}
                    )
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Check for exact token match
                        if verification_token in content:
                            return True, f"File verification successful at {verification_url}"
                        
                        # Check for slayer-loadtest-auth directive
                        for line in content.split('\n'):
                            line = line.strip()
                            if line.startswith('slayer-loadtest-auth:'):
                                recorded_token = line.split(':', 1)[1].strip()
                                if recorded_token == verification_token:
                                    return True, f"File verification successful at {verification_url}"
                    
                except requests.RequestException:
                    continue  # Try next path
            
            return False, f"No valid authorization file found at any of: {self.paths}"
            
        except Exception as e:
            return False, f"File verification error: {str(e)}"


class HeaderVerificationMethod(VerificationMethod):
    """Verify authorization via HTTP response headers."""
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
    
    async def verify(self, target_url: str, verification_token: str) -> Tuple[bool, str]:
        """
        Check for authorization via HTTP response headers.
        
        Looks for header: X-SLAYER-LoadTest-Auth: <token>
        """
        try:
            response = requests.head(
                target_url,
                timeout=self.timeout,
                headers={'User-Agent': 'SLAYER-LoadTest-Verification/1.0'}
            )
            
            auth_header = response.headers.get('X-SLAYER-LoadTest-Auth')
            if auth_header == verification_token:
                return True, "Header verification successful"
            
            return False, "No valid authorization header found"
            
        except Exception as e:
            return False, f"Header verification error: {str(e)}"


class TargetAuthorization:
    """
    Comprehensive target authorization system for load testing.
    
    Implements multiple verification methods and safety checks to ensure
    that load tests are only performed against authorized targets.
    """
    
    def __init__(self, config: AuthorizationConfig):
        self.config = config
        self.verification_methods: List[VerificationMethod] = []
        
        # Initialize verification methods
        if config.enable_dns_verification:
            self.verification_methods.append(
                DNSVerificationMethod(config.dns_timeout)
            )
        
        if config.enable_file_verification:
            self.verification_methods.append(
                FileVerificationMethod(config.verification_paths, config.file_verification_timeout)
            )
        
        if config.enable_header_verification:
            self.verification_methods.append(
                HeaderVerificationMethod()
            )
        
        # Authorization cache
        self._auth_cache: Dict[str, Tuple[bool, datetime]] = {}
        
        logger.info("Target authorization system initialized")
    
    def generate_verification_token(self, target_url: str) -> str:
        """
        Generate a unique verification token for target URL.
        
        Args:
            target_url: Target URL for load testing
            
        Returns:
            Unique verification token
        """
        # Create deterministic token based on URL and current date
        url_hash = hashlib.sha256(target_url.encode()).hexdigest()[:16]
        date_hash = hashlib.sha256(datetime.now().strftime('%Y-%m-%d').encode()).hexdigest()[:8]
        return f"slayer-{url_hash}-{date_hash}"
    
    async def check_authorization(
        self, 
        target_url: str, 
        verification_token: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, any]]:
        """
        Comprehensive authorization check for target URL.
        
        Args:
            target_url: URL to verify authorization for
            verification_token: Optional pre-generated token
        
        Returns:
            Tuple of (authorized, reason, details)
        """
        try:
            # Normalize URL
            if not target_url.startswith(('http://', 'https://')):
                target_url = 'https://' + target_url
            
            parsed = urllib.parse.urlparse(target_url)
            domain = parsed.netloc.split(':')[0]
            
            # Check cache first
            cache_key = f"{domain}:{verification_token or 'anonymous'}"
            if cache_key in self._auth_cache:
                cached_result, cache_time = self._auth_cache[cache_key]
                if datetime.now() - cache_time < timedelta(hours=1):  # Cache valid for 1 hour
                    return cached_result, "Cached authorization result", {}
            
            # Generate verification token if not provided
            if verification_token is None:
                verification_token = self.generate_verification_token(target_url)
            
            details = {
                'target_url': target_url,
                'domain': domain,
                'verification_token': verification_token,
                'verification_methods_attempted': [],
                'verification_results': {}
            }
            
            # Check if target is localhost/private IP (auto-authorized)
            if self._is_local_target(domain):
                result = True, "Local target auto-authorized"
                self._auth_cache[cache_key] = (result, datetime.now())
                return result[0], result[1], details
            
            # Try all verification methods
            verification_successful = False
            verification_details = []
            
            for method in self.verification_methods:
                method_name = method.__class__.__name__
                details['verification_methods_attempted'].append(method_name)
                
                try:
                    success, reason = await method.verify(target_url, verification_token)
                    details['verification_results'][method_name] = {
                        'success': success,
                        'reason': reason
                    }
                    
                    if success:
                        verification_successful = True
                        verification_details.append(f"{method_name}: {reason}")
                        break
                        
                except Exception as e:
                    details['verification_results'][method_name] = {
                        'success': False,
                        'reason': f"Error: {str(e)}"
                    }
                    logger.warning(f"Verification method {method_name} failed: {e}")
            
            if verification_successful:
                result = True, f"Authorization verified: {'; '.join(verification_details)}"
                self._auth_cache[cache_key] = (result, datetime.now())
                return result[0], result[1], details
            else:
                result = False, "No verification method succeeded"
                return result[0], result[1], details
            
        except Exception as e:
            logger.error(f"Authorization check failed: {e}")
            return False, f"Authorization check error: {str(e)}", {'error': str(e)}
    
    def _is_local_target(self, domain: str) -> bool:
        """Check if target is localhost or private IP address."""
        local_indicators = [
            'localhost',
            '127.0.0.1',
            '::1',
            '0.0.0.0'
        ]
        
        if domain in local_indicators:
            return True
        
        try:
            # Check if it's a private IP
            ip = socket.gethostbyname(domain)
            return (
                ip.startswith('10.') or
                ip.startswith('192.168.') or
                ip.startswith('172.') and int(ip.split('.')[1]) in range(16, 32) or
                ip == '127.0.0.1'
            )
        except:
            return False
    
    def get_safety_warnings(
        self, 
        target_url: str, 
        planned_rps: int, 
        duration_seconds: int,
        concurrent_connections: int
    ) -> List[str]:
        """
        Generate safety warnings based on test parameters.
        
        Args:
            target_url: Target URL
            planned_rps: Planned requests per second
            duration_seconds: Test duration in seconds
            concurrent_connections: Number of concurrent connections
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        # High intensity warnings
        if planned_rps > self.config.high_intensity_rps:
            warnings.append(
                f"⚠️  HIGH INTENSITY: {planned_rps} RPS exceeds recommended threshold "
                f"of {self.config.high_intensity_rps} RPS"
            )
        
        if duration_seconds > self.config.high_intensity_duration:
            warnings.append(
                f"⚠️  EXTENDED DURATION: {duration_seconds}s test exceeds "
                f"recommended duration of {self.config.high_intensity_duration}s"
            )
        
        if concurrent_connections > self.config.max_concurrent_without_verification:
            warnings.append(
                f"⚠️  HIGH CONCURRENCY: {concurrent_connections} concurrent connections "
                f"may overwhelm target server"
            )
        
        # Calculate total requests
        total_requests = planned_rps * duration_seconds
        if total_requests > 100000:  # 100k requests
            warnings.append(
                f"⚠️  LARGE VOLUME: Test will generate approximately {total_requests:,} total requests"
            )
        
        # Parse target for additional warnings
        parsed = urllib.parse.urlparse(target_url)
        if parsed.scheme == 'https':
            warnings.append(
                "ℹ️  Target uses HTTPS - SSL handshake overhead will impact performance"
            )
        
        return warnings
    
    def print_authorization_instructions(self, target_url: str, verification_token: str):
        """
        Print detailed instructions for authorizing the target.
        
        Args:
            target_url: Target URL to authorize
            verification_token: Generated verification token
        """
        parsed = urllib.parse.urlparse(target_url)
        domain = parsed.netloc.split(':')[0]
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        print("\n" + "="*80)
        print("🔐 TARGET AUTHORIZATION REQUIRED")
        print("="*80)
        print(f"\nTo authorize load testing against: {target_url}")
        print(f"Verification token: {verification_token}\n")
        
        print("📋 AUTHORIZATION METHODS (choose ONE):\n")
        
        if self.config.enable_dns_verification:
            print("1️⃣  DNS TXT Record Method:")
            print(f"   Add a TXT record to domain '{domain}' with value:")
            print(f"   slayer-loadtest-auth={verification_token}\n")
        
        if self.config.enable_file_verification:
            print("2️⃣  File Verification Method:")
            print("   Create a file at one of these locations on your server:")
            for path in self.config.verification_paths:
                print(f"   {base_url}{path}")
            print(f"   \n   File content should include: {verification_token}")
            print("   OR add line: slayer-loadtest-auth: " + verification_token + "\n")
        
        if self.config.enable_header_verification:
            print("3️⃣  HTTP Header Method:")
            print("   Configure your server to return this header:")
            print(f"   X-SLAYER-LoadTest-Auth: {verification_token}\n")
        
        print("⚠️  IMPORTANT SAFETY NOTES:")
        print("   • Only authorize testing against servers you own or have explicit permission to test")
        print("   • Verify your server can handle the planned load before testing")
        print("   • Monitor your server during testing and stop if issues occur")
        print("   • Authorization tokens expire after 24 hours for security")
        print("\n" + "="*80 + "\n")
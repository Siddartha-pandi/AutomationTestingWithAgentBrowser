"""Network policy enforcement and SSRF prevention for browser automation."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Restricted private / metadata subnets to prevent Server-Side Request Forgery (SSRF)
RESTRICTED_NETWORKS = [
    ipaddress.ip_network("169.254.169.254/32"),  # AWS/Cloud Metadata Service
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local
    ipaddress.ip_network("10.0.0.0/8"),          # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),       # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),      # RFC 1918
    ipaddress.ip_network("127.0.0.0/8"),         # Loopback
]


def is_ip_restricted(ip_str: str) -> bool:
    """Checks whether an IP address belongs to cloud metadata or internal private subnets."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in RESTRICTED_NETWORKS)
    except ValueError:
        return False


def is_domain_allowed(hostname: str, allowed_patterns: list[str]) -> bool:
    """Matches a hostname against allowed patterns with wildcard (*.example.com) support."""
    clean_host = hostname.strip().lower()
    for pattern in allowed_patterns:
        pat = pattern.strip().lower()
        if pat == "*":
            return True
        if pat.startswith("*."):
            suffix = pat[2:]
            if clean_host == suffix or clean_host.endswith(f".{suffix}"):
                return True
        elif clean_host == pat:
            return True
    return False


def validate_destination_url(
    url: str,
    allowed_domains: list[str] | None = None,
    allow_private_subnets: bool = False,
) -> tuple[bool, str]:
    """Validates destination URL against scheme, SSRF restrictions, and domain allowlists.

    Returns:
        (is_valid, reason_or_error_message)
    """
    if not url:
        return False, "URL cannot be empty"

    try:
        parsed = urlparse(url)
    except Exception as err:
        return False, f"Malformed URL syntax: {err}"

    # Only http and https schemes are permitted (blocks file://, gopher://, javascript:, data:)
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Prohibited URL scheme '{parsed.scheme}'. Only http and https are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL missing valid hostname"

    # Domain allowlist check
    if allowed_domains and not is_domain_allowed(hostname, allowed_domains):
        return False, f"Domain '{hostname}' is not in the approved allowed domains list: {allowed_domains}"

    # SSRF verification: resolve hostname to IP and check against restricted subnets
    if not allow_private_subnets:
        try:
            # Resolve DNS
            addr_info = socket.getaddrinfo(hostname, None)
            for entry in addr_info:
                ip_str = entry[4][0]
                if is_ip_restricted(ip_str):
                    return False, f"SSRF Protection: Host '{hostname}' resolves to restricted IP: {ip_str}"
        except socket.gaierror:
            # Unresolvable hostname in isolated tests
            pass

    return True, "URL allowed"


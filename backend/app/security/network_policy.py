"""Network policy enforcement and SSRF prevention for browser automation."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

# Restricted private / metadata subnets to prevent Server-Side Request Forgery (SSRF)
CLOUD_METADATA_NETWORKS = [
    ipaddress.ip_network("169.254.169.254/32"),  # AWS/GCP/Azure Metadata Service
    ipaddress.ip_network("fd00:ec2::254/128"),    # AWS IPv6 IMDS
]

RESTRICTED_NETWORKS = [
    ipaddress.ip_network("169.254.169.254/32"),  # AWS/Cloud Metadata Service
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local
    ipaddress.ip_network("10.0.0.0/8"),          # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),       # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),      # RFC 1918
    ipaddress.ip_network("127.0.0.0/8"),         # Loopback
    ipaddress.ip_network("0.0.0.0/8"),           # Current network
    ipaddress.ip_network("100.64.0.0/10"),       # Shared address space / CGNAT
    ipaddress.ip_network("198.18.0.0/15"),       # Benchmark testing
    ipaddress.ip_network("::1/128"),             # IPv6 Loopback
    ipaddress.ip_network("fe80::/10"),           # IPv6 Link-local
    ipaddress.ip_network("fc00::/7"),            # IPv6 Unique local
    ipaddress.ip_network("::/128"),              # IPv6 Unspecified
    ipaddress.ip_network("::ffff:127.0.0.0/104"),# IPv4-mapped loopback
]

METADATA_HOSTNAMES = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.goog",
    "instance-data",
}


def is_ip_restricted(
    ip_str: str,
    allow_private_subnets: bool = False,
    allow_loopback: bool = False,
) -> bool:
    """Checks whether an IP address belongs to cloud metadata or internal private subnets."""
    try:
        addr = ipaddress.ip_address(ip_str.strip("[]"))
    except ValueError:
        return False

    # Cloud metadata is strictly forbidden in all environments
    if any(addr in net for net in CLOUD_METADATA_NETWORKS):
        return True

    # Check loopback
    if addr.is_loopback:
        return not allow_loopback

    # Check link-local
    if addr.is_link_local:
        return True

    # Check private
    if addr.is_private:
        return not allow_private_subnets

    # Check reserved / unspecified / multicast
    if addr.is_reserved or addr.is_unspecified or addr.is_multicast:
        return True

    return any(addr in net for net in RESTRICTED_NETWORKS)


def is_domain_allowed(hostname: str, allowed_patterns: list[str]) -> bool:
    """Matches a hostname against allowed patterns with wildcard (*.example.com) support."""
    clean_host = hostname.strip().lower()
    for pattern in allowed_patterns:
        pat = pattern.strip().lower()
        if pat in ("*", "*.*", "all"):
            return True
        if pat.startswith("*."):
            suffix = pat[2:]
            if clean_host == suffix or clean_host.endswith(f".{suffix}"):
                return True
        elif clean_host == pat:
            return True
    return False


def is_local_dev_allowed() -> bool:
    """Determines whether local development private / loopback access is explicitly enabled."""
    env = os.getenv("ENVIRONMENT", "").lower()
    allow_local = os.getenv("ALLOW_LOCAL_DEV_NETWORKS", "").lower() in ("true", "1", "yes")
    return env == "development" and allow_local


def validate_destination_url(
    url: str,
    allowed_domains: list[str] | None = None,
    allow_private_subnets: bool = False,
    allow_loopback: bool = False,
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
        return False, f"Prohibited URL scheme '{parsed.scheme}'. Only http and https schemes are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL missing valid hostname"

    lower_host = hostname.strip().lower()

    # Block known cloud metadata hostnames directly
    if lower_host in METADATA_HOSTNAMES:
        return False, f"SSRF Protection: Cloud metadata host '{lower_host}' is strictly prohibited."

    # Effective dev flags
    dev_mode = is_local_dev_allowed()
    effective_allow_private = allow_private_subnets or dev_mode
    effective_allow_loopback = allow_loopback or dev_mode

    # Check loopback hostnames
    if lower_host in ("localhost", "localhost.localdomain") and not effective_allow_loopback:
        return False, f"SSRF Protection: Loopback host '{hostname}' is not permitted in production."

    # Domain allowlist check
    if allowed_domains and not is_domain_allowed(hostname, allowed_domains):
        return False, f"Domain '{hostname}' is not in approved allowed domains list (not in the approved allowed domains): {allowed_domains}"

    # Check direct IP literals
    try:
        ip_obj = ipaddress.ip_address(lower_host.strip("[]"))
        if is_ip_restricted(str(ip_obj), allow_private_subnets=effective_allow_private, allow_loopback=effective_allow_loopback):
            return False, f"SSRF Protection: Direct IP destination '{hostname}' is in restricted range."
    except ValueError:
        pass

    # SSRF verification: resolve hostname to IP and check against restricted subnets
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            if is_ip_restricted(ip_str, allow_private_subnets=effective_allow_private, allow_loopback=effective_allow_loopback):
                return False, f"SSRF Protection: Host '{hostname}' resolves to restricted IP: {ip_str}"
    except socket.gaierror:
        # Unresolvable hostname in isolated tests
        pass

    return True, "URL allowed"


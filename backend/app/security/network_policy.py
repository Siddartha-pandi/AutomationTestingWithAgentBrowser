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
    ipaddress.ip_network("169.254.0.0/16"),      # IPv4 Link-local
    ipaddress.ip_network("fe80::/10"),           # IPv6 Link-local
]

RESTRICTED_NETWORKS = [
    ipaddress.ip_network("169.254.169.254/32"),  # AWS/Cloud Metadata Service
    ipaddress.ip_network("fd00:ec2::254/128"),    # AWS IPv6 IMDS
    ipaddress.ip_network("169.254.0.0/16"),      # IPv4 Link-local
    ipaddress.ip_network("10.0.0.0/8"),          # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),       # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),      # RFC 1918
    ipaddress.ip_network("127.0.0.0/8"),         # Loopback
    ipaddress.ip_network("0.0.0.0/8"),           # Current network
    ipaddress.ip_network("100.64.0.0/10"),       # Shared address space / CGNAT
    ipaddress.ip_network("198.18.0.0/15"),       # Benchmark testing
    ipaddress.ip_network("::1/128"),             # IPv6 Loopback
    ipaddress.ip_network("fe80::/10"),           # IPv6 Link-local
    ipaddress.ip_network("fc00::/7"),            # IPv6 Unique local (ULA)
    ipaddress.ip_network("::/128"),              # IPv6 Unspecified
    ipaddress.ip_network("::ffff:0:0/96"),       # IPv4-mapped IPv6
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
    clean_ip = ip_str.strip().strip("[]")
    try:
        addr = ipaddress.ip_address(clean_ip)
    except ValueError:
        # Check if it's integer / decimal IP representation
        try:
            if clean_ip.isdigit():
                addr = ipaddress.ip_address(int(clean_ip))
            else:
                return True  # Fail closed on malformed IP
        except ValueError:
            return True

    # If IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1 or ::ffff:169.254.169.254), map to underlying IPv4
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped

    # Cloud metadata is strictly forbidden in all environments
    if any(addr in net for net in CLOUD_METADATA_NETWORKS):
        return True

    # Check loopback
    if addr.is_loopback:
        return not allow_loopback

    # Check link-local
    if addr.is_link_local:
        return True

    # Check private (RFC 1918 / ULA)
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
        # Unrestricted wildcards are only permitted in local dev mode
        if pat in ("*", "*.*", "all"):
            if is_local_dev_allowed():
                return True
            continue
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
    fail_closed_dns: bool | None = None,
) -> tuple[bool, str]:
    """Validates destination URL against scheme, SSRF restrictions, and domain allowlists.

    Returns:
        (is_valid, reason_or_error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty"

    # Reject control characters or null bytes
    if any(ord(c) < 32 or ord(c) == 127 for c in url):
        return False, "SSRF Protection: Malformed URL containing invalid control characters."

    try:
        parsed = urlparse(url.strip())
    except Exception as err:
        return False, f"Malformed URL syntax: {err}"

    # Only http and https schemes are permitted
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Prohibited URL scheme '{parsed.scheme}'. Only http and https schemes are permitted."

    # Reject userinfo / credentials (@) in URL (RFC 3986 parser evasion)
    if parsed.username or parsed.password or "@" in (parsed.netloc.split(":")[0]):
        return False, "SSRF Protection: URLs containing credentials or userinfo (@) are prohibited."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL missing valid hostname"

    lower_host = hostname.strip().lower()

    # Block cloud metadata hostnames directly
    if lower_host in METADATA_HOSTNAMES or lower_host.endswith(".google.internal"):
        return False, f"SSRF Protection: Cloud metadata host '{lower_host}' is strictly prohibited."

    # Effective dev flags
    dev_mode = is_local_dev_allowed()
    effective_allow_private = allow_private_subnets or dev_mode
    effective_allow_loopback = allow_loopback or dev_mode
    effective_fail_closed_dns = (not dev_mode) if fail_closed_dns is None else fail_closed_dns

    # Check loopback hostnames
    if lower_host in ("localhost", "localhost.localdomain") and not effective_allow_loopback:
        return False, f"SSRF Protection: Loopback host '{hostname}' is not permitted in production."

    # Enforce non-empty allowlist in production
    if not dev_mode:
        if not allowed_domains:
            return False, "SSRF Protection: Empty domain allowlist is prohibited in production."

    # Domain allowlist check
    if allowed_domains and not is_domain_allowed(hostname, allowed_domains):
        return False, f"Domain '{hostname}' is not in approved allowed domains list: {allowed_domains}"

    # Check direct IP literals (including decimal / hex / IPv6)
    try:
        clean_ip = lower_host.strip("[]")
        # Handle integer IP literal
        if clean_ip.isdigit():
            clean_ip = str(ipaddress.ip_address(int(clean_ip)))
        ip_obj = ipaddress.ip_address(clean_ip)
        if is_ip_restricted(str(ip_obj), allow_private_subnets=effective_allow_private, allow_loopback=effective_allow_loopback):
            return False, f"SSRF Protection: Direct IP destination '{hostname}' is in restricted range."
    except ValueError:
        pass

    # Resolve hostname and validate every resolved IP
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        if not addr_info and effective_fail_closed_dns:
            return False, f"SSRF Protection: Hostname '{hostname}' could not be resolved."
        for entry in addr_info:
            ip_str = entry[4][0]
            if is_ip_restricted(ip_str, allow_private_subnets=effective_allow_private, allow_loopback=effective_allow_loopback):
                return False, f"SSRF Protection: Host '{hostname}' resolves to restricted IP: {ip_str}"
    except socket.gaierror as dns_err:
        if effective_fail_closed_dns:
            return False, f"SSRF Protection: Hostname '{hostname}' could not be resolved (DNS resolution failed): {dns_err}"

    return True, "URL allowed"

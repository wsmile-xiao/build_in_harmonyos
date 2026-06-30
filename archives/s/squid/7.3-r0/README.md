# Squid 7.3-r0 for OpenHarmony

## Overview

Squid is a caching proxy for the Web supporting HTTP, HTTPS, FTP, and more. It reduces bandwidth and improves response times by caching and reusing frequently-requested web pages. Squid has extensive access controls and makes a great server accelerator.

**Version:** 7.3-r0  
**Platform:** OpenHarmony aarch64  
**Build Date:** 2025-05-25

## Features

### Included Features
- ✅ HTTP/HTTPS proxy
- ✅ FTP proxy support
- ✅ SSL/TLS interception (via OpenSSL)
- ✅ Kerberos authentication (via krb5)
- ✅ ICAP and eCAP support (via libxml2)
- ✅ POSIX capabilities (via libcap)
- ✅ Caching and bandwidth optimization
- ✅ Access control lists (ACLs)
- ✅ Reverse proxy mode
- ✅ Transparent proxy support

### Disabled Features
- ❌ Shadow password authentication (OpenHarmony limitation)

## Installation

### Prerequisites

Ensure the following dependencies are installed:

```
- openssl (>= 1.1.1)
- krb5 (>= 1.18)
- libxml2 (>= 2.9)
- libcap (>= 2.30)
- nettle (>= 3.6)
- glib-2.0 (>= 2.60)
```

### Installation Steps

1. **Extract the package:**
   ```bash
   tar xzf squid-7.3-r0-ohos-aarch64.tar.gz
   ```

2. **Install the binary:**
   ```bash
   cp bin/squid /usr/local/sbin/
   chmod 755 /usr/local/sbin/squid
   ```

3. **Create necessary directories:**
   ```bash
   mkdir -p /var/log/squid
   mkdir -p /var/cache/squid
   chown -R squid:squid /var/log/squid /var/cache/squid
   ```

4. **Create configuration file:**
   ```bash
   # Sample minimal configuration
   cat > /etc/squid/squid.conf << 'EOF'
   # Basic configuration
   http_port 3128
   cache_dir ufs /var/cache/squid 100 16 256
   
   # Access control
   acl localnet src 10.0.0.0/8
   acl localnet src 172.16.0.0/12
   acl localnet src 192.168.0.0/16
   
   http_access allow localnet
   http_access deny all
   
   # Logging
   access_log /var/log/squid/access.log squid
   cache_log /var/log/squid/cache.log
   EOF
   ```

5. **Initialize cache directories:**
   ```bash
   squid -z
   ```

6. **Start Squid:**
   ```bash
   squid
   ```

## Configuration

### Basic Proxy Configuration

Edit `/etc/squid/squid.conf`:

```conf
# Port configuration
http_port 3128

# Cache configuration
cache_dir ufs /var/cache/squid 1000 16 256
cache_mem 256 MB
maximum_object_size 4 MB

# Access control
acl allowed_clients src 192.168.1.0/24
http_access allow allowed_clients
http_access deny all

# Logging
access_log /var/log/squid/access.log
cache_log /var/log/squid/cache.log
```

### SSL Interception (HTTPS)

For HTTPS interception, additional configuration is needed:

```conf
# SSL Bump configuration
https_port 3129 ssl-bump \
  cert=/etc/squid/ssl_cert/squid.pem \
  generate-host-certificates=on

acl step1 at_step SslBump1
ssl_bump peek step1
ssl_bump bump all
```

### Transparent Proxy Mode

```conf
http_port 3128 transparent
```

Configure firewall rules:
```bash
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 \
  -j REDIRECT --to-port 3128
```

## OpenHarmony-Specific Notes

### Shadow Password Limitation

**Important:** This build does NOT support shadow password authentication.

**Reason:** OpenHarmony uses musl libc which does not implement the shadow password API (getspnam, getspnam_r, etc.). The shadow.h header and related functions are missing.

**Impact:**
- Shadow password-based authentication will not work
- Use alternative authentication methods:
  - Basic authentication (htpasswd files)
  - LDAP authentication
  - Kerberos authentication
  - Custom authentication helpers

**Workaround:**
Configure alternative authentication:
```conf
# Use basic authentication instead
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwd
auth_param basic realm proxy
acl authenticated proxy_auth REQUIRED
http_access allow authenticated
```

### Musl Libc Considerations

This build uses musl libc (not glibc), which may have slight differences:
- Smaller memory footprint
- Different DNS resolution behavior
- May require explicit timezone configuration

### File Paths

Default paths for OpenHarmony:
- Binary: `/usr/local/sbin/squid`
- Config: `/etc/squid/squid.conf`
- Cache: `/var/cache/squid`
- Logs: `/var/log/squid/`

## Running Squid

### Starting Squid
```bash
squid
```

### Testing Configuration
```bash
squid -k parse
```

### Reloading Configuration
```bash
squid -k reconfigure
```

### Stopping Squid
```bash
squid -k shutdown
```

### Checking Status
```bash
squid -k check
```

## Monitoring

### Cache Statistics
```bash
squidclient -h localhost -p 3128 mgr:info
```

### Memory Usage
```bash
squidclient -h localhost -p 3128 mgr:mem
```

### Access Logs
```bash
tail -f /var/log/squid/access.log
```

## Troubleshooting

### Common Issues

1. **Permission denied errors:**
   ```bash
   chown -R squid:squid /var/log/squid /var/cache/squid
   ```

2. **Cannot create cache directories:**
   ```bash
   squid -z  # Initialize cache
   ```

3. **Authentication failures:**
   - Verify shadow password is not configured (not supported)
   - Use alternative authentication methods

4. **DNS resolution issues:**
   - Check /etc/resolv.conf
   - May need to configure dns_nameservers in squid.conf

5. **Memory issues:**
   - Adjust cache_mem in squid.conf
   - Reduce cache_dir size if needed

### Log Files

- `/var/log/squid/access.log` - Client requests
- `/var/log/squid/cache.log` - Squid daemon logs
- `/var/log/squid/store.log` - Cache storage activities

## Security Recommendations

1. **Restrict access** with ACLs
2. **Use HTTPS** for secure connections
3. **Enable logging** for audit trails
4. **Regular updates** - keep Squid patched
5. **Firewall rules** - limit exposed ports
6. **Authentication** - implement proper auth methods
7. **Chroot** - consider running in chroot environment

## Performance Tuning

```conf
# Increase file descriptors
max_filedescriptors 65535

# Optimize cache
cache_mem 512 MB
maximum_object_size 10 MB

# Worker threads
workers 4
```

## Resources

- **Official Documentation:** http://www.squid-cache.org/Doc/
- **Configuration Guide:** http://www.squid-cache.org/Doc/config/
- **FAQ:** http://wiki.squid-cache.org/SquidFaq

## License

Squid is distributed under the GNU General Public License version 2 or later (GPL-2.0-or-later).

## Support

For issues specific to this OpenHarmony build, refer to the build manifest and patch files included in this archive.

---
**Build Information**
- Build Date: 2025-05-25
- Platform: OpenHarmony aarch64
- Compiler: GCC
- Status: Published
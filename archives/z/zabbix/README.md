# Zabbix - Enterprise-class Open Source Monitoring Solution

Zabbix is an enterprise-class open source distributed monitoring solution designed
to monitor and track performance and availability of network servers, devices,
services and other IT resources.

## Current version: 7.4.5

This port includes:
- `zabbix_agentd` - Monitoring agent daemon
- `zabbix_get` - Data retrieval utility
- `zabbix_sender` - Data sending utility

## Dependencies

- openssl (TLS support)
- pcre2 (regular expressions)
- zlib (compression)

## Build

The agent is compiled with OpenSSL TLS support for secure communication with
Zabbix servers/proxies. Server, proxy, agent2, web service, and Java gateway
components are disabled in this port.

# resolvconf

Debian resolvconf — name server information handler for HarmonyOS PC.

## Description

Resolvconf is a framework for keeping up to date the system's information about name servers. It sets itself up as the intermediary between programs that supply name server information (such as ifup, ifdown, DHCP clients, PPP daemon) and programs that use this information (such as DNS caches and resolver libraries).

## Usage

```sh
resolvconf --help
resolvconf --version
resolvconf -a IFACE < /etc/resolv.conf
resolvconf -d IFACE
resolvconf -u
```

## License

GPL-2+

## Source

https://salsa.debian.org/debian/resolvconf

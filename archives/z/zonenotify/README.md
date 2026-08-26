# zonenotify

Send a NS_NOTIFY packet to BIND slave server from your DJBDNS server.

When you update a zone in your djbdns DNS, you must notify the slaves about your change.
zonenotify sends a DNS NOTIFY packet to one or more slave servers.

## Usage

```
zonenotify zone slave1 [slave2] [... slaveN]
```

This sends a NOTIFY packet to slave1 (slave2...slaveN) about zone "zone".
If there are problems, zonenotify displays the error message and exits 1, otherwise exits 0.

## License

BSD-2-Clause

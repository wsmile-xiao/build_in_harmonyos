# gensio - General Stream I/O

gensio (pronounced gen'-see-oh) is a framework for giving a consistent view of various stream (and packet) I/O types. It allows you to create a gensio object and use it without having to know too much about what is going on underneath. You can stack gensio on top of another one to add protocol functionality.

## Key Features

- **Stream Abstraction**: Provides a consistent interface for various I/O types (TCP, Unix sockets, serial ports, sound interfaces, etc.)
- **Protocol Stacking**: Stack multiple protocols (e.g., TCP → SSL → Telnet)
- **Accepter Framework**: Set up listeners that automatically stack protocols when connections come in
- **Cross-Platform**: Works on Linux, BSDs, MacOS, and Windows
- **Easy Encryption**: Simplifies establishing encrypted and authenticated connections

## Tools Included

- **gensiot**: Tool for making basic gensio connections
- **gtlsshd**: SSH-like daemon using certauth and SSL/TLS
- **gtlssh (gsh)**: SSH-like client for connecting to gtlsshd
- **gtlssh-keygen**: Key management tool
- **gmdns**: MDNS provider and query tool
- **gsound**: Sound playback and recording tool
- **gagwpe**: AGWPE (Amateur Radio) interface tool

## Available Gensio Types

- **Network**: tcp, udp, sctp, unix, unixdgram, unixseq
- **Serial**: serialdev, pty
- **Sound**: alsa, portaudio, win32sound
- **Filters**: ssl, telnet, mux, echo, trace, relpkt, msgdelim, and more

## Build Requirements

- autotools (autoconf, automake, libtool)
- Optional: OpenSSL (for SSL support), glib, tcl, swig, python, sctp, avahi, alsa, openipmi, pam

## Build Instructions

```bash
autoreconf -fi
./configure --prefix=/path/to/install
make
make install
```

## Documentation

See BUILDING.rst for build instructions and USING.rst for usage information.

## License

GPL-2.0+ AND LGPL-2.1+

## Homepage

https://github.com/cminyard/gensio
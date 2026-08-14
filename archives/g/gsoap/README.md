# gSOAP

## What is gSOAP?

gSOAP is a toolkit for developing SOAP/XML web services and clients in C and C++. It provides a comprehensive solution for building cross-platform, interoperable web services using the SOAP protocol.

## Key Features

- **SOAP/XML Web Services**: Full support for SOAP 1.1/1.2 and WSDL 1.1/2.0
- **Code Generation**: Automatic generation of C/C++ client and server stubs from WSDL
- **Cross-Platform**: Works on multiple platforms including Linux, Windows, macOS, and now HarmonyOS
- **Language Support**: Both C and C++ APIs with automatic data binding
- **Transport Protocols**: HTTP, HTTPS, TCP, UDP, and custom transports
- **Security Features**: SSL/TLS support, WS-Security, and authentication
- **Compression**: Built-in support for gzip compression
- **DOM Support**: Document Object Model for XML manipulation

## OHOS Adaptation

### Key Adaptation Points

1. **FD_SET/__fd_chk Issue**:
   - On HarmonyOS, the `FD_SET` macro references the `__fd_chk` function which is not available in musl libc
   - Solution: Force use of `poll()` instead of `select()` by adding `|| defined(__OHOS__)` condition
   - Modified files: `gsoap/stdsoap2.c` and `gsoap/stdsoap2.cpp`

2. **Configure Permission Issue**:
   - On HMDFS filesystem, `config.status` may fail to create temporary files
   - Solution: Run `autoreconf -fvi` to regenerate configure scripts

3. **OpenSSL Integration**:
   - Requires OpenSSL for SSL/TLS functionality
   - Need to specify correct header and library paths via CPPFLAGS and LDFLAGS

### Known Issues

- SSL functionality is **enabled** in this build using OpenSSL 1.1.1w from Conan artifact repo
- poll() is used exclusively instead of select() to avoid __fd_chk dependency

### Differences from Linux

- Uses `poll()` exclusively instead of `select()` for socket operations
- Requires explicit CPPFLAGS/LDFLAGS for OpenSSL header/library paths
- HMDFS filesystem requires regenerated configure scripts

## Dependencies

### Build Dependencies

- **OpenSSL** (optional, for SSL/TLS support): openssl/1.1.1w or later
- **Flex**: for lexical analysis
- **Bison**: for parser generation
- **Automake/Autoconf**: for build system
- **GCC/Clang**: C and C++ compiler

### Runtime Dependencies

- **OpenSSL** (if SSL enabled): libssl and libcrypto
- **zlib** (if compression enabled): for gzip support

## Build Instructions

### Basic Build

```bash
# Download source
wget https://www.genivia.com/thanks.html?download=gsoap-2.8.142.zip

# Extract
unzip gsoap-2.8.142.zip
cd gsoap-2.8.142

# Regenerate configure (recommended for OHOS)
autoreconf -fvi

# Configure (SSL enabled, no trimming)
./configure --prefix=/usr/local \
    CPPFLAGS="-I/usr/local/include -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0" \
    LDFLAGS="-L/usr/local/lib" \
    CFLAGS="-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0" \
    CXXFLAGS="-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0"

# Build
make -j$(nproc)

# Install
make install
```

### Build with SSL Support

```bash
# Install OpenSSL first
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openssl 1.1.1w

# Configure with SSL
./configure --prefix=/usr/local \
    CPPFLAGS="-I/usr/local/include -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0" \
    LDFLAGS="-L/usr/local/lib" \
    CFLAGS="-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0" \
    CXXFLAGS="-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0"

# Build and install
make -j$(nproc) && make install
```

## Usage Examples

### Generate C++ Client from WSDL

```bash
# Generate header from WSDL
wsdl2h -o service.h http://example.com/service.wsdl

# Generate C++ stubs
soapcpp2 -i -C service.h

# Compile your client
g++ -o client client.cpp soapC.cpp soapClient.cpp -lgsoap++
```

### Generate C Server

```bash
# Generate header
wsdl2h -o service.h service.wsdl

# Generate C stubs
soapcpp2 -i -S service.h

# Compile server
gcc -o server server.c soapC.c soapServer.c -lgsoap
```

## References

- **Official Website**: https://www.genivia.com
- **Documentation**: https://www.genivia.com/doc
- **Source Downloads**: https://www.genivia.com/downloads.html
- **License**: GPLv2 (commercial licenses available from Genivia)
- **Version 2.8.142 Release**: April 25, 2026

## License

gSOAP is available under two licensing options:

1. **GPLv2**: Free for open-source projects and non-commercial use
2. **Commercial License**: Available from Genivia Inc. for commercial applications

For commercial use, contact Genivia Inc. at contact@genivia.com.
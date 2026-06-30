# Varnish Cache

Varnish Cache is a high-performance HTTP accelerator designed for content-heavy dynamic web sites.

## Description

Varnish Cache is a web application accelerator also known as a caching HTTP reverse proxy. You install it in front of any server that speaks HTTP and configure it to cache the contents. Varnish Cache is really, really fast. It typically speeds up delivery with a factor of 300 - 1000x, depending on your architecture.

## Available Versions

- 7.5.0

## Dependencies

- libedit (20240808 or later)
- pcre2 (10.42 or later)
- ncurses (6.4 or later)
- docutils (0.22.4 or later)
- sphinx (9.1.0 or later)

## Platform Notes

### OHOS Specific Adaptations

- **pthread_cancel**: Not implemented on OHOS. Patched with `#ifdef __OHOS__` guards in vtc_logexp.c, vtc_server.c, and vtc_syslog.c.
- **configure generation**: GitHub source tarball lacks configure file. Requires running `autogen.sh` before configure.
- **rst2man/rst2html**: Python wrapper scripts created for docutils commands.
- **ncurses**: Only static library available, pkg-config file manually created.
- **libedit.so**: Symlink manually created for libedit.so.0.0.74.

## Configuration Options

```bash
./configure --prefix=$DEFAULT_PREFIX \
  --with-rst2man=rst2man.py \
  --with-rst2html=rst2html.py \
  --with-sphinx-build=sphinx-build
```

## Usage

```bash
# Start varnishd
varnishd -a :80 -b localhost:8080

# Check version
varnishd -V
```

## License

BSD-2-Clause

## Source

https://github.com/varnishcache/varnish-cache
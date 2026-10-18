# AAlib 1.4.0

- Upstream: AAlib 1.4rc4 (`aalib-1.4.0` source tree).
- Build system: Autotools.
- OHOS adaptation: disable optional X11, SLang, curses, Linux console, and GPM drivers; the core library and stdout-independent API remain available.
- Upstream test status: the archive provides the `aatest` diagnostic program but no non-interactive automated test suite. The consumer test exercises library initialization and image/framebuffer APIs.

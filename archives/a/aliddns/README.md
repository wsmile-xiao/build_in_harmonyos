# aliddns

OpenWrt/LEDE LuCI support for AliDDNS. The upstream package bundles a shell-based
DDNS driver plus a standalone C utility `po2lmo` that converts gettext `.po`
catalogs into compact `.lmo` (Lua Machine Objects) archives.

On HarmonyOS PC we only adapt the portable `po2lmo` command-line tool (found under
`tools/po2lmo/`); the OpenWrt LuCI shell scripts are not portable and are not built.

## Dependencies

No external libraries — `po2lmo` uses only libc + POSIX headers (`fnmatch.h`,
`sys/mman.h`, `dirent.h`, `arpa/inet.h`).

## OHOS adaptation

- Build system: raw `Makefile` (no `./configure`). The implicit `.c.o:` rule is
  used, so the recipe passes `CC`/`AR`/`RANLIB` explicitly from Conan conf.
- License: Apache-2.0 (source headers) + MIT (upstream Makefile declaration).

## References

- Upstream: https://github.com/ghnicole/aliddns
- Portable tool: `tools/po2lmo/` (`po2lmo.c`, `template_lmo.c`, `template_lmo.h`)

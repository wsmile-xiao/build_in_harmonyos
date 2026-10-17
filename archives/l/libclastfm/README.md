# libclastfm

libclastfm is an unofficial C-API to the Last.fm web service, written by
Vikram Ambrose in 2009 to provide a clean C alternative to the official
Qt-based liblastfm. All HTTP traffic goes through libcurl to
`http://ws.audioscrobbler.com/2.0/`.

- **Upstream**: https://liblastfm.sourceforge.net/
- **Source tarball**: https://downloads.sourceforge.net/project/liblastfm/libclastfm-0.5.tar.gz
- **License**: GPL-3.0-only

## Adaptation

| Version | Build system | Dependencies | Notes |
|---------|--------------|--------------|-------|
| 0.5 | autotools | libcurl (cmd-pkgs curl 8.19.0 prebuilt) | HMDFS configure patch (E011); upstream 5 online integration tests declared skipped (require Last.fm credentials + outbound network) |

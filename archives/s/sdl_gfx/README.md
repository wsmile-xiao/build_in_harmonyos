# sdl_gfx

`SDL_gfx` is A. Schiffler's SDL 1.2 extension library: drawing primitives
(lines/boxes/circles/ellipses/polygons/bezier, plus anti-aliased variants),
`rotozoom`/`zoom` surface transforms, a framerate manager and C/MMX image
filters on top of SDL surfaces. This archive holds the Conan recipe and the
OpenHarmony PC adaptation.

## Version note

The task targeted **sdl_gfx 2.0.5**, which upstream never distributed
(`SDL_gfx-2.0.5.tar.gz` → HTTP 300, Changelog `Ver 2.0.5 - n/a`, no git tag,
absent from Debian and the usual mirrors). The adaptation therefore uses
**2.0.7**, the earliest release still downloadable from the official site; the
2.0.x line has an identical SDL 1.2 dependency.

## Layout

```
2.0.7/
├── conanfile.py            # sdl/1.2.15 (transitive_headers=True), sdl-config shim, --disable-mmx
├── conandata.yml           # official URL + sha256 + 4 portability patches (strip: 1)
├── manifest.yaml           # version metadata
├── notes.md                # adaptation notes (errors, root causes, fixes, test inventory)
├── patches/                # config.guess / config.sub OHOS support (top level + Test/)
├── reports/                # 本地验证证据（conan-verify/conan create/W3/测试报告；被 .gitignore 排除，不随 PR 交付）
└── test_package/           # consumer test: 20 pixel/API assertions
```

## Status

- `conan create` (profile `ohos-aarch64`) → **exit 0**; consumer test_package **20/20 assertions pass**.
- `conan-verify` G0–G4 + L2/L4/L5 → **PASS**; `finish`'s blocking W3 local-CI gate → **PASS**.
- Deliverable: static `libSDL_gfx.a` + 5 public headers (the bundled 2001 libtool
  cannot emit shared objects for OHOS).

See `2.0.7/notes.md` for the full error/fix chain and the upstream test inventory
(4 demo programs, no automated suite — `make check` is a no-op).

# kxl

KXL (Kacchan X Windows System Library) provides simple X11 drawing helpers. On OHOS the OSS/PulseAudio sound backend is replaced by a no-op stub; apps that need audio should integrate OHAudio directly.

## Conan

```bash
conan install --requires=kxl/1.2.4 -r=ohpcd
```

```cmake
find_package(kxl REQUIRED)
target_link_libraries(app PRIVATE kxl::kxl)
# On OHOS prefer static when loader ACL blocks dlopen from /storage:
# target_link_libraries(app PRIVATE kxl::kxl_static)
```

```c
#include <KXL.h>
```

## Dependencies

- `libx11/6.4.0` (upstream libX11 1.8.10; pulls xorgproto / xtrans / libxcb transitively)

## Version History

| Version | Status | Notes |
|---------|--------|-------|
| 1.2.4 | built | OHOS Conan recipe (CMake + X.Org; audio stubbed) |

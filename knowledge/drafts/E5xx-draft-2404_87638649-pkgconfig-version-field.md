# DRAFT-E5xx: Conan PkgConfigDeps 生成的 .pc 版本字段用包版本而非库 ABI 版本，上游版本约束探测失败（vlc/ffmpeg 案例）

## 场景

上游软件（autotools/pkg-config 探测）对依赖库有【库 ABI 版本】约束
（如 vlc 要求 `libavcodec >= 57.37.100`、`x264 >= 0.148`），而 Conan
PkgConfigDeps 生成的 .pc 的 `Version:` 字段一律是【包版本】（ffmpeg/4.4.8
→ `Version: 4.4.8`；x264/r3223 → `Version: r3223`）。版本语义错位导致
`PKG_CHECK_MODULES` 比较失败。

## 典型报错

```
configure: error: Requested 'libavcodec >= 57.16.0' but version of libavcodec is 4.4.8
Requested 'libavutil >= 52.0.0' but version of libavutil is 4.4.8.
configure: error: Requested 'x264 >= 0.148' but version of x264 is r3223
```

## 根因

| 版本类型 | 含义 | 来源 |
|---|---|---|
| 包版本 | Conan recipe 版本坐标（4.4.8/r3223） | PkgConfigDeps 直接引用 |
| 库 ABI 版本 | SO_NAME 主次版本（58.134.100/0.165.3223） | 上游原生 .pc 才有 |

伴生陷阱（同一批 .pc 修正）：
1. **头文件子目录**：conan .pc 的 `Cflags: -I${includedir}` 只到 include/，
   而 opus 头在 `include/opus/`、fribidi 头在 `include/fribidi/`——上游
   `#include <opus.h>` 直引时找不到头。
2. **原生 .pc 路径残留**：包内 `lib/pkgconfig/*.pc` 的 Version 正确，但
   prefix/libdir 可能是构建期残留（`b/<hash>/p`）——不能整体复制，
   必须逐行重写路径变量。
3. **静态库传递依赖不展开**：`Requires.private: ogg` 不被 `pkg-config
   --libs` 展开（flac/vorbis 静态库场景）→ 提升为公共 Requires；
   x265 静态库 Libs 需补 `-lc++`。

## 修法（配方 build() 内，configure 之前）

```python
def _fix_pkgconfig_versions(self):
    import glob, os
    pc_dir = self.generators_folder
    # 1. 读 conan 生成 .pc 的 prefix（= 依赖包真实路径）
    prefixes = {}
    for pc in glob.glob(os.path.join(pc_dir, "*.pc")):
        for line in open(pc):
            if line.startswith("prefix="):
                prefixes[os.path.basename(pc)[:-3]] = line.strip()[7:]
                break
    # 2. 用包内原生 .pc 替换（Version 字段正确），逐行重写路径
    ff_prefix = prefixes.get("ffmpeg")
    for name in ("libavcodec", "libavutil", "libavformat", ...):
        gen_pc = os.path.join(pc_dir, name + ".pc")
        native_pc = os.path.join(ff_prefix, "lib", "pkgconfig", name + ".pc")
        if os.path.exists(gen_pc) and os.path.exists(native_pc):
            out = []
            for line in open(native_pc).read().split("\n"):
                if line.startswith("prefix="):
                    out.append(f"prefix={ff_prefix}")
                elif line.startswith("exec_prefix="):
                    out.append("exec_prefix=${prefix}")
                elif line.startswith("libdir="):
                    out.append(f"libdir={ff_prefix}/lib")
                elif line.startswith("includedir="):
                    out.append(f"includedir={ff_prefix}/include")
                else:
                    out.append(line)
            open(gen_pc, "w").write("\n".join(out))
```

## 验证

vlc/3.0.23（2026-09-25，本机 conan create 全绿）：修正 libavcodec/
libavutil/libavformat/libswscale/x264/opus/fribidi/flac/vorbis/x265
共 10+ 个 .pc 后，configure 探测全过（`checking for AVCODEC... yes`、
`checking for X264... yes`），test_package 5/5 PASS。

## 与既有条目的边界

- E468 解决"pc 找不到"（PKG_CONFIG_PATH 注入）——本条解决"pc 找到了但
  Version 语义错位"，两者是 pkg-config 集成的不同失败层。
- E247 解决静态库 C++ 运行时传递（Libs.private）——本条含 x265 -lc++
  场景但主体是版本字段与路径重写。

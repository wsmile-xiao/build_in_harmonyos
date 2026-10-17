# 草稿：zlib ≥1.2.13 移除 ASMV 后接入自定义 longest_match 的三段式模式

> 状态：**草稿**（fast_zlib 0.0-git6141d21116 适配实测，2026-09-28）。
> 一条主发现（ASMV 替换协议恢复）+ 一条附带发现（Conan 2 copy dst 空包坑），
> 均属于「下一个替换 zlib deflate 内部函数的任务还会用到」。

## 错误特征

```
# zlib 1.2.13+ 直接按旧方式替换 longest_match 时：
deflate.c:1272: local uInt longest_match(s, cur_match)   ← 文件内静态，外部实现无法替换
# 或编译后无效果（静默回退到原实现）
# Conan create 阶段（附带坑）：
package(): WARN: No files in this package!
CMake Error ...: Library 'z' not found in package.  If 'z' is a system library, declare it with 'cpp_info.system_libs'
```

## 根因

1. **主发现**：zlib 1.2.13（2022-10）上游移除了 ASMV 选项，deflate.c 中的
   `longest_match` 被限定为 `local`（文件内静态）。旧协议（`#define ASMV` 后外部
   提供同名函数替换）失效，第三方对 deflate 内部函数的优化（如 fast_zlib 的
   C 版快速匹配器）无法再接入，且不报错——静默回退，压缩性能"白做"。
2. **附带坑**：Conan 2 的 `conan.tools.files.copy()` 中 `dst` 是相对/当前目录语义；
   `package()` 阶段 CWD 是 **build 目录**，写 `dst="lib"` 会把 `libz.a` 复制到
   `build/lib/` 而不是 `package/lib/` → 包产物为空，下游 CMakeDeps 报
   `Library 'z' not found in package`。

## 方案

### ① 恢复 ASMV 守卫（上游官方补丁）
应用上游 `Sources/zlib_1.2.13.patch`（给 deflate.c 恢复 `#ifndef ASMV` 守卫，使
ASMV 定义时 `longest_match` 保持外部可见）。注意该补丁路径带 `original/` `patched/`
前缀，conandata 补丁条目必须 `strip: 1`（Conan apply_conandata_patches 默认
strip=0，直接应用会报 source/target file does not exist）。

```yaml
# conandata.yml
patches:
  - patch_file: "patches/zlib_1.2.13.patch"
    base_path: "zlib"
    strip: 1
```

### ② deflate_stub 三段式接入（等价上游 genmake TYPE=C）
```c
/* Test/deflate_stub.c —— 编译进库以替换 deflate.c */
#define ASMV
#include "deflate.c"
#undef local
#define local
#include "../Sources/match.h"
void match_init() {}
```
编译命令（-I zlib 使 `#include "deflate.c"` 命中 zlib/ 目录）：
```bash
clang -c -O2 -fPIC -DUNALIGNED_OK -I zlib -o deflate_stub.o Test/deflate_stub.c
```

### ③ Conan copy dst 修复（附带坑）
```python
from conan.tools.files import copy
copy(self, "libz.a", dst=os.path.join(self.package_folder, "lib"),
     src=self.build_folder)
copy(self, "zlib.h", dst=os.path.join(self.package_folder, "include"),
     src=os.path.join(self.source_folder, "zlib"))
```

## 验证

```bash
# 对比：同数据 level 9，NewC 与 Orig 压缩 size 一致且吞吐更高 → 快速匹配路径真正生效
./obj/bin/test-C-linux <data> --compact --memory --level=9
#   "NewC":9  Data: 0.2 Mb  Size: 205480 bytes  Speed: 22.84 Mb/s   rc=0
./obj/bin/test-Orig-linux <data> --compact --memory --level=9
#   "Orig":9  Data: 0.2 Mb  Size: 205480 bytes  Speed: 20.46 Mb/s   rc=0

# 空包修复后 conan create 产物完整
ls <pkg>/lib/libz.a <pkg>/include/zlib.h <pkg>/include/zconf.h
```

## 适用边界与反例

- **适用**：zlib ≥1.2.13（ASMV 已移除）、C 语言、需要替换 deflate 内部函数
  （longest_match）的第三方优化；任何手写 `package()` 用 conan copy 的 Conan 2 配方。
- **反例**：zlib <1.2.13 无需补丁（旧 ASMV 协议仍有效）；非 deflate 内部函数替换
  （inflate 等）不适用本模式；CMake 安装路径（`cmake.install()`）不受 copy dst 坑影响。

## 查重差异

- index.tsv 关键词 `longest_match`/`ASMV`/`deflate_stub` = 0 命中 → 未命中。
- E515/E526 是 Conan patch strip 语义（配置/CI 校验），与本条"ASMV 替换协议恢复"
  触发面不同（补丁应用 vs deflate 内部函数替换），非因果重复。
- E541（zlib 静态 PIC）为打包/链接侧，与本条编译接入侧互补。
- 附带坑（copy dst → 空包）与 E362（资源物化）语义不同，无直接条目。
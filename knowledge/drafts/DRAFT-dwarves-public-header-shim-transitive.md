# DRAFT-dwarves-public-header-shim-transitive — 库公开头直接 include musl 垫片头（obstack/argp）与 elfutils 头，OHOS 消费者需显式 requires+link 传递依赖

> **Contributor**: pc1-26 | **Status**: DRAFT | **Updated**: 2026-09-10
> **Severity**: blocking (2) | **Category**: conan / cmake / packaging / musl-shim
> **Audience**: 在 OHOS-musl 上适配公开头链依赖 argp/obstack/elfutils 头的 Conan 2 library 配方作者

## 触发（trigger）

dwarves 1.30 OHOS PC aarch64 适配：公开头 `include/dwarves/dwarves.h` 第 14-16 行
直接 `#include <obstack.h>` / `<dwarf.h>` / `<elfutils/libdwfl.h>`。
OHOS-musl libc 无 glibc 的 argp/obstack，需 argp-standalone/1.5.0 与 musl-obstack/1.2.3 垫片，
dwarf.h 与 elfutils/libdwfl.h 来自 elfutils/0.195。
test_package 消费者仅 `find_package(dwarves)` + `target_link_libraries(... dwarves::dwarves)`
编译报 `fatal error: 'obstack.h' file not found`。

## 症状（symptom）

```
In file included from .../include/dwarves/dwarves.h:14:
fatal error: 'obstack.h' file not found
```

生成目录 `test_package/build/<generators>/musl-obstack-<arch>-data.cmake` 中：

```
set(musl-obstack_INCLUDE_DIRS_RELEASE )   # 空！
set(musl-obstack_LIBS_RELEASE )           # 空！
```

## 根因（root cause）

Conan 2.29.1 CMakeDeps 生成器在**消费端**只对"配方直接 requires 的包"生成包含
include 目录的完整配置；对经依赖包传递引入的包，`*-data.cmake` 中
`xxx_INCLUDE_DIRS_RELEASE` 被置空，仅保留链接库引用。库自身（dwarves 主包）
构建不报错——CMakeToolchain 以 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH 兜底注入了依赖头路径，
掩盖了传播缺失；而消费者的 dwarves.h 公开头直接 include 垫片/elfutils 头时，
传递依赖（musl-obstack/argp-standalone/elfutils）的 include 元数据为空 → 编译失败。

## 方案（approach）

test_package（消费者）显式声明并链接传递依赖 target：

```python
def requirements(self):
    self.requires(self.tested_reference_str)
    self.requires("musl-obstack/1.2.3")
    self.requires("argp-standalone/1.5.0")
    self.requires("elfutils/0.195")
```

```cmake
find_package(dwarves CONFIG REQUIRED)
find_package(musl-obstack CONFIG REQUIRED)
find_package(argp-standalone CONFIG REQUIRED)
find_package(elfutils CONFIG REQUIRED)
target_link_libraries(consumer PRIVATE dwarves::dwarves
    musl-obstack::musl-obstack argp-standalone::argp-standalone elfutils::elfutils)
```

## 验证（verification）

```
conan create archives/d/dwarves/1.30 -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```
修复前 consumer 编译 fatal error: 'obstack.h' file not found；
修复后 consumer 编译链接运行 OK（`dwarves version: 130` + `consumer: OK`），
W3 L1 门禁通过，test-ledger.md 记录全量证据。

## 适用边界（boundary）与反例

- 适用：公开头链依赖 musl 垫片头或第三方头（obstack/argp/libdw 等）的 C/C++ 库，
  OHOS-musl 目标平台
- 反例：glibc 平台无需垫片头；公开头自包含（不 include 外部头）的库无此问题；
  已通过 requires 声明为直接依赖的库不受影响
- 查重关联：DRAFT-conan2-cmakedeps-transitive-include-strip（pokerstove/boost 案例）覆盖
  同根因，本草稿补充 musl 垫片头三 target 组合与公开头链场景

## 关系字段

- similar_to: DRAFT-conan2-cmakedeps-transitive-include-strip
- caused_by: conan-cmakedeps-transitive-include-empty（根因同草稿 DRAFT-conan2-cmakedeps-transitive-include-strip）
- prerequisite_of: 消费者可用性门禁（每个适配库至少 1 个消费者用例）
- conflicts_with: 无
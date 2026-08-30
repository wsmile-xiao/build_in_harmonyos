# DRAFT-cute_aseprite-1.0.0-header-compile-fixes — 单头文件 v1.00 编译错误修复

> 对应 KV：`knowledge/drafts/DRAFT-cute_aseprite-1.0.0-header-compile-fixes.kv`
> 触发事件：cute_aseprite 1.0.0 HarmonyOS PC 适配（R02 adapt）

## 问题（error_signature）

cute_aseprite.h v1.00 在纯 C（`-std=c99`/`-std=c11`）编译下暴露四类上游缺陷：

```text
error: unknown type name 'uint8_t'                 // struct 定义处缺 <stdint.h>
error: must use 'struct' tag to refer to type 'ase_color_t'
error: use of undeclared identifier 'fp'           // load_from_file 缺 <stdio.h>
warning/error: call to undeclared function 'CUTE_ASSERT'   // 只定义了 CUTE_ASEPRITE_ASSERT
```

## 根因（root_cause）

1. struct 定义（ase_color_t/ase_fixed_t/ase_color_profile_t 等）使用
   `uint8_t`/`uint16_t`/`uint32_t`，但 `#include <stdint.h>` 只出现在实现区
   （约 335 行），声明区（约 81-171 行）之前缺失 → `unknown type name`；
2. forward typedef 列表缺少 `typedef struct ase_color_t ase_color_t;`，
   后文裸用 `ase_color_t` → `must use 'struct' tag`；
3. `cute_aseprite_load_from_file` 使用 `FILE`/`fread`/`fclose`，但实现区
   未 `#include <stdio.h>` → `undeclared identifier 'fp'`；
4. 解析函数调用 `CUTE_ASSERT`，但上游只定义了 `CUTE_ASEPRITE_ASSERT` →
   隐式声明（链接期 undefined symbol: CUTE_ASSERT）。

## 方案（fix_approach）

v1.04 (master) 已全部修复，逐项对齐上游修复即可
（`patches/0001-add-stdint-include.patch`，在 `source()` 内经
`apply_conandata_patches` 应用）：

1. 在 `CUTE_ASEPRITE_MAX_TAGS` 定义后补 `#include <stdint.h>`；
2. 在 `typedef struct ase_cel_extra_chunk_t` 与 `ase_color_profile_t` 之间补
   `typedef struct ase_color_t ase_color_t;`；
3. 在 `#if !defined(CUTE_ASEPRITE_ALLOC)` 块内、`#include <stdlib.h>` 之前补
   `#include <stdio.h>`；
4. 将 4 处 `CUTE_ASSERT(` 调用改为 `CUTE_ASEPRITE_ASSERT(`。

测试注意（构造合法 .ase 字节流）：
- `s_read_string` 读 **u16** 长度，layer name 长度字段须写 u16（不是 u8）；
- chunk `chunk_size` 字段含 size+type 共 6 字节头，写完整 chunk 总长；
- 头部 128 字节 + 帧头 16 字节：layer chunk 起始 offset 144，cel 紧随后。

配 test_package 用 `CUTE_ASEPRITE_IMPLEMENTATION` 单 TU 编译运行，
8 项断言验证 `load_from_memory` 解析帧/层/cel/像素字段。

## 验证（verification）

```text
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64  → EXIT 0
PASS: cute_aseprite_load_from_memory returns non-NULL
PASS: frame_count == 1
PASS: w/h == 2x2
PASS: layer_count == 1
PASS: frame[0] cel_count == 1
PASS: frame[0] duration == 100ms
PASS: cel pixel[0] == 0x40
PASS: cel pixel[15] == 0x4f
HMBS_TEST_PACKAGE_RESULT: PASS (0 failures)
```

## 适用边界

- cute_aseprite 1.0.0（cute_headers 集合内单头文件）
- 其他以单头文件形式发布、声明区依赖 `stdint`/`stdio` 的 header-only 库
- 平台：OHOS 6.0 arm64，通用任何 `-std=c99` 纯 C 编译环境

## 查重差异

- 与 DRAFT-astrometry.net-0.98-conan-dep-include 不同：本条目是**上游头文件
  自身缺失 include/typedef/宏定义**（header-only 库可移植性缺陷），
  非 Conan 依赖 include/lib 接入 raw Makefile 构建的问题。

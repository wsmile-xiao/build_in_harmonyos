# wuffs

Wuffs 是一个编程语言加标准库项目：语言本身用于编写内存安全的编解码器，
标准库（*Wuffs the Library*）提供图像解码（PNG/GIF/JPEG/WebP/BMP/TGA/QOI/
Netpbm/WBMP/ETC2/ThumbHash/NIE/VP8）、压缩编解码（deflate/gzip/zlib/lzma/
lzma2/xz/bzip2/lzip/LZW）、JSON 词法与指针，以及哈希（adler32/CRC-32/
CRC-64/SHA-256/xxhash32/xxhash64）。库的 C 形态由仓库在检入时生成并入库。

- 上游仓库：https://github.com/google/wuffs
- 版本：0.4.0-alpha.10（上游 tag `v0.4.0-alpha.10`）
- 许可证：Apache-2.0 OR MIT
- 类型：single file C library（stb 风格「头文件库」，单个 `.c` 文件兼作头文件与实现）
- 构建系统：无（上游对库本体没有 configure/make/CMake）

## 用途

「Wuffs the Library」以 *single file C library* 形式发布：`release/c/` 下每个
受支持版本对应一个文件，例如 `release/c/wuffs-v0.4.c`。把这个文件放进自己的
构建系统即可，不需要安装单独的库，也不需要 Go 工具链：

```c
#include "wuffs-v0.4.c"          // 头模式：只得到声明
```

或在**恰好一个**翻译单元里：

```c
#define WUFFS_IMPLEMENTATION
#include "wuffs-v0.4.c"          // 实现模式：得到全部实现
```

## 在 OpenHarmony / HarmonyOS PC 上

- 包安装路径：`include/wuffs/wuffs-v0.4.c`，消费方
  `#include <wuffs/wuffs-v0.4.c>`；另有 `licenses/` 下三份许可证。
- 消费方 CMake：`find_package(wuffs REQUIRED)` +
  `target_link_libraries(... wuffs::wuffs)`（包内不产生任何 `.a`/`.so`，
  目标只提供 include 路径）。
- 纯 C99，无需额外依赖；本设备 `clang 15.0.4`（aarch64-unknown-linux-ohos）
  实测 C99 与 C++11 下头模式/实现模式均以 `-Wall -Werror -Wpedantic` 级别的
  上游 warning 集零警告通过。
- 上游生成的 AArch64/NEON 代码路径使用 C99 复合字面量；若在 **C++** 下按
  `-Wpedantic` 编译，需补 `-Wno-c99-extensions`（否则 8 条硬诊断）。
- 未定义 `WUFFS_IMPLEMENTATION` 的翻译单元中，编解码结构体是刻意设计的不透明
  类型（默认构造被 delete，`sizeof T` 被故意放大 123MB 以拒绝误用）。此类
  翻译单元须用 `sizeof__wuffs_xxx()` 分配后调用 C API，或直接用 C++ 便捷层
  （`wuffs_png__decoder::alloc()` + 成员方法）。
- `decode_frame` 需要一个至少为 `workbuf_len().max_incl` 的临时缓冲，
  上游自带调用方均按其自报长度分配。

## 在 OpenHarmony 上的平台相关行为

wuffs 在**编译期**按 CPU 架构选择代码路径，由 `release/c/wuffs-v0.4.c` 的配置段
控制（`__ARM_NEON` → NEON 路径；`__ARM_FEATURE_CRC32` → ARM 硬件 CRC-32）。这两条
路径的前提是**小端序**与**可用的非对齐访存**，因此它们在 aarch64 上是否成立属于
平台属性，需要在目标设备上验证：

- 不希望任何架构特化代码时，可定义 `WUFFS_CONFIG__AVOID_CPU_ARCH` 强制走纯可移植
  C（本包的 `test_package` 就用它对同一源文件做第二次构建，作为对照）。
- 本包实测（OHOS PC aarch64）：默认构建选中 NEON（`have_arm_neon() == 1`），
  `AVOID_CPU_ARCH` 构建未选中（`== 0`），两者在同一批已知答案（含 16 个非对齐
  输入偏移下的 PNG 解码）上结果完全一致——即 NEON 快速路径与可移植回退等价。

## 依赖关系

- 编译依赖：无（仅 libc / libc++ 的 `<stdint.h>`/`<string.h>`/`<stdlib.h>`）
- 运行依赖：无

## 参考资料

- 构建说明：https://github.com/google/wuffs/blob/main/BUILD.md
- 库使用说明：https://github.com/google/wuffs/blob/main/doc/wuffs-the-library.md
- 版本化单文件产物的说明：`release/c/README.md`

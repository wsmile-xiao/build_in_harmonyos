# scalpel 1.60-git20240110.6960eb2 适配笔记

## 编译环境
- 构建系统: makefile（raw GNU Make，无 configure/cmake/meson）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（OHOS aarch64 profile，/data/service/hnp/bin/clang）
- 状态: built

## 上游与版本形态
- 上游仓库: https://github.com/nolaforensix/scalpel-1.60（scalpel 1.60 维护分支，
  Golden G. Richard III；注意不是 sleuthkit/scalpel——那是 scalpel 2.0 C++ 代码基，
  commit 6960eb2 在 sleuthkit 仓不存在，与 Debian .dsc Homepage 字段一致）
- 版本形态: Debian 快照形 `1.60+git20240110.6960eb2`，仓库口径把 `+` 写作 `-`
- 同源核验: Debian pool `scalpel_1.60+git20240110.6960eb2.orig.tar.xz`
  （sha256 f5f272367e9409feb6a2a5429683a00c00f888e4bd4314ffad35b09f61bdf6d8）
  与上游 commit 6960eb28d53a88fc9994db0cdb4b20bdac1c99fd 的 codeload 快照
  （sha256 ff828ede7a1140cd638e14c13f63bd0d174513e8a1c23a5ade6d2be3841fea7f）
  18 个文件逐一 sha256 比对**完全一致**——配方取 GitHub 官方 URL + 其 sha256
- 源码规模: 19 个文件、约 60 KB；无捆绑 libtre、无外部库依赖（仅 libc/libm）

## 编译步骤

1. init-build: 上游 commit 快照归档（sha256 见上）。
2. lang-preflight: 通过（C，R47）。
3. 探索性编译: `clang -D__LINUX -O2 -o scalpel helpers.c files.c scalpel.c dig.c
   prioque.c base_name.c -lm` → 成功；`./scalpel -h` 输出横幅正常。
4. 雕刻功能实测: 3 个 HTML 块埋入 3.9KB 原始镜像 + 最小 scalpel.conf（TAB 分隔）
   → 雕出 3 个文件、内容逐字正确、audit.txt 记录 files carved = 3、exit 0。
5. 配方: `make linux -j1 CC="<clang> -D__LINUX -O2"`（-D__LINUX 必须显式放进命令行
   CC，见问题表 #2）；package() 复制 scalpel / scalpel.conf / scalpel.1 / 许可证。
6. conan-verify G1-G4/L2/L4/L5 通过；finish W3 本地 CI 通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS sysroot 无 `<error.h>`，6 个源文件全部编译失败 `fatal error: 'error.h' file not found` | `__LINUX` 分支无条件 include glibc 专属 error.h，但 `error()` 全工程从未调用（残留 include） | 0001 补丁：`__GLIBC__` 守卫该 include（portability，不引入平台宏） |
| 2 | `scalpel -o <不存在的输出目录>` 必然报 `ERROR: You have attempted to use a non-empty output directory` | `convertFileNames()` 对输出目录调 `realpath()`：glibc 解析最长存在前缀成功返回，musl/OHOS 要求每个分量都存在 → 返回 NULL 且不动缓冲区，未初始化栈垃圾（截到 `" domain string"`）被 strncpy 进 outputdirectory | 0002 补丁：判 realpath 返回值，失败保留原路径（对 glibc 行为零改动） |
| 3 | 命令行 `CC=clang` 时若不注入 `-D__LINUX`，helpers.c:64 报 `error: incompatible integer to pointer conversion` | scalpel Makefile 用**目标级** `linux: CC += -D__LINUX` 注入平台宏；GNU make 对命令行变量忽略 makefile 内（含目标级）`+=` 追加（make 4.4.1 实测：`make goal CC=clang` 得 `CC=[clang]`，`-DX` 丢失） | 配方在命令行 CC 里显式并入 `-D__LINUX`（E649 草稿沉淀） |

## 源码修改

- `patches/0001-guard-glibc-only-error-h-include.patch`：scalpel.h 的
  `#include <error.h>` 加 `__GLIBC__` 守卫（error.h 仅 glibc 提供，该函数未被使用）。
- `patches/0002-realpath-nonexistent-output-dir.patch`：scalpel.c
  `convertFileNames()` 的两次 `realpath()` 结果判空后再 strncpy。

## 依赖版本

无第三方依赖（仅 libc/libm，系统自带；pthread 互斥量在 musl 中内建，无需 -lpthread）。

## 验证结果

```bash
# 探索性编译（设备直跑）
clang -D__LINUX -O2 -o scalpel helpers.c files.c scalpel.c dig.c prioque.c base_name.c -lm
# → Build finished; ./scalpel -h → "Scalpel version 1.60"

# 端到端雕刻（test_package/test.sh 同款流程）
# 3.9KB 镜像埋 <html>alpha|beta|gamma</html> → 雕出 3 个 .html，内容逐字正确
# audit.txt: "files carved = 3"、exit 0
```

## 上游测试

上游**无测试套件**：Makefile 仅 all/linux/bsd/win32/nice/clean 目标（无 check/test），
源码树无 tests/ 目录、无任何测试框架注册（19 个文件逐项核对）。
N（上游测试总数）= 0，N′ = 0；验证以 test_package 消费者测试（8 项断言）承担。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/scalpel | 主可执行文件（PIE/NX/RELRO/BIND_NOW 全开） |
| bin/scalpel.conf | 默认雕刻配置（随二进制分发，便于就地使用） |
| res/scalpel.1 | man 手册页 |
| licenses/LICENSE, licenses/gpl.txt | GPL-2.0 许可证文本 |

## 注意事项

- 上游 `-h`/`-V` 的退出码是 1（usage 设计如此），消费者测试断言横幅文本而非退出码。
- scalpel 拒绝已存在且非空的输出目录（forensic soundness），测试与使用时输出目录
  必须预先不存在。
- `pthreadGC1.dll` 是 win32 分发物，linux 构建不涉及，不打包。

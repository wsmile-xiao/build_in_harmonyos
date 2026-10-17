# xworld 2.0 适配笔记

## 目标库
- **名称**: xworld
- **版本**: 2.0
- **类型**: application（单二进制 X11 地球查看器）
- **上游**: FreeBSD distfile `pkg.freebsd.org/local-distfiles/naddy/xworld-2.0.tar.gz`
- **许可**: BSD-4-Clause（作者 Alexandre Wennmacher）
- **构建系统**: 手写 `configure` + `Makefile.in`（非 autoconf 生成）
- **语言**: 纯 C（7 个 .c + 6 个 .h）
- **三方依赖**: libX11

## 构建机制
xworld 的构建过程较为特殊：
1. `make compile_world` — 编译 compile_world 辅助程序
2. `./compile_world` — 读取 world.dat，生成 world.o（原始像素 mmap 数据）
3. `make pad` — 编译 pad 辅助程序（页面对齐）
4. `make xworld` — 编译 xworld.c → xworld.tmp（ELF），再运行 pad，最后 `cat xworld.tmp world.o > xworld`
5. 最终二进制 = ELF 头部 + 尾部 world.o 数据段，运行时自行 mmap 自身

## OHOS 适配点

### 补丁 0001 — compile_world.c: 缺失头文件
- **根因**: `compile_world.c` 调用 `exit()` 但未 `#include <stdlib.h>`，调用 `ftruncate/fileno/lseek` 但未 `#include <unistd.h>`
- **修复**: 在 `#include <sys/types.h>` 后追加 `#include <stdlib.h>` 和 `#include <unistd.h>`
- **说明**: `register_t` 在 OHOS musl 的 `bits/alltypes.h` 中已有定义（为 `_Reg` = `long`），无需额外 typedef
- **类型**: portability

### 补丁 0002 — Makefile.in: 链接与安装
- **根因**:
  1. Makefile.in 链接行缺少 `$(LDFLAGS)`，导致 libX11 等依赖库路径无法传入
  2. install 目标使用 `-g bin -o bin`，OHOS 无对应 group/user
  3. `$(MKDIR)` 缺少 `-p` 参数，多级目录创建失败
- **修复**:
  1. 在 `$(MORELIBS)` 后添加 `$(LDFLAGS)`
  2. install 去掉 `-g bin -o bin`，`MKDIR` 加 `-p`
- **类型**: platform（OHOS 平台专属）

## 配方设计
- `package_type = "application"`（单二进制，不导出头文件/库）
- 仅声明 `requires("libx11/1.8.13")`
- 传递依赖（xorgproto、libxau、libxcb、xtrans、xcb-proto）由 libX11 自动处理
- 构建通过 `make` 命令行直接传入所有变量，不运行 csh configure 脚本
- `LDFLAGS` 聚合所有依赖包的 lib 目录

## 验证结果
- `conan create` — 真编（recipe revision `e91b493639673369b6e8c67ca28a40a2`，package_id `aaa36621d5020ccfae7b024d38905f1758ac7036`）
- `test_package` — **5 项断言通过**：
  1. 二进制存在且为有效 ARM64 ELF
  2. 动态链接 libX11（readelf 确认）
  3. 运行时 X11 错误而非缺库（headless 环境预期行为）
  4. OHOS mmap 消费者用例通过（验证 2979312 字节 world.o 数据段自加载机制）
  5. test_package/MANIFEST.yml assertion_count=5
- 上游测试：**无**（xworld 是图形应用，README/INSTALL 均无自动化测试入口）
- `conan-verify` — PASS（G1/G2/G3 全绿，G4/L2/L4/L5 因包类型跳过）
- `finish` — W3 通过

## 已知限制
- xworld 需要 X11 display（`$DISPLAY`）才能运行
- 在 headless/无 X server 环境下，test_package 的运行时测试预期失败（X11 错误），这是环境限制而非构建问题
- OHOS PC 是否提供 X server 属平台特性，非本配方问题
- 二进制安装后需通过 X11 消费者用例验证

## 交付物
| 文件 | 说明 |
|------|------|
| bin/xworld | ELF arm64 可执行文件（含尾部 world.o 数据） |
| licenses/xworld.COPYRIGHT | BSD-4-Clause 版权声明 |
---

**编译结束**: 2026-09-23 12:47
**最终状态**: built

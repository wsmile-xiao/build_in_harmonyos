# pipebench — OpenHarmony 编译档案

## 软件简介
pipebench（Thomas Habets 编写）是一个测量 **stdin→stdout 管道吞吐速率** 的命令行基准工具：
从标准输入读数据、以近乎原速写回标准输出，并按时间输出速率统计
（`... | pipebench | ...`，典型用法如 `cat file | pipebench > /dev/null`）。
许可证 GPL-2.0-or-later。本次适配上游发布版 **0.40**。

## OHOS 适配要点
- 上游 Makefile 硬编码 `CC=gcc`，且 `install` 目标写死到 `/usr/local/bin`、`/usr/local/man/man1`
  —— conanfile 以 `make CC=<OHOS clang>` 覆盖编译器完成编译，产物由 `package()` 自行拷入
  `bin/` 与 `share/man/man1/`，**不调用** `make install`。
- 单文件 C 工具，无 configure/autotools，无编译期/运行期依赖。
- 源码使用了 legacy BSD 类型 `u_int64_t` 等（仅在 `#ifdef sun` 下才定义）；glibc 由
  `<sys/types.h>` 提供，但 **musl/OHOS 不提供**。适配：补 `#include <stdint.h>`，并把类型
  定义块改为 `#if defined(sun) || !defined(__GLIBC__)` 宏映射到 `uint8_t/…/uint64_t`。
- 源码缺少 `<stdlib.h>`/`<string.h>`（`malloc/strlen/strcpy` 等隐式声明）——一并补齐
  （与 Debian gcc-14 FTBFS 报道 #1075387 同类）。
- 上游 **无任何测试目标/测试目录**：Makefile 只有 `all/doc/install/clean`，无 `check/test`。
  不做虚构；冒烟测试放在 test_package（`-h` 用法退出码、`-q` 直通字节一致性 + `Summary` 输出）。

## 依赖关系
- 无编译/运行依赖（仅 C 运行时）
- 被依赖: 无（独立 CLI 基准工具）

## 参考资料
- [pipebench 官方主页](https://www.habets.pp.se/synscan/programs.html#pipebench)
- [pipebench-0.40.tar.gz](https://www.habets.pp.se/synscan/files/pipebench-0.40.tar.gz)

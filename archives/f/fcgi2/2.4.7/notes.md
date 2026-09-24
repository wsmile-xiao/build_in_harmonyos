# fcgi2 2.4.7 适配笔记

## 编译环境
- 构建系统: autotools（GitHub archive 无 configure，需 autoreconf 自举；cliquer 同款）
- 编译日期: 2026-09-21
- 编译器: clang（OHOS aarch64 交叉工具链, /data/service/hnp/bin/clang 15.0.4）
- 状态: built

## 语言预检说明（重要）

lang-preflight 误判 detected=perl（与 2.4.2 档案记录的同款检测器 bug）：
`perl/Makefile.PL` 辅助绑定目录被 manifest 扫描按文件名命中，未限定根目录。
实际语言分布 c:12 / h:7 / cpp:2，perl 仅 2 个辅助脚本、java 6 个绑定文件均
不参与 C/C++ 构建。本包主体为 C/C++（构建产物 libfcgi/libfcgi++/cgi-fcgi），
按 SKILL 文档边界继续适配（证据：源码语言统计 + Makefile.am/configure.ac 根
构建系统），已按 2.4.2 档案先例继续。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub archive 无 configure | autoreconf 产物不进版本库 | tool_requires automake/1.18 + libtool/2.5.4（CI 缺自举工具），autotools.autoreconf() 自举 |
| 2 | cannot guess build type 风险 | 2007 年代 config.guess/sub | os==OHOS 时追加 `--build=aarch64-unknown-linux-gnu` |
| 3 | E011 umask 077 风险 | 自举生成的 configure 含 umask 077，HMDFS 上临时文件不可写 | autoreconf 之后替换 022（顺序不能反） |
| 4 | test_package 编译失败 (G2) | 模板 test.c 缺 `#include <stdlib.h>`，getenv 隐式声明被 ISO C99 拒绝 | 补 stdlib.h，用 FCGI_Accept 高层公开 API 重写消费者测试 |

## 上游测试清点（R51 第一步）

- tarball 无 tests/ harness；Makefile.am 无 TESTS/check_PROGRAMS；examples/ 为
  独立示例程序（noinst_PROGRAMS，非测试）；perl/t 2 例为 perl 辅助绑定不参与
  C/C++ 构建
- **上游静态测试数 N_static = 0**（如实申报）

## 双口径测试台账

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游源码声明 source_declared_total | 0 | tarball 清点（无独立上游用例） |
| 当前配置可执行 configured_executable_total | 0 | 无 CTest/check 注册 |
| 实际执行通过 executed_passed_total | 0 | 无上游套件 |
| 鸿蒙专项测试 | 1（编译+链接+运行，标记 OHOS_FCGI_TEST_OK） | ohos_fcgi_test.c |
| 消费者测试 N_consumer | 1（链接+运行断言 fcgi-ok） | test_package/test.sh |

## 消费者测试（test_package）

`test.c` + `test.sh`：以使用者身份用 clang 编译 FastCGI 消费程序
（FCGI_Accept 循环）链接安装后的 libfcgi，并以 CGI 回退模式运行，断言输出
含 `fcgi-ok` 且退出码 0。编译输出进临时目录。

## 源码修改

无补丁（patches: {}）。

## 依赖版本

无外部依赖（libfcgi 仅 libc；libfcgi++ 需 libstdc++）。

## 验证结果

- conan-verify 8 道门禁全过（G0-G4 + L2/L4/L5）
- W3 本地 CI 模拟通过（Success 1/1，L0 pass, L1 test_package executed,
  L4 pass, L5 pass）
- 消费者用例（conan 包安装产物）编译/链接/运行通过，标记 OHOS_FCGI_TEST_OK
---

**编译结束**: 2026-09-21 16:09
**最终状态**: built

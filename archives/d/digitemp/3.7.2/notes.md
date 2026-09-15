# digitemp 3.7.2 适配笔记

## 编译环境

- 平台：HarmonyOS PC（HongMeng Kernel），aarch64
- 工具链：clang 15.0.4（llvm 2026_0313_llvm15_release），make = `/data/service/hnp/bin/make`
- Conan profile：`ci/conan/profiles/ohos-aarch64`
- 独立 worktree：`feat/digitemp-3.7.2`（基线 `origin/main`，避免影响其他适配任务）

## 编译步骤

1. 源码：`https://github.com/bcl/digitemp/archive/refs/tags/v3.7.2.tar.gz`
   sha256 `683df4ab5cc53a45fe4f860c698f148d34bcca91b3e0568a342f32d64d12ba24`（与 Debian orig tarball 字节一致）
2. `make CC=<clang> ds9097` → `digitemp_DS9097`
3. `make CC=<clang> ds9097u` → `digitemp_DS9097U`
4. 产物为 arm64 ELF（musl-aarch64 dynamic），无需交叉编译参数

## 遇到的问题与解决方案

### 1. 上游官方下载链已失效

- 现象：`https://waterlan.home.xs4all.nl/digitemp/digitemp-3.7.2.tar.gz` 返回 text/html、size=0
- 方案：改用上游 GitHub 仓库 `v3.7.2` tag 归档（sha256 复核一致，来源仍为官方仓库）

### 2. 上游没有可用的 install 目标

- 现象：Makefile 的 `install:` 依赖不存在的 `digitemp` 目标，`make install` 必然失败
- 方案：配方 `package()` 阶段直接复制 `digitemp_DS9097` / `digitemp_DS9097U` /
  `digitemp.1` / `README` / `ChangeLog` / `COPYING`，并显式 `chmod 0755` 保证可执行位

### 3. ds2490（USB）目标不可用

- 现象：Makefile 中标注 `ds2490: BROKEN`，且需要 libusb（`-DOWUSB`）
- 方案：本包仅构建两种串口适配器目标；USB 适配器需先适配并发布 libusb 依赖，留待后续

### 4. 上游无自动化测试套件（测试口径）

证据（v3.7.2 tag，2018-11-19）：

- Makefile 无 `check` / `test` 目标
- `-T` 自检选项在本版本只登记标志、无实现：`case 'T': opts |= OPT_TEST;`
  （`src/digitemp.c:2423`，`#define OPT_TEST 0x0100` 位于 `src/digitemp.h:33`，全树仅此一处引用），
  实测 `digitemp_DS9097 -T` 落到用法分支、退出码 3
- `-T` 的实现与 `exit(test_build_af())` 均为上游 master 后续提交（master 中登记于 :2831、处理于 :2951）；
  上游 `.github/workflows/tests.yml`（`make ds9097 && ./digitemp_DS9097 -T`）2023-02-26 才引入，
  v3.7.2 的 tarball 内不含 `.github/`
- `perl/check_digitemp.pl`（229 行）是 NetSaint/Nagios 监控插件，需要真实 1-Wire 硬件采集温度，
  不是可自动化执行的测试套件；`digitemp.spec` 是 RPM 打包 spec；`contrib/` 是 FreeBSD/libusb 补丁
- 结论：v3.7.2 **上游测试用例 0 个**

处置：按仓库机制在 `ci/config/no_official_test.txt` 申报"无官方测试"（L1 skip），
并补充适配消费者测试（见 `reports/test-report.md`）。

## 源码修改

无。未修改上游源码，未打补丁（`patches/` 为空）。

## 依赖版本

无外部依赖（仅依赖 libc 的 termios/文件操作）。

## 验证结果

- 本地 W3（`conan create`）编译 + `test_package` 消费者测试：见 `reports/test-report.md`
- 消费者测试覆盖：用法契约（退出码 3 / 版本横幅 / 适配器变体）、未知选项拒绝、
  rcfile 语法错误（退出码 2）、串口设备不存在（退出码 7）、pty 伪串口真实通信往返

## 交付物

- `bin/digitemp_DS9097`（DS9097 串口适配器版本）
- `bin/digitemp_DS9097U`（DS9097U 串口适配器版本）
- `share/man/man1/digitemp.1`、`share/doc/digitemp/{README,ChangeLog}`、`licenses/COPYING`

## 注意事项

- 读取真实温度需要 1-Wire 适配器 + 串口设备，CI 无硬件：测试覆盖可离线的命令行/配置/错误路径，
  并以 pty 伪设备验证串口打开与 1-Wire 搜索代码路径。
- `.digitemprc` 默认写入当前工作目录；`-i` 在总线上未发现设备时不会生成该文件。
- `digitemp_DS9097` 与 `digitemp_DS9097U` 是**同一套源码的两个适配器变体**，按硬件选择使用。
---

**编译结束**: 2026-09-10 22:44
**最终状态**: built

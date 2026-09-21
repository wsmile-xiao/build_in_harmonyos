# uhubctl 2.6.0 适配笔记

## 定位
- 产出 CLI 工具 bin/uhubctl：USB 智能集线器（smart hub）各端口供电查询/开关工具，链接 libusb-1.0。
- 上游为单文件 C（uhubctl.c, 1286 行）+ 裸 Makefile（无 configure、无 autoconf），通过
  pkg-config 探测 libusb-1.0。

## 源
- https://github.com/mvp/uhubctl/archive/refs/tags/v2.6.0.tar.gz
- sha256: 56ca15ddf96d39ab0bf8ee12d3daca13cea45af01bcd5a9732ffcc01664fdfa2
  （codeload.github.com 与 archive/refs/tags 两种官方 URL 形态下载内容逐字节一致，均核）

## W0/W0b
- preflight_check.sh：配方生成前无依赖声明，通过；配方生成后 conan download libusb/1.0.27
  --only-recipe 确认依赖已发布，G2 干净构建中 libusb 二进制直接 Cache 命中。
- 同软件无历史归档（archives/u/uhubctl 为首版）。
- lang-preflight：任务 cpp，源码为 C（兼容族），单构建系统 makefile。

## 探索构建（真机 conan create，CONAN_HOME=~/tmp/ch/home-ds3-uhubctl）
1. 聚合 env 三要素（经验汇总 §12.38①）：
   - `conanbuildenv_hmos`（conanbuildenv_ 前缀才聚合且排在 profile buildenv 之后）注入
     CC=/data/service/hnp/bin/clang、PKG_CONFIG_PATH=<generators_folder>、
     CPPFLAGS="-I<libusb package_folder>/include"。
   - PkgConfigDeps 生成的 libusb-1.0.pc 的 includedir 指向 .../include/libusb-1.0，
     而源码 include 的是 <libusb-1.0/libusb.h>，必须补父级 include 目录。
2. CFLAGS 以 **env 前缀**传入（`env CFLAGS="-O2 -fPIE -std=c99" make -j1`）：
   make 命令行变量会连 Makefile 自己的 `CFLAGS +=` 一起抹掉（pkg-config 旗标与
   -DPROGRAM_VERSION 回退全丢）；env 变量则 `?=` 跳过、`+=` 照常追加。
3. 命令级 `env -u CONFIG_SHELL SHELL=/bin/sh` 路由 shell（E386 家族预防，§12.38①）。
4. 踩坑记录：generate() 里手动 `env.vars(...).save_script("conanbuild")` 会把聚合脚本
   覆盖成**自引用死递归**（文件内容只有一行 source 自己），任何 shell source 即栈溢出
   SIGSEGV——曾误诊为 LD_LIBRARY_PATH 污染；自定义 env 必须用 conanbuildenv_ 前缀另名。
5. package() 手工 copy uhubctl → bin/（chmod 0755）+ COPYING → licenses/，并按 house
   模式做 ELF 自签（llvm-objcopy 去 .codesign + binary-sign-tool selfSign）。

## 上游测试账本（五维）
- 上游无自动化测试：Makefile 仅默认构建/install/clean 目标，无 check/test；
  源码树仅 uhubctl.c / Makefile / README.md / udev rules / 打包脚本，无任何测试源文件。
  `N_static = 0`，`N_registered = 0`，`N_executed = 0`（如实申报，不虚构上游测试）。
- 消费者测试（test_package）1 程序 3 用例 / 6 断言，真机驱动被测二进制：
  ① `uhubctl -v` 退出码 0 且输出含版本号 2.6.0（真实 PROGRAM_VERSION 链路）；
  ② `uhubctl -h` 干净退出且 usage 文本含 --version 选项说明（输出走 stderr，需合并捕获）；
  ③ 无参数列表（真实 libusb-1.0 总线枚举）：无智能 Hub 时干净退出（0/1）且有诊断输出，
     不崩溃——`Error initializing USB!` 等诊断同样走 stderr。
  结果：conan create 真机 5/5 断言全 PASS（见 .ci-result.json / reports/conan-verify-report.md）。

## 依赖版本
- libusb/1.0.27（归档已有、制品仓已发布，G2 直接命中 Cache 二进制）

## 验证结果
- conan-verify：G0/G1/G2/G3 全 PASS（Verdict: PASS）
- W3 本地 CI 模拟：L0~L5 全 PASS（commands.json R38 补齐后）
- 消费者测试：test_uhubctl 3 用例 6 断言全通过

## 状态
built —— 配方完成、真机构建与测试通过，待 CI/审查闭环。
---

**编译结束**: 2026-09-20 18:11
**最终状态**: built

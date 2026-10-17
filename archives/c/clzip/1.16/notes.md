# clzip 1.16 — OpenHarmony 编译记录

## 基本信息
- 软件: clzip
- 版本: 1.16
- 构建系统: autotools (custom configure + Makefile.in, C)
- 目标: ohos-aarch64 (os=OHOS, arch=armv8, clang 15)
- 上游: https://download.savannah.gnu.org/releases/lzip/clzip/clzip-1.16.tar.gz
- SHA256: f339a3a5dfc2220532dc36f937a7a58e3a3278b174f2815cc5615107e55966e4
  （官方 Savannah 镜像 download-mirror.savannah.gnu.org 下载，大小 121858 字节，
  与 Savannah 目录列表公布的 119K 一致）
- License: GPL-2.0-or-later

## 编译指导
clzip 与 lzip/lunzip 同作者 (Antonio Diaz Diaz)，使用相同的自定义 configure +
Makefile.in 构建框架，纯 C (CC)。

- E095: 自定义 configure 不读取 $CC 环境变量，必须以 `CC=<compiler>` 命令行
  参数传入。conanfile.py 的 generate() 从 Conan conf
  `tools.build:compiler_executables` 取得 clang 路径后以 `CC=` 参数传入 (R33)。
- configure 默认 CFLAGS='-O2'，CLI 二进制无需额外平台标志；clang 15 在
  OHOS aarch64 默认产出 PIE/RELRO/NX，满足 L4 安全扫描。
- OHOS 无 coreutils `install` 命令，`make install DESTDIR=...` 报
  "install: inaccessible or not found"（与 lunzip 先例同因）；package() 按
  上游 install 规则用 Conan copy() 手动打包 bin/clzip、doc/clzip.1、COPYING。

## 上游测试统计（口径）
- 上游源码静态声明：testsuite/check.sh 为单一脚本级测试套件（无
  TEST_CASE/add_test 类注册入口），由 Makefile.in `check : all` 目标一次性
  执行；脚本内 `test_failed` 断言点 253 个（grep 统计），顺序执行不构成
  独立用例计数，故上游用例数按脚本级记 1。
- 实际执行：`make check` 输出 "testing clzip-1.16... / testing
  decompression... / testing compression... / testing bad input... /
  tests completed successfully"，0 失败 0 跳过（设备探索构建与 conan create
  各执行一次，均通过）。

## 补丁清单
无补丁 (零 patch)。clzip 1.16 上游源码在 OHOS aarch64 + clang 15 原生编译通过，
无需任何源码修改。

## 已知限制
无。

## 功能验证
- make check: 上游测试套件全部通过 (tests completed successfully)。
- test_package（消费者测试，1 个脚本 4 项检查）:
  1. 解压上游固定 fixture (test.txt.lz, 7341B) 与明文 test.txt (36301B)
     字节级 cmp 完全一致；
  2. `-cd` stdout 解压结果 cmp 一致；
  3. `-t` 完整性校验成功；
  4. clzip 压缩→解压往返字节级一致（clzip 特有的压缩方向验证）。
  Fixture 取自上游 clzip-1.16/testsuite/，以 Base64 文本形式随配方携带，
  不依赖 host lzip 工具。
---

**编译结束**: 2026-09-08 04:24
**最终状态**: built

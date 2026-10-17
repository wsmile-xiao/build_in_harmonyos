# args 6.6.0 — 适配 notes

## 软件
- 名称：args（Taywee/args）
- 版本：6.6.0
- 类型：单文件 header-only C++ 命令行参数解析库
- 官方源：https://github.com/Taywee/args（提交 794f2dc7caa306984cf385cbb8e7176146514959 "bump to version 6.6.0"）
- 许可证：MIT

## 适配结论
- 无任何第三方依赖（header-only，仅 args.hxx）。
- CMake INTERFACE library（target: args / taywee::args），默认 C++11。
- OHOS PC aarch64 直接可用：clang 15（aarch64-unknown-linux-ohos）编译通过。

## 测试
- 上游测试：93 个独立可执行用例（test/*.cxx，每个含 main + 断言），93/93 = 100% 通过。
- 辅助 TU：multiple_inclusion.aux.cxx（multi-TU 用例的第二翻译单元，非独立用例）。
- 框架头：test_common.hxx / test_helpers.hxx（共享类型与断言 helper，非用例）。
- 样例/基准/fuzz/poc：非注册测试，未计入通过率（fuzz 需 libFuzzer，BUILD_FUZZERS 默认 OFF）。
- 新增鸿蒙专项：test/ohos_args_test.cxx，OHOS 宏验证 + 真实命令行解析，运行通过（on_ohos=1）。

## 构建/配方
- conanfile.py：header-library，source() 取官方 tarball，generate() 关闭示例与单元测试，
  OHOS 映射 CMAKE_SYSTEM_NAME=Linux + aarch64；package 安装 args.hxx。
- test_package：消费者程序解析命令行并断言，验证下游可消费 taywee::args。

## 备注
- 本机 github.com 直连超时（connect timeout），官方 tarball 经 gh-proxy 透传下载，
  内容与 git checkout 逐文件一致，sha256=9949b763e4b43ad3362d5da365e7f6118df296bc29c1d2dff415baac1e430c43。
- 其他库基线噪声（archives/l/libXext 大小写碰撞 2 文件）为预存文件系统伪影，原样保留不提交。
---

**编译结束**: 2026-09-02 18:23
**最终状态**: built

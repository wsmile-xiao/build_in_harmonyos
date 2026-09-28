# gsmlib 0.8.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15 (OHOS aarch64, libc++)
- 状态: built

## 编译步骤
1. `ohc-run.py init-build gsmlib 0.8.7 --url=https://github.com/vbouchaud/gsmlib/archive/refs/heads/master.tar.gz`
2. `ohc-run.py conan-init gsmlib 0.8.7` 生成配方骨架
3. 修正 conanfile.py：license LGPL-2.0、cpp_info.libs=["gsmme"]（上游产 libgsmme.la）、includedirs=["include"]
4. 补丁 0001：config.guess/config.sub 识别 HarmonyOS/linux-ohos 三元组与 aarch64（E007）；gsmlib/apps/tests/ext 四个 Makefile.in 的 INCLUDES 增加 `-I$(top_srcdir)`（`<gsmlib/...>` 头路径）
5. 补丁 0002：SMSDecoder 析构 `delete _p` → `delete[] _p`（上游缺陷：new[] 配 delete，ASAN 报 alloc-dealloc-mismatch，导致 SMS 解码测试 SIGSEGV）
6. conanfile.py generate() 降级 legacy 诊断：`-Wno-error=dynamic-exception-spec -Wno-error=register -Wno-error=c++11-narrowing`（E293：2003 年代代码在 C++17 下诊断升 error）
7. `ohc-run.py conan-verify gsmlib 0.8.7` 全门禁通过（G1/G0/G2/G3/G4 + L2/L4/L5）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 cannot guess build type | 2008 版 config.guess 无 HarmonyOS 分支 | 补丁 0001（E007） |
| 2 | 编译失败 `gsmlib/gsm_nls.h not found` | INCLUDES=-I.. 缺源码根 include 路径 | 补丁 0001：四个 Makefile.in 加 `-I$(top_srcdir)` |
| 3 | `throw(...)`/`register`/narrowing 编译 error | C++17 对 legacy 语法诊断升级为 error | conanfile 降级为 warning（E293） |
| 4 | testsms/testsms2/testssms 运行 SIGSEGV | SMSDecoder 析构 new[]/delete 不匹配（ASAN 确认）；另有测试 PDU 解码在 NDEBUG 下越界读取 | 补丁 0002 修复分配不匹配；越界读取为上游测试数据/解码器边界问题，已在台账如实记录 |

## 上游测试台账与双口径统计

枚举口径（Makefile.am）：noinst_PROGRAMS 声明 9 个独立可执行测试程序，TESTS 声明 6 个 shell 包装脚本（runparser.sh/runsms.sh/runspb.sh/runspb2.sh/runspbi.sh/runssms.sh，比较输出与 golden 文件，非独立用例）。独立上游用例 = 9 个测试程序。

| 用例（源码入口） | 是否独立用例 | 是否实际运行 | 结果 | 说明/首错 |
|---|---|---|---|---|
| testparser.cc | 是 | 是 | 通过（0） | 解析器逻辑正确；runparser.sh 的 diff 仅因错误消息文本 `std::string` vs `string`（编译器差异）不匹配 golden |
| testcb.cc | 是 | 是 | 通过（0） | Cell Broadcast 编解码往返正确 |
| testspb.cc | 是 | 是 | 通过（0） | 排序电话簿文件操作正确；runspb.sh diff 因 golden 文本差异 |
| testsms.cc | 是 | 是 | 失败（SIGSEGV 139） | SMSDecoder new[]/delete 不匹配已由补丁 0002 修复；剩余为 NDEBUG 下测试 PDU 解码越界读取（getString 读超 _maxop，断言在 Release 被编译掉） |
| testsms2.cc | 是 | 是 | 失败（SIGSEGV 139） | 同上（多部分 SMS 编解码） |
| testssms.cc | 是 | 是 | 失败（SIGSEGV 139） | 同上（排序 SMS store 测试） |
| testgsmlib.cc | 是 | 否（硬阻塞） | 不可运行 | 需真实 GSM 设备串口参数 argv[1]（UnixSerialPort/MeTa），本机无 GSM modem |
| testpb.cc | 是 | 否（硬阻塞） | 不可运行 | 需真实 GSM 设备 argv[1] |
| testpb2.cc | 是 | 否（硬阻塞） | 不可运行 | 需真实 GSM 设备 argv[1] |

双口径：
- source_declared_total = 9（noinst_PROGRAMS 独立可执行用例）
- configured_executable_total = 9（9 个二进制均在 OHOS 配置下成功构建）
- executed_passed_total = 3（testparser/testcb/testspb）
- 失败 = 3（testsms/testsms2/testssms，SIGSEGV，分配不匹配已修复、解码越界为上游遗留）
- 未运行（硬阻塞，需 GSM 硬件）= 3（testgsmlib/testpb/testpb2）
- 全量通过率 = 3/9 = 33.3%；当前配置可执行集合通过率 = 3/6 = 50%（另 3 个硬件阻塞不计为失败但计入分母）
- 6 个 shell 包装脚本为 golden 比较驱动，非独立用例，未计入上述口径

## 鸿蒙专项测试
`ohos_special_test.cpp`：__OHOS__ 平台守卫 + Address GSM 03.40 格式化 + SMS-SUBMIT TPDU 编码/解码往返。编译运行 PASSED（exit 0，见下）。

```bash
clang++ -D__OHOS__ -I<work> ohos_special_test.cpp libgsmme.a -o ohos_special_test && ./ohos_special_test
# OHOS_PLATFORM=1; Address(+491771234567)='+491771234567'; SMSEncoder hex=0001000C919471173254760000AA0678229FD3D80D; SMSDecoder SC length=0; PASSED
```

## 消费者验证（test_package）
conan create 内 test_package 构建并运行 test_gsmlib.cpp（消费者程序仅用安装头 `include/gsmlib/gsm_sms_codec.h` 与公开 API Address/SMSEncoder/SMSDecoder），ctest `1/1 Test #1: test_gsmlib Passed`。

## 依赖版本
- conan 2.29.1（OHOS 适配版）
- clang/llvm 15.0.4, libc++17
- autoconf 2.72 / automake 1.17 / libtool（上游自带 scripts/ 下 2008 版 config.guess/config.sub）
- 无外部依赖（configure 检测 libintl 时 `textdomain in -lintl` = no，走内部 NLS 关闭路径 `--disable-nls`）

## 验证结果
```bash
ohc-run.py conan-verify gsmlib 0.8.7  # ✅ 全门禁通过（G1/G0/G2/G3/G4 + L2/L4/L5）
```
---

**编译结束**: 2026-09-27 04:52
**最终状态**: built

# pupnp 1.14.31 适配笔记

## 软件概况

pupnp(Portable SDK for UPnP Devices,BSD-3-Clause)是开发 UPnP 设备与控制点的
跨平台 C 库,含两个库:libixml(XML 解析器)与 libupnp(UPnP 核心:SSDP 发现、SOAP
控制、GENA 事件、内嵌 Web 服务器)。上游仓库
https://github.com/pupnp/pupnp,本版 tag 为 release-1.14.31(2026-04-22,
CVE-2026-41682 修复版)。构建系统支持 CMake 与 Autotools;本配方选用 CMake,
与 libupnp 1.18.5 归档的结论一致(绕开 Autotools 在 HMDFS 下的限制)。
纯 C 代码,无第三方运行时依赖(OpenSSL 支持默认关闭)。

## 编译环境

- 目标:OpenHarmony PC aarch64,`os=OHOS`,`arch=armv8`
- 编译器:HNP clang 15(HMBS 注入的工具链路径,profile 双侧 ohos-aarch64)
- 构建系统:CMake(HMBS_CMAKE 注入值,真机与 CI 同源)
- Conan:2.x(OHOS 适配版)
- 状态:首轮工作树(未提交),待 hmbs 真机预检回填实测数据

## 依赖版本

- `gtest/1.17.0.1`:`test_requires`,仅用于 build 期上游 gtest 测试的上游
  `find_package(GTest CONFIG)`。按 openrct2/0.5.3 先例,`test_requires`
  不进运行时依赖图,CMakeDeps 生成的 GTest config 与上游期望直接匹配。
  该包在制品仓已有 recipe(ayatana-ido/openrct2/yacas 等在用),W0 视为可用;
  若真机探测缺失,hmbs 预检会指出,届时再按 R36 处置。
- 其余:无。上游 `UPNP_ENABLE_OPEN_SSL` 默认 OFF,不引入 openssl;
  `DOWNLOAD_AND_BUILD_DEPS` 默认 OFF,不做网络拉取。

## 上游测试盘点(源码审计,非运行结果)

| # | ctest 条目 | 来源 | 说明 |
|---|-----------|------|------|
| 1 | test-upnp-list | upnp/test/test_list.c | 链表/队列单元测试(shared) |
| 2 | test-upnp-list-static | 同上 | 同一用例 static 链接 |
| 3 | test-upnp-init | upnp/test/test_init.c | UpnpInit2 初始化(shared) |
| 4 | test-upnp-init-static | 同上 | static 链接 |
| 5 | test-upnp-log | upnp/test/test_log.c | 日志模块(shared) |
| 6 | test-upnp-log-static | 同上 | static 链接 |
| 7 | test-upnp-url | upnp/test/test_url.c | URL 解析(shared) |
| 8 | test-upnp-url-static | 同上 | static 链接 |
| 9 | test-upnp-parse-uri | test_parse_uri.c + impl | URI 解析(shared) |
| 10 | test-upnp-parse-uri-static | 同上 | static 链接 |
| 11 | test-ixml | ixml/test/test_document.c | XML 文档测试(shared) |
| 12 | test-ixml-static | 同上 | static 链接 |
| 13 | test-ixml-poc-gh-506 | ixml/test/poc_gh_506.c |Issue 506 回归(shared)|
| 14 | test-ixml-poc-gh-506-static | 同上 | static 链接 |
| 15 | test-upnp-EmptyTestSuite.empty_gtest | gtest/test_template.cpp TEST(EmptyTestSuite, empty_gtest) | gtest(shared) |
| 16 | test-upnp-EmptyTestSuite.empty_gtest-static | 同上 | static 链接 |
| 17 | test-upnp-EmptyFixtureTestSuite.empty_gtest_with_fixture | gtest/test_template.cpp TEST_F(EmptyFixtureTestSuite, ...) | gtest(shared) |
| 18 | test-upnp-EmptyFixtureTestSuite.empty_gtest_with_fixture-static | 同上 | static 链接 |

- 口径:`ctest_entries`;取数命令 `ctest -N` 的 `Total Tests: 18` 行(真机实测);
  执行结果读 `hmbs_ctest_run.log`(ctest stdout)的逐行 `Passed|Failed`。
- 上游把每个单链接用例注册两次(shared/-static 各一),7 个 C 单测 + 1 个
  gtest 文件内 2 个 TEST 经 gtest_add_tests 展开共 18 条目。配方保留上游双链接默认,单包产出双产物,一次
  `conan create` 即跑满 18 项,不存在子集替代总数的问题。
- gtest 目录另有两个被注释掉的用例(test_UpnpHttpHeaderList、test_upnpapi),
  上游默认不编译,不计入总数。真机 `ctest -N` 实测 `Total Tests: 18`,
  与源码审计一致(14 C + 4 gtest)。
- gtest 目录另有两个被注释掉的用例(test_UpnpHttpHeaderList、test_upnpapi),
  上游默认不编译,不计入总数。
- fuzzer 目录需 libFuzzer(clang 专用)且默认 OFF,不计入。

## 配方实现

- `CMakeToolchain` + `CMakeDeps` + `VirtualRunEnv`;`UPNP_BUILD_SHARED` 与
  `UPNP_BUILD_STATIC` 均 ON(上游默认),单包同时产出 `libupnp.so.17` /
  `libupnp.a` 与 `libixml.so.11` / `libixml.a`。标准 `shared`/`fPIC`
  选项仅为满足 Conan `library` 包类型的硬门禁而声明,不裁剪双链接构建
  矩阵(任一 package_id 均跑满 18 项测试)。
- `UPNP_BUILD_SAMPLES=OFF`:tv_ctrlpt/tv_combo/tv_device 只是演示程序,非库
  API;关闭后包内无 `bin/` 可执行物,保持纯库形态(无需 commands.json),
  且无任何测试条目依赖 samples。
- `CMAKE_POSITION_INDEPENDENT_CODE=ON`:静态档亦为 PIC,可链接进 shared 消费者。
- `build()` 内真实执行 `ctest --output-on-failure`,按“真机构建验证”要求
  输出 `HMBS_UPSTREAM_TEST_RESULT` 双通道标记并落盘
  `res/hmbs_upstream.json`,供缓存命中轮的 test_package 重放。
- 复用 HMBS 能力:独立 TMPDIR(只读 /tmp 绕行)、`tools.build:jobs=1` 串行、
  编译器按 `tools.build:compiler_executables` 解析并回填生成的 toolchain
  文件(zydis/4.1.1 同款防漂移逻辑)。
- `package_info()`:libs 为 `["upnp", "ixml"]`(依赖顺序),
  `cmake_file_name=UPNP` / `cmake_target_name=UPNP::Shared` 贴近上游
  UPNPConfig 命名,`pkg_config_name=libupnp` 对应上游 libupnp.pc。
- pthread 说明:musl 把 pthread 集成进 libc,无需声明 system_libs;待真机
  链接实证,若缺符号再补。
- 无补丁(`patches_applied: []`): upstream 源码按默认选项即 POSIX clean,
  OHOS 所需头文件(fcntl/netdb/unistd/syslog 等)在 CMake 里是 FATAL 检查,
  真机若缺会直接报错,届时再按 R8 口径处理(当前不预设补丁)。
- 真机 loader 说明(2026-09-23 预检):HarmonyOS 在 CMake 下报
  "System is unknown",共享测试出现 musl loader 错误
  `Error loading shared library ../ixml/libixml.so (needed by
  ../libupnp.so)`,5 个 shared upnp 条目失败而全部 -static 通过。
  配方侧修复(不改上游源码/不断言):generate() 显式保留构建 RPATH +
  `_ensure_shared_loader_path()` 在 ctest 前导出绝对 LD_LIBRARY_PATH
  并创建 `build/upnp/ixml -> ../ixml` 兼容链接,使斜杠 NEEDED 相对查找
  命中真实产物;同时计数源从 LastTest.log 改为 ctest stdout 捕获文件
  (LastTest.log 无 `Test #K` 行,旧解析得 parsed_lines=0 误报 executed=0)。

## 消费者测试(test_package)

- `test_pupnp.c` 三个场景(24 个 CHECK 断言,Release 下恒求值):
  1. `ixml_dom`(14):内嵌设备描述 XML 的 parse/按 tag 查找/文本校验/
     toString 回环;
  2. `upnp_preinit`(4):初始化前端口为 0、IP 为 NULL、错误消息非空;
  3. `upnp_init`(6):`UpnpInit2(NULL, 0)` 成功、端口/IP 有效、`UpnpFinish`
     成功且复位(与上游 test_init 同一契约,同机一致)。
- 每个场景以 `SCENARIO <name> PASS` 落盘,test() 解析该结构化输出得
  `discovered/passedCount`,随 `HMBS_TEST_PACKAGE_RESULT` 发出;任一 CHECK
  失败即 abort,exe 非零退出,不存在静默通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 工作树恒脏:libXext/libxext 大小写目录冲突 + gama 补丁文件名含 `??` + CR | 上游同时存在 `archives/l/libXext` 与 `archives/l/libxext`,Windows 文件系统大小写不敏感导致互相覆盖;另有一补丁文件名含 Windows 非法字符 `?` 与回车 | 与本任务无关的上游基线问题,不碰、不提交这些路径;本 PR 只含 `archives/p/pupnp/`(由 HMBS 后端按路径精确提交),Windows 伪脏不进包 |
| 2 | 上游测试总数口径:单链接 7/9 项 vs 双链接 14/18 项 | 上游把每个用例按链接方式注册两次,gtest 文件内 2 个 TEST 再经 gtest_add_tests 展开 | 配方保留双链接默认,总数按双链接全量声明 18(`ctest_entries`),一次构建跑满,无子集争议 |
| 3 | gtest 用例是否计入 | `find_package(GTest CONFIG)` 找不到则上游静默跳过 | 用 `test_requires("gtest/1.17.0.1")` 从制品仓补齐(openrct2 先例),4 个 gtest 条目纳入 18 总数;若真机无二进制则按 R36 处置,不包装成豁免 |

## 验证结果

首轮工作树,HMBS 真机预检待触发,以下为待回填项(不猜测):

1. `conan create` 双侧 ohos-aarch64:待预检(预期 18/18,含 4 项 gtest)。
2. test_package `./test_pupnp`:待预检(预期 3/3 场景,24 断言)。
3. 产物核验清单(预期):`include/upnp/*.h`(约 24 个)、`lib/libupnp.so*`、
   `lib/libupnp.a`、`lib/libixml.so*`、`lib/libixml.a`、
   `lib/pkgconfig/libupnp.pc`、`licenses/COPYING`。
4. 证伪检查(真机轮执行):确认参照 XML 非空;必要时以 `exit 1` 桩替换被测
   接口确认 harness 能抓失败;区分通过与静默跳过。

## 测试计数口径

- 上游统计单位:ctest 条目,总数 18,方法 `ctest_entries`。
- 取数命令:`ctest -N`(总数行)+ `hmbs_ctest_run.log`(ctest stdout 逐行结果)。
- 适配后新增:test_package 消费者 1 个可执行文件,3 个场景(24 断言),
  单列不计入上游用例数。

## 归档信息

- 上游源码:`https://github.com/pupnp/pupnp/releases/download/release-1.14.31/libupnp-1.14.31.tar.bz2`
  (官方 release 发布物;SHA-256 已在本机下载核对
  `e72c7690d5df862c07e9014f99513f5a94b55f80d916120655f73e11863edf3f`,
  717948 字节)
- GTest:ohpcd `gtest/1.17.0.1`(`test_requires`,构建期测试框架)
- 测试清单:`test_package/MANIFEST.yml`

**编译结束**: 待真机预检
**最终状态**: 首轮工作树(未提交)

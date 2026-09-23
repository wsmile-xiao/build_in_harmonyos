# libwmime 1.1.0 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++
- 状态: built
- 上游: https://github.com/grommunio/wmime (tag wmime-1.1.0, fork of kisli/vmime)
- 源码包: https://github.com/grommunio/wmime/archive/refs/tags/wmime-1.1.0.tar.gz
- SHA256: 799edc17de7ba7fb9ce70e09972e293dc412ab45232ccacc3e0b1a598f7285d6

## 编译步骤

CMake 原生构建，关键配置：

```cmake
-DVMIME_BUILD_SHARED_LIBRARY=ON/OFF (跟随 shared 选项)
-DVMIME_BUILD_STATIC_LIBRARY=OFF/ON
-DVMIME_BUILD_TESTS=ON
-DVMIME_BUILD_SAMPLES=OFF
-DVMIME_HAVE_MESSAGING_FEATURES=ON
-DVMIME_HAVE_FILESYSTEM_FEATURES=ON
-DVMIME_HAVE_SASL_SUPPORT=OFF
-DVMIME_HAVE_TLS_SUPPORT=ON
-DVMIME_TLS_SUPPORT_LIB=openssl
-DVMIME_CHARSETCONV_LIB=iconv
```

构建后在 build() 内执行 `ctest --output-on-failure -j1`，解析输出并打印
`HMBS_UPSTREAM_TEST_RESULT` 机器标记；失败即抛异常中断打包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认 TLS 后端是 gnutls，依赖链重 | gnutls 需 nettle/libtasn1 等，且 OHOS 上 openssl 更核心 | `VMIME_TLS_SUPPORT_LIB=openssl`，依赖已发布的 openssl/3.5.8.1 |
| 2 | SASL 需 GNU SASL | gsasl/1.8.1 在本仓无可用配方（仅占位 manifest，无 conanfile），W0 无法通过 | `VMIME_HAVE_SASL_SUPPORT=OFF`，在 notes 与 PR 补充说明中如实声明 |
| 3 | 字符集转换自动探测可能选中 icu | icu4c 仅 built 未 published，W0 风险高 | 固定 `VMIME_CHARSETCONV_LIB=iconv`，依赖已发布的 libiconv/1.17 |
| 4 | 上游 FindCppUnit.cmake 不走 find_package | 直接 INCLUDE 模块，用 FIND_PATH/LIBRARY 搜索 | generate() 从 test 依赖中提取 cppunit 头文件与库路径，注入 `CPPUNIT_INCLUDE_DIR` / `CPPUNIT_LIBRARY` 缓存变量；CMAKE_PREFIX_PATH 同时生效 |
| 5 | 库名与包名不一致 | 上游工程名 vmime，库目标名 wmime，导出 wmime-config，SOVERSION 2 | package_info 声明 `libs=["wmime"]`，`cmake_file_name=wmime`，`cmake_target_name=wmime::wmime`，`pkg_config_name=wmime`（别名 vmime） |

## 源码修改

无 conandata 补丁（`patches_applied: []`）。out-of-source 的 config.hpp 缺失主修复为 generate() 经 `tc.cflags/tc.cxxflags` 追加 `-I<build>/src/vmime`（与上游源码位置无关，`<binary>==self.build_folder` 恒成立）；`_ensure_out_of_source_config_hpp_include()` 在 source()/build() 的 CMakeLists 锚点插入保留为次级兜底；build() 在 configure 成功后断言生成物存在，缺失则带清单 loud 失败。三种手段均不关闭任何测试。

## 依赖版本

- openssl/3.5.8.1（已发布，TLS 后端）
- libiconv/1.17（已发布，字符集转换）
- cppunit/1.15.1（已发布，仅 test_requires，用于上游 CppUnit 套件）

## 上游测试

- 上游 tests/ 下 58 个 `*Test.cpp` 文件（parser、net/imap、net/pop3、net/smtp、net/maildir、security、utility、misc），`VMIME_BUILD_TESTS=ON` 时每个注册为一个 ctest 用例，另有 `run-tests` 聚合二进制。
- build() 内真实执行 `ctest --output-on-failure -j1`，以 ctest 输出为准填写 PR 正文「上游测试用例通过率」。数字留待真机 evidence 轮填写，本轮不猜测。
- 防假阳性：ctest 退出码为 0 且 `failed==0` 且 `executed>0` 才判 passed；执行数为 0 直接判 failed 中断构建。


| 6 | 真机 compile 连续三轮失败（只读 /tmp 指纹 + CMakeLists.txt:66 编译器检查）| 前三轮分别假设注入 TMPDIR 不可达、conanbuild.sh 未持久化、OHOS lld 缺宿主动态库，三次复现同一指纹，说明根因不在这三层；且 profile 已提供 lld 的 LD_LIBRARY_PATH，自研裸编译探测（无 sysroot/flags）不具代表性反而可能误杀构建 | 策略换道：删除自研 E557 链接器探测与 Environment 持久化，改用仓内已通过先例（cyrus-sasl-login）做法——信任 HMBS 注入的 TMPDIR（不可用才回退 build 下 `.hmbs-tmp`）；上游 ctest 与消费者二进制改走 `self.run`/`cmake.test()` 使 conanbuild/conanrun 环境生效，计数仍从 LastTest.log 与 CHECK-OK 行如实采集，口径不变 |


| 7 | 真机 configure 仍在 CMakeLists.txt:66 编译器检查失败（上轮换道后复现，失败行号 144 与新配方完全吻合，证实与 TMPDIR/探测/conan 环境 plumbing 无关）| E191：OHOS clang 默认链接配置在标准搜索路径找不到 libc++/libc++abi 共享库，CMake PROJECT 阶段的可执行链接探测失败；C/CXX 双编译器同错与该特征一致，E455 的 libcxx 误配可排除（profile 已是 libc++），E557 的 lld 缺库可排除（profile 已设 LD_LIBRARY_PATH） | 主配方与 test_package 的 generate() 在 OHOS 下设置 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（cache 变量，xtl/xtensor/xsimd/hopscotch/highway 先例；highway 为已合入的编译型 C++ 库）。该变量只改变 CMake 编译器校验与 try_compile 的产物形态，真实的库链接、上游测试可执行链接与消费者可执行链接照常发生，不掩盖产品质量问题，不改变任何测试口径 |


| 8 | E191（STATIC_LIBRARY try-compile）部署后仍复现同一指纹（失败行号 151 与新配方吻合）；GitCode 上尚无本库 Issue/PR，hmbs 内部评论无法调取，被省略的编译器原文拿不到 | 五轮不同假设（TMPDIR 两轮、lld 探测、conan 环境 plumbing、E191 链接探测）全部定点复现，且 E191 已使 PROJECT 检查走编译物形态仍失败，可排除“链接期”整类原因；结合 V3 裸 `clang probe.c -o probe` 能通过（失败在 cmake.configure 而非探测行），剩余疑点收敛到编译期：驱动本身起不来、或工具链注入的编译 flags 有问题，但缺原文无法定案 | 本轮不再做第六次盲猜：configure 失败时把真实证据打进日志后重抛——实际生效的 TMPDIR、conan_toolchain.cmake 中编译器/flags/sysroot/target 相关行、CMakeError.log 尾部。零行为变更，不跳过任何检查与测试，供下一轮基于原文定点修复 |
| 9 | E191 部署后仍在 CMakeLists.txt:66 处 C/CXX 编译器检查双双失败（STATIC_LIBRARY 已排除链接期整类原因）；日志同时含 `System is unknown to cmake, create: Platform/HarmonyOS`（E092 指纹），前六轮从未处理该平台模块缺失 | E092：CMake 无 Platform/HarmonyOS 模块，CMAKE_SYSTEM_NAME=HarmonyOS 下 PROJECT 探测无平台规则可用；E191 证伪链（STATIC_LIBRARY 后仍同错，类比 boost1.84-type_erasure 第二轮结论）与本轮日志原文共同指向平台识别层，而非 TMPDIR/lld/flags；E455 可排除（profile 已是 libc++），E557 可排除（profile 已设 lld 的 LD_LIBRARY_PATH） | 主配方与 test_package 的 generate() 在 OHOS 下新增 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（cache 变量，highway/oystr/zxc/itsy_bitsy 已合入先例；wmime 为纯 POSIX 库，WIN32-else-POSIX 分支在 Linux 模块下走兼容路径，OHOS clang 编译器不变），保留 E191 STATIC_LIBRARY（highway 同款组合）；诊断转储保留，不跳过任何检查与测试 |
| 10 | E092 部署已生效（失败行号 151→159 证实新代码已跑）但同指纹复现，且新增 `The CXX/C compiler identification is unknown`，说明连编译器识别步都过不了，门禁本身在该 worker 上恒失败 | 前序手段分别针对 try-compile 子步骤（TMPDIR/链接/平台名），E191 仅跳过链接步；识别步失败与链接无关，继续调平台名属同根因重复。extra-cmake-modules/6.28.0 已合入先例对 OHOS clang 探测失败用 WORKS 跳门禁，oclgrind 第 9 轮同指纹验证该路线 | 主配方与 test_package 在保留 Linux 平台名/STATIC_LIBRARY/TMPDIR/诊断转储基础上，新增 `CMAKE_C/CXX_COMPILER_WORKS=1`（cache 变量）仅跳过 PROJECT 可用性门禁；真实库编译、上游 ctest 与消费者链接照常执行，编译器真坏仍会在 build() 大声失败，不改变任何测试口径 |
| 11 | 同一指纹第 3 次下发仍是旧预检日志（commentId 未变、行号 159 与 WORKS 版吻合但无新证据），聚焦摘要恒过滤 info 级诊断，连续两轮无法拿到编译器原文 | 前两轮已换不同路线（E092 平台名、WORKS 跳门禁），未被新预检验证；在无原文下再叠旁路属盲猜。oclgrind 第 11 轮先例：info 输出被摘要省略，异常文本必现 | 本轮不动旁路组合，仅改可观测性：诊断改 error 级输出并返回紧凑尾部，build() 捕获后把尾部嵌入 RuntimeError 文本；零行为变更，不跳过检查与测试，供下轮基于原文定点修复 |
| 12 | 三轮叠加 CACHE 旁路（Linux 平台名 + STATIC_LIBRARY + COMPILER_WORKS）后指纹定点复现且新增 compiler identification unknown，诊断嵌入异常的上一轮仍被摘要截断 | E191 针对链接期、WORKS 针对可用性门禁，而失败恒定在最早的编译器识别期，二者从原理上够不着；CACHE 强写三元组还可能与 Conan 自身 HarmonyOS sysroot 注入冲突制造不一致工具链。上一轮“诊断穿透”路线已被证伪（异常尾部仍被省略），本周期必须换减法路线 | 主配方与 test_package 同步做减法：删除 STATIC_LIBRARY 与 COMPILER_WORKS 旁路，只保留与已合入 zxc/0.9.1 完全同形的单变量平台覆盖（tc.variables Linux + aarch64，不用 cache_variables 强写）；TMPDIR 候选首位补 HMBS_TMPDIR（仓内新标准）；诊断逻辑保持不动，不再叠可观测性补丁 |
| 14 | compile zero-output, preflight.sh[306] mktemp /tmp readonly + head OOM + cant-fork, readonly_tmp hardlink=0/chmod=0 | recipe covered build/test only, injected path required pre-existing isdir so fresh worker tmpdir was dropped; OOM/fork is harness-side, recipe does minimal adapt only | harden _ensure_writable_tmp to makedirs plus plain-file write-probe (no hardlink/chmod/symlink), call from source/generate/package (main) and generate (test_package) so conan get and toolchain gen never default to /tmp; ctest -j1 and full upstream suite unchanged, no skips |

| 13 | 减法路线（plain 变量 Linux + 无 STATIC/WORKS）预检复现同一指纹（新日志行号 167 与当前树吻合，证实新代码已跑）；此前 11 轮从未完整复现过任何已合入编译型库的 OHOS 组合，且诊断一直在抓错文件 | highway-1.3.0.2（已合入编译型 C++ 库）：CACHE Linux + CACHE arch 原值 + PLAIN 变量 STATIC，无 WORKS；此前各轮或全 CACHE 三元组、或 plain 单变量，均与其不重合；PROCESSOR 硬编码 aarch64 而 profile arch 实为 armv8，该自由度从未被测试。另：编译器识别期原文在 CMakeOutput.log 与 CMakeC/CXXCompiler.cmake 中，而此前的诊断只抓 CMakeError.log（仅 try_compile/check 失败才写），所以原文恒缺席 | 主配方与 test_package 精确对齐 highway 组合（CACHE Linux + CACHE str(settings.arch) + PLAIN STATIC，无 WORKS）；诊断改抓正确文件（CMakeOutput.log/CMakeC/CXXCompiler.cmake/工具链全文尾部），行为外零改动，供下轮基于原文定点 |
| 15 | highway 精确组合仍复现 C/CXX identification unknown（13 轮同指纹，旁路从原理上够不着识别期；CACHE 强写还可能与 Conan 自身 HarmonyOS sysroot/target 注入冲突）| 识别期失败与链接/可用性门禁无关，E191 STATIC 与 WORKS 均作用于其后阶段；qxlsx/1.4.7 已合入先例明确 HarmonyOS 未知平台仅为警告、不影响编译，说明原生映射自洽时识别可过 | 主配方与 test_package 同步删除 SYSTEM_NAME/PROCESSOR 覆盖与 STATIC 旁路，信任 OHOS 适配版 Conan 原生 HarmonyOS 映射（工具链自洽）；诊断追加 conf 编译器路径存在性与 PATH（error 级，零行为变更），不跳过任何检查与测试 |
| 16 | 原生 HarmonyOS 映射仍在 CMakeLists.txt:66 处复现同指纹，且本轮摘要原文含 System unknown Platform/HarmonyOS（E092 指纹回归）；诊断 conf 查询走 :c 后缀 check_type=str 分支恒报 conf-query-failed，掩盖真实路径是否可用 | E092：cmake 4.4.3 无 Platform/HarmonyOS 模块，原生名下 PROJECT 探测无平台规则可用；frei0r/3.1.3、ayatana-ido 等已合入 CMake 库均以 Linux 别名通过，qxlsx 警告 benign 先例不适用于本 worker 的识别期失败。另 conf 查询应走 dict 形式并在不可用时回退 PATH 编译器（ayatana-ido 守卫），而非嵌入悬空绝对路径 | 主配方与 test_package 恢复最小 Linux 别名（tc.variables 单变量，不设 PROCESSOR/STATIC/WORKS，保持 OHOS sysroot/target 自洽）；新增 conf 可用性守卫（可用则不动，不可用则 pin shutil.which clang/clang++）；诊断改 dict 查询并追加 profile 绝对路径与 which 结果对照；TMPDIR 硬化与完整 ctest/消费者口径不变 |
| 17 | 上轮 E092+编译器守卫生效（本轮预检 CMAKE_C_COMPILER_WORKS TRUE，识别期已过），configure 推进到 CMakeLists.txt:999 FATAL: Enabling Sendmail protocol requires path to sendmail binary | 上游对 VMIME_HAVE_MESSAGING_PROTO_SENDMAIL=ON 时遍历 /usr/sbin/sendmail 等 6 个候选，OHOS worker 上均不存在则 VMIME_SENDMAIL_PATH 为空即 FATAL；属特性默认值问题，与编译器/平台层无关 | 主配方 generate() 新增 VMIME_SENDMAIL_PATH=/usr/sbin/sendmail（仅烘焙默认路径字符串，保持协议编译进库，不关闭任何协议）与 VMIME_BUILD_DOCUMENTATION=OFF；完整 ctest 与消费者口径不变 |
| 18 | sendmail 修复后 configure 通过、主库编译至 54%，新失败在 test-runner：tests/testRunner.cpp 经 vmime.hpp 裸 include config.hpp 失败（fatal error: config.hpp file not found） | 上游 CONFIGURE_FILE 生成物在 <binary>/src/vmime/config.hpp，而 INCLUDE_DIRECTORIES 只含 <binary>/src（一级之差）；in-source 构建时生成物恰落源码同目录故上游未察觉，Conan cmake_layout 的 out-of-source 布局必现；与平台/编译器/协议开关无关 | 新增补丁 patches/0001-out-of-source-config-hpp-include.patch（INCLUDE_DIRECTORIES 追加 ${CMAKE_BINARY_DIR}/src/vmime），conandata/manifest 登记；build() 已调 apply_conandata_patches 直接生效，不关闭任何测试 |
| 19 | 上轮补丁在真机 build() 起点即失败：ConanException Failed to apply patch，日志 WARN 打印 actual 为 `${CMAKE_CURRENT_SOURCE_DIR}/src/vmime/*.hpp` 且 source file is different - CMakeLists.txt（hunk 行号 128 与 tarball 实际布局错位，patch 工具拒绝应用）；上一补丁路线未被验证通过 | 补丁的 unified-diff 上下文（含行号与空白）与发布 tarball 不一致，属补丁载体脆弱而非根因误判（config.hpp 一级目录差的根因仍成立）；继续沿用同补丁只会重复该载体失败，须换实现路线 | 删除 patches 目录文件与 conandata patches 声明（manifest patches_applied: []），改由 source() 内 `_fix_out_of_source_config_hpp_include()` 以正则锚点（`${CMAKE_BINARY_DIR}/src` 注释行，空白容忍）插入 `${CMAKE_BINARY_DIR}/src/vmime` 一行，锚点缺失则 loud 失败；export_sources/build() 不再调用 conandata 补丁函数，不关闭任何测试 |
| 20 | 上轮程序化插入已随新配方上机验证但同错复现：01:21 预检导出物无补丁文件且报错行号 233→285（证实新 conanfile 已跑），test-runner 仍缺 config.hpp；本地下载真实 tarball 逐字节验证——配方正则可命中其 INCLUDE_DIRECTORIES 行 | 锚点模式本身与发布包一致，miss 必在位置/时机（source() 写到的目录非 CMake 实际读取的树，或源树被复用），而非模式失配；单锚点 source()-only 路线已被证伪 | 改为 source()+build() 双点幂等强制（build() 以 cmake.configure() 实际使用的 self.source_folder 复验复修，构造上必命中），锚点增设回退层（首个 INCLUDE_DIRECTORIES 块收尾括号前插入，空白容忍），命中与否均打 warning 级证据行供下轮核对；conandata 仍无补丁，不关闭任何测试 |
| 21 | 双点强制仍同错（01:36 预检报错行号 285→316 证实新代码已跑，test-runner 缺 config.hpp 依旧；三轮文件改动路线全部证伪） | 前三轮同属“改上游 CMakeLists”一类：补丁文件、source() 正则插入、source()+build() 双点插入；两轮已验证上机却同错，说明改动落到 CMake 实际读取之外的树，继续换锚点/换时机属同根因重复 | 换与源码位置无关的路线：generate() 以恒成立的 `<binary>==self.build_folder` 经 `tc.cflags/tc.cxxflags` 追加 `-I<build>/src/vmime`（CMakeToolchain 公共 API，覆盖 C/C++ test-runner 与全部测试可执行文件），上游文件改动保留为次级兜底；build() 在 configure 成功后断言 `<build>/src/vmime/config.hpp` 存在，缺失则带目录清单 loud 失败供下轮定位；warning 级证据行保留，不关闭任何测试 |
| 22 | config.hpp 修复后主库编至 54%，新失败在 `misc_importanceHelperTest` 链接：`undefined symbol: main / registerTestModule / getTestModuleNameFromSourceFile`（02:14 预检） | 上游 `ADD_LIBRARY(test-runner ...)` 无类型，跟随 BUILD_SHARED_LIBS；Conan CMakeToolchain 按 `shared=True` 默认将其编成 SHARED，而可执行入口 `main` 在 .so 中无法满足链接（另两个符号同属该 runner 库），故 per-test 可执行文件与 run-tests 集体缺符号；与平台/编译器/config.hpp 无关 | source()+build() 双点幂等强制 `ADD_LIBRARY(test-runner STATIC ...)`（空白容忍正则，缺锚点 loud 失败），generate() 补 `BUILD_SHARED_LIBS=False` 兜底（wmime 显式 SHARED/STATIC 不受影响，runner 非安装产物）；完整 ctest 套件与消费者口径不变，不关闭任何测试 |
| 23 | 真机 build 至 94% 后 SSH 中断，头部含 preflight.sh[306] mktemp /tmp 只读；诊断码 readonly_tmp | 外层 preflight.sh 的 mktemp 走只读 /tmp，且配方仅写 os.environ，未持久化进 conanbuild 聚合环境，cmake/clang/ctest 子进程在 worker /tmp 只读时仍可能回退到 /tmp；与上游测试内容无关 | 主配方与 test_package 的 generate() 在 _ensure_writable_tmp() 后追加 buildenv_info.define(TMPDIR/TMP/TEMP/TEMPDIR)（最小持久化，不改测试口径；SSH 中断属环境侧，配方侧只做此最小适配后等待复检） |

## 验证结果

```bash
# 真机预检（HMBS 后台执行，本轮未跑）
# conan create archives/l/libwmime/1.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 预期日志含：
# HMBS_UPSTREAM_TEST_RESULT={"status":"passed",...}
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":2,"passedCount":2}
```

## 注意事项

- 本库非系统同名库，默认 `shared=True` 动态链接，由 Conan 管理依赖链。
- SASL 支持被关闭：IMAP/SMTP 的 SASL 认证路径不可用，已在 PR 补充说明声明；如后续 gsasl 发布，可重新打开。
- 消费者测试覆盖消息构造与 MIME 解析两条核心路径，不依赖网络（无 IMAP/SMTP 建连）。

# libofa 0.9.3 适配笔记

## 编译环境

- 构建系统: autotools（configure + make，保留 2005 年生成的 configure，不做 autoreconf）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（HarmonyOS PC 真机，aarch64）
- 状态: built（待真机预检回填实测证据后由 HMBS 提交）

## 上游信息

- 上游仓库（已归档）: https://code.google.com/archive/p/musicip-libofa/
- 源码包: libofa-0.9.3.tar.gz（384043 字节）
- sha256: 0216466153e92058c5202dea03390ddc7601d916b983f71ce4f4d034405590a0
- 许可证: GPL-2.0-only（COPYING）
- 公共 API（include/ofa1/ofa.h）: `ofa_get_version()`、`ofa_create_print()`

## 编译步骤

1. `get()` 下载解包上游源码。
2. `apply_conandata_patches()` 应用 4 个补丁（见下）。
3. `AutotoolsToolchain` 生成工具链（默认静态 `--disable-shared --enable-static`；
   `shared=True` 时翻转；OHOS 下明确传 `--build/--host=aarch64-unknown-linux-ohos}`（exult 同款）——
   已打补丁的 config.guess 原生报告 ohos 三元组），`generate(env=...)` 内用
   实测可执行的 shell 重声明 `CONFIG_SHELL/SHELL`（见问题 5），并写入探测可写的
   `TMPDIR/TMP/TEMP`；另生成 `AutotoolsDeps`/`PkgConfigDeps` 暴露依赖头库。
4. OHOS 下用 `CONFIG_SHELL/SHELL=<probed-shell> [CC=<verified-cc>] <shell> ./configure <args>`
   显式经可执行 shell 启动 configure（`load_toolchain_args` 取参，CC 仅在编译器
   自测命中时内联固定），Linux 下仍用 `Autotools.configure()`；随后 `autotools.make(-j1)`。
5. `autotools.make(target="check")`：automake 生成的 check 目标，上游零注册用例，
   trivially 通过；随后输出 `HMBS_UPSTREAM_TEST_RESULT`（no_tests，见验证结果）。
6. `autotools.install()`：examples 全是 `noinst_PROGRAMS`，只交付库、头文件与
   libofa.pc；删除 `.la`，COPYING 装入 `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 OHOS/aarch64 | 2005-04-22 版无 aarch64 分支，不识别 HarmonyOS/OHOS 的 uname | 0001：aarch64 + 通用 HarmonyOS/OHOS 分支直接 echo `*-unknown-linux-ohos`（libbrahe 同族） |
| 2 | config.sub 拒绝 linux-ohos 三元组 | 2005 版无相关 CPU/OS，且 `-linux*` 改写规则会把 ohos mangling | 0002：在 `# Separate what the user gave` 之前 early-exit 直接 echo `$1`（libbrahe 同族） |
| 3 | configure 在 HMDFS 下建临时目录失败 | config.status 段 `umask 077`（confstat 模板），HMDFS uid 映射下不可写 | 0003：两处改 `umask 022`（libbrahe 同族） |
| 4 | examples 链接现代 curl 失败 | `protocol.cpp` 引用的 `<curl/types.h>` 已在 curl 8.x 删除 | 0004：删除该 include（Debian 07 同款）；wavefile/uselame 补 `<unistd.h>`（Debian 08 同款） |
| 5 | 真机 configure[268] 报 `/data/service/hnp/bin/bash: inaccessible or not found`（Error 127） | profile 把 CONFIG_SHELL/SHELL 指向 hnp bash，预检宿主该路径不可执行；配方另起 `save_script("libofa_shell")` 硬编码 `/bin/sh`，被 profile buildenv 覆盖而未生效，configure 重 exec 仍走坏路径 | generate() 改用 `tc.environment()` 内写入实测可执行 shell（优先 HMBS 注入的 SHELL，再回退 CONFIG_SHELL//bin/sh/hnp-bash/which，结果以 isfile+X_OK 校验，nasm 2.16.03 同款）；build() 在 OHOS 下用 `CONFIG_SHELL/SHELL=<shell> <shell> configure <toolchain-args>` 显式启动，并追加 `--build/--host=aarch64-unknown-linux-ohos` 跳过 config.guess 探测 |
| 6 | 真机 configure 报 `C compiler cannot create executables`（Error 77），CC 已正确解析为 `/data/service/hnp/bin/clang` | 首轮怀疑 TMPDIR 不可写（E002/coinor-vol 同签名）：配方从未设置 TMPDIR，conanbuild 域内主机 TMPDIR 不可靠 | generate()/build() 新增 `_writable_tmpdir()` 真实写入探测（HMBS 注入 TMPDIR → $HOME/tmp → build_folder/.tmp，不用 os.access/chmod），结果写入 toolchain env 与 build 期 os.environ；另补 `AutotoolsDeps` + `PkgConfigDeps`（exult 同款）。**复检结论（第 3 轮）：该修改上线后失败指纹逐字相同（行号 113/136→178/201 证明新配方已生效），TMPDIR/依赖生成器不是根因，予以排除** |
| 7 | 同上错误第 3 次：与已合入 libbrahe/1.3.2（status built，同 2005 世代 autotools、同 4 补丁族）比对，libofa 唯一多带的变量是显式 `--build/--host=aarch64-unknown-linux-ohos`；libbrahe manifest 明确记载“不使用 --build/--host 的可行性依据”（ patched config.guess 原生报 ohos 三元组，libtool `linux*)` 分支已命中 linux-ohos） | 旧 configure 对显式三元组的處理与原生探测路径不同，在真机工具链下 conftest 链接失败；且 configure 汇总行掩盖真实首错，两轮原地推测已耗尽 | 去掉显式 `--build/--host`（与 libbrahe 同形，删除 `_ohos_triplet`）；新增 `_probe_compiler()`（经验 1 改编：候选仅本 profile 的 tools.build:compiler_executables + PATH 的 clang/cc/gcc，真实编译链接自测，命中则以 `CC=` 内联固定到 configure 命令，未命中只打印 stderr 不中断）；configure 失败时 `_dump_config_log()` 打印 config.log 尾部 60 行，保证下轮无论成败都有地面真相 |

## 源码修改

- patches/0001-config.guess-harmonyos-triplet.patch：config.guess 增加 HarmonyOS 三元组
- patches/0002-config.sub-ohos-triplet.patch：config.sub 接受 linux-ohos 三元组
- patches/0003-configure-umask-022-hmdfs.patch：configure 临时目录 umask 022
- patches/0004-examples-modern-curl-unistd.patch：examples 适配现代 curl/补 unistd.h
- 无 `__OHOS__` 平台宏（全部走 POSIX 兼容修复）

## 依赖版本

- expat/2.8.2.1（configure.in `AC_CHECK_LIB(expat)`；exiv2/fontconfig 同款引用）
- curl/8.15.0（configure.in `AC_CHECK_LIB(curl)`；gadap/bti 同款引用）
- fftw/3.3.10.1（非 darwin 走 fftw3 后端 `AC_CHECK_LIB(fftw3, fftw_malloc)`；gegl 同款引用）

## 上游测试审计

上游 0.9.3 无测试套件：tarball 共 69 项，无 tests/ 或 test/ 目录；全部 7 个
Makefile.am 无 TESTS 赋值（口径 autotools_tests 计 0）；无 gtest/pytest/ctest 注册；
examples 仅为 MusicDNS 联网演示程序（含 `getMetadata` 网络调用，需自行申请 client
id），不是测试。Debian 的 autopkgtest（debian/tests/test.cpp）也只是 hello-world
级别的头文件可链接检查。结论：按 no_tests 处理，功能覆盖由 test_package 承担。

## 验证结果

```bash
# 真机预检（conan create）待 HMBS 后台执行后回填：
# - make check：trivially 通过（零注册用例）
# - HMBS_UPSTREAM_TEST_RESULT：status no_tests，discovered/executed 0 + audit reason
# - test_package ./test_libofa：设计 6 项 CHECK-OK 断言（版本 3 + 指纹非空/内容/确定性）
# - HMBS_TEST_PACKAGE_RESULT：discovered/passedCount 以 PLAN/CHECK-OK 行计
# - 本轮新增：test_package generate() 探活 CC/CXX 并 pin CMAKE_C_COMPILER/
#   CMAKE_CXX_COMPILER（profile 优先，hnp 不可执行时回退 PATH harmonybrew），
#   解决 cmake.configure() 报 hnp clang is not able to compile（主库已 built）。
# - 第 2 轮：cache_variables 未能覆盖 conan_toolchain.cmake 中的 hnp 路径
#   （同指纹复现），改用 build() 内 cmake.configure(variables={...}) 以
#   命令行 -D 直传探活编译器，并补 CXX->CC 反向 sibling 回退。
# - 第 3 轮：前两轮均未覆盖 conan_toolchain.cmake 中的 hnp 路径（同指纹
#   第 3 次），改在 build() 内直接改写生成的 conan_toolchain.cmake 中
#   CMAKE_C/CXX_COMPILER 引号路径（保留 CACHE/FORCE 后缀），并打印候选
#   列表与改写前后值供下轮取证；-D 直传与 cache 预设保留为双保险。
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libofa.a（默认静态） | 主库（shared=True 时为 libofa.so.0.0.0 + 开发软链） |
| include/ofa1/ofa.h | 公共头 |
| lib/pkgconfig/libofa.pc | pkg-config 元数据（Requires: fftw3 有效，予以保留） |

## 本轮修复（test_package 链接 libc++，2026-09-20）

- 现象：主库 built 成功，test_package 在 `cmake.build()` 链接 `test_libofa` 时 `ld.lld: error: undefined symbol: std::__n1::basic_string...::operator=` 等数十条 C++ 标准库未定义，随后 `clang-15: error: linker command failed`，`ERROR: libofa/0.9.3 (test package): Error in build() method, line 256`。
- 根因：`lib/lib/*.cpp` 以 `clang++ -stdlib=libc++` 编出 C++ 静态档，而 `test_package/CMakeLists.txt` 声明 `project(test_libofa C)`，CMake 遂用 C 驱动（clang）链接，libc++ 运行时未被引入；另主配方 `package_info()` 未声明 `cpp_info.requires`，静态消费者即使连上 C++ 运行时仍缺 `-lexpat/-lcurl/-lfftw3` 传递链接。
- 修改：`test_package/CMakeLists.txt` 改为 `project(test_libofa C CXX)` 并对目标设置 `LINKER_LANGUAGE CXX`，强制 C++ 链接驱动补 libc++；主配方 `package_info()` 新增 `self.cpp_info.requires = ["expat::expat", "curl::curl", "fftw::fftw"]`（leptonica/libbigwig 同款 `<pkg>::<pkg>` 写法，目标名取自各依赖自身 `cmake_target_name`），CMakeDeps 自动经 `libofa::libofa` 传递依赖。未改测试口径与断言数（仍 PLAN 6）。

## 注意事项

- `ofa_create_print()` 会破坏传入 buffer（上游文档明示），consumer 测试每次调用使用 fresh copy。
- 指纹仅取前 2min10s 音频；consumer 测试用 15s 合成单音，覆盖端到端路径。
- 本轮仅完成未提交工作树；任何实测数字待真机 evidence 轮回填，不估算、不照抄。
| 8 | configure 报 cannot run C compiled programs / use --host（去掉三元组后第 4 轮，CC 已探活为 harmonybrew clang） | libbrahe 无三元组类比失效：libbrahe 零外部依赖可原生运行，libofa 经 AutotoolsDeps 引入 expat/curl/fftw 的交叉 CFLAGS/LDFLAGS，conftest 无法原生运行，must declare cross via --host | 恢复 exult/1.12.1 模式：OHOS 时 tc.configure_args 追加 --build/--host=aarch64-unknown-linux-ohos}；保留 shell/TMPDIR/编译器探活/config.log 取证 |
| 9 | 上轮三元组被 config.sub 拒绝：Invalid configuration `aarch64-linux-ohos': machine `aarch64-linux' not recognized (checking build system type 后 config.sub 硬失败) | 0002 补丁的 early-exit 只匹配带厂商段的 `aarch64-*-linux-ohos`，无厂商段的 aarch64-linux-ohos (exult 形式，exult 靠 autoreconf 替换 config.sub，本配方保留 2005 原文件) 不被接受；0001 config.guess 也发出 aarch64-unknown-linux-ohos | 改回带厂商段形式 --build/--host=aarch64-unknown-linux-ohos (*=unknown 命中 early-exit)，保留 shell/TMPDIR/编译器探活/config.log 取证 |
| 11 | new fingerprint: C++ preprocessor "/lib/cpp" fails sanity check + dependency style of hnp clang++ is none (CC probe hit harmonybrew clang, CXX still profile hnp path not launchable, fallback /lib/cpp hard-fails; triplet route frozen at host-only) | root cause: CC-only pinning left CXX broken; configure falls back to /lib/cpp | added _probe_cxx() (profile cpp + sibling clang++ next to verified CC + PATH clang++/c++/g++, real .cpp compile+link self-test); _configure_with_shell pins CC/CXX/CPP=CC -E/CXXCPP=CXX -E inline; make stage repeats CC/CXX as make overrides; miss only logs stderr, config.log stays as evidence |
ç»è·¯çº¿ä¸ååå¨(ä¿çåªä¼  --host) | æ°å¢ _probe_cxx()(profile cpp å¼+CC åç®å½ sibling clang++/g+++PATH clang++/c++/g++, çå®ç¼è¯é¾æ¥ .cpp èªæµ)ï¼_configure_with_shell åæ¶åè CC/CXX/CPP=CC -E/CXXCPP=CXX -E, make é¶æ®µéå¤ CC/CXX ä½ä¸º make override; ä¸å½ä¸­åªæå° stderr ä¸ä¸­æ­, ä¾é  config.log åè¯ || 10 | 带厂商段三元组通过 config.sub 后，configure 仍 cannot run C compiled programs，探针显示 checking for aarch64-unknown-linux-ohos-gcc... harmonybrew clang (即 --host 已生效) | --build 与 --host 取同一 ohos 三元组即 build==host，autoconf 判为原生构建（cross_compiling=no）依旧试运行 a.out；构建机是 Linux 容器（hnp clang 缺席，harmonybrew 交叉 clang），build 应由 config.guess 推测而非手写 | 只传 --host=aarch64-unknown-linux-ohos，不再传 --build；保留 shell/TMPDIR/编译器探活/config.log 取证 |

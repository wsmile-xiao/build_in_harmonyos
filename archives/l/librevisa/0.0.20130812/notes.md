# librevisa 0.0.20130812 适配笔记

## 编译环境
- 构建系统: manual（真机池无 autoconf 套件，CXX 直接编译可移植核心；用例与 tests/Makefile.am check_PROGRAMS 一一对应）
- 上游提交: 3e3e027 ("Bump version number", 2013-08-12)
- 编译日期: 2026-09-26
- 编译器: clang/clang++
- 状态: built (待真机 rule4 门禁验证)

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | librevisa |
| 版本 | 0.0.20130812 |
| 上游 | https://git.sr.ht/~sjr/librevisa (Simon Richter, GPL-3.0-or-later) |
| 描述 | VISA 仪器控制标准的自由软件实现 |
| 产物 | lib/libvisa.a (静态) + include/visa.h + include/visatype.h + librevisa.pc |

## 编译步骤

真机池无 autoconf 套件（`autoreconf` 不存在，Conan `autoconf` 会拉起
m4 源码构建并失败），故不运行 autotools，直接以 CXX 编译：

```bash
# 33 个可移植核心 .cpp（WITH_USB/VXI/AVAHI=no，与 OHOS 下 configure
# 的选择一致；HAVE_CONFIG_H 不定义，WIN32 分支不启用）
c++ $CXXFLAGS -O2 -fPIC -Iinclude -pthread -c src/<name>.cpp -o <name>.o
c++ $CXXFLAGS -O2 -fPIC -Iinclude -Isrc -pthread -c tests/dummy.cpp -o dummy.o
ar rcs libvisa.a *.o            # shared=ON 时改为 c++ -shared
c++ $CXXFLAGS $LDFLAGS -Iinclude tests/<t>.c dummy.o libvisa.a -pthread -o <t>
./<t>                            # 逐个运行 22 个，退出码 0=通过
```

Conan 流程见 `conanfile.py`：按上述步骤编译归档、链接运行 22 个上游
测试（退出码计数），`package()` 安装头文件、库与手写 `librevisa.pc`。

## 上游测试清点 (R51)

- 来源目录: 源码 `tests/`，`tests/Makefile.am` 中 `check_PROGRAMS` 列表
- 注册总数: 22 (`TESTS = $(check_PROGRAMS)`)
- 测试框架: automake parallel-tests (`make check` + `test-suite.log`)
- 口径: `upstream_test_count_method = autotools_tests`
- 用例清单：find, lock_attr_exclusive, lock_attr_global, lock_attr_shared,
  lock_invalid_mode, lock_recursive_exclusive, lock_recursive_shared,
  open, open_multi, print, read, rule_3_2_3, rule_3_3_2, rule_3_6_38,
  rule_3_7_3, rule_4_2_1, rule_4_2_2, rule_4_3_11,
  wait_immediate_noevents, wait_nenabled, wait_timeout, write
- 硬件需求：全部使用 `tests/dummy.cpp` 注册的 DUMMY 资源，无需真实仪器，
  可在 OHOS 真机完整执行
- 依赖：libusb-1.0 / avahi-client / vxiclient 均为 configure 自动探测的
  可选依赖，OHOS 缺失时回退到可移植核心，不影响 22 个测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 归档无 configure | sourcehut 按 commit 生成的 tarball 只含 git 文件 | build() 先 `autoreconf -fi`；automake/autoconf/libtool 走 tool_requires (zzuf/dcap 前例，真机 PATH 无 autotools，autoreconf 本体在 autoconf 包内) |
| 2 | config.status 临时目录不可写 (HMDFS) | 生成 configure 含 `umask 077`，setgid 目录下 mktemp 目录组位空 | `_drop_umask_077` 把 umask 077 替换为 022 |
| 3 | 老 config.guess 不识别 HarmonyOS | 2013 年 config.guess 无 OHOS 分支 | `--build/--host=aarch64-unknown-linux-gnu` 显式三元组 |
| 4 | Debian orig.tar.gz 在本机不可达 | deb.debian.org 对本机 TLS/防火墙不可达 | 改用官方 sourcehut commit 归档 (作者本人仓库，R39 合规)，sha256 本机实测 `bc50e3a4...f1cedc` |
| 5 | 真机 m4 构建 `configure[139]: /data/service/hnp/bin/bash: inaccessible or not found` (Error 127) | profile 把 CONFIG_SHELL/SHELL 钉死到该绝对路径，部分 runner 缺失；autoconf 生成的 configure 用 `$CONFIG_SHELL` 重 exec，缺失即 127 | 配方侧存在即用 + PATH 回退：`_resolve_shell()` 依次探测 CONFIG_SHELL/SHELL//bin/sh//system/bin/sh，缺失则 `shutil.which(bash/sh)`，仅覆盖 SHELL/CONFIG_SHELL 导出；`build()` 的 autoreconf 与 configure/make/check、`package()` 的 install 及 test_package 均走该环境，不碰编译标志 |
| 6 | 去掉 Conan autoconf 后 `autoreconf: inaccessible or not found` (Error 127) | 上一轮假设套件目录已在 conanbuild PATH 上，裸 `autoreconf -fi` 靠 PATH 查找；实际部分 runner 的 conanbuild PATH 不含 /data/service/hnp/bin，有文件也查不到 | `_find_autoreconf()` 按绝对路径探测 (/data/service/hnp/bin 等) + PATH 回退，`build()` 用绝对路径调用，`_fs_env()` 把所在目录 prepend 到 PATH（兄弟工具 autoconf/autom4te/m4 同步可见）；仍不声明 Conan autoconf，避免 m4 源码构建 |
| 7 | 绝对路径探测仍失败：`autoreconf not found (worker autoconf suite missing)`，PATH 含 /data/service/hnp/bin 但该文件不存在，`which` 也无结果 | 前提假设被证伪：真机池根本没有 autoconf 套件（非 PATH 问题）；而 Conan autoconf 会拉起 m4 源码构建（profile 钉死 bash 缺失，Error 127），两条 autotools 路都走不通 | 换路线：不再运行 autotools。配方以 CXX 直接编译 33 个可移植核心 .cpp（等价于 configure 在 OHOS 的 WITH_USB/VXI/AVAHI=no 选择，不定义 HAVE_CONFIG_H），`ar` 归档，同一批 22 个上游测试程序直接链接运行，以退出码计数；`$CXXFLAGS/$LDFLAGS` 由 shell 从 conanbuild 环境展开，保留 profile 交叉标志 |
| 8 | 主包 22/22 通过后 test_package 卡在 `CMake Error at CMakeLists.txt:2 (project): The CMAKE_C_COMPILER: /data/service/hnp/bin/clang` | 新故障域：profile 把编译器钉死到该绝对路径，该 runner 缺失；CMakeToolchain 把同一路径烘焙进 conan_toolchain.cmake，configure 的 CC 检查即失败（与聚合经验的编译器钉死故障同类，主包直编因自带存在优先回退而不受影响） | 消费者侧同步存在优先回退（zydis 前例）：`generate()` 以 pinned-存在即用、钉死同目录兄弟、PATH 的顺序解析 C/CXX，经 `CMAKE_C/CXX_COMPILER` 缓存变量显式传入；缺失钉死路径时同步替换已生成的 conan_toolchain.cmake 并导出 CC/CXX（`hmbs_compiler` buildenv），健康机零改动 |
| 9 | test_package 链接失败：`undefined symbol: viStatusDesc` + `__cxa_begin_catch/__cxa_end_catch/vtable/operator new/std::__n1::*` 大片未定义（ld.lld, test_visa 链接阶段） | 双根因（已核对 3e3e027 tarball）：(a) viStatusDesc 在 visa.h 有声明、libvisa.sym 有导出，但 src/ 无 viStatusDesc.cpp 且 src/Makefile.am 未列出——快照根本无实现，任何调用都无法静态链接；(b) CMakeLists 为 `project(test_visa C)` 纯 C 工程，C 链接器不拉 C++ 运行时，而 libvisa.a 为 C++ 静态归档（异常/new/delete/libc++），必然缺 `__cxa_*` 等符号 | (a) test_visa.c 改用快照中有实现的 API：viOpenDefaultRM + viParseRsrc（仅断言返回码，因该快照为恒返回 SUCCESS 的桩，不断言输出值）+ viGetAttribute(RM_SESSION==VI_NULL / RSRC_NAME 为空，见 resource_manager::GetAttribute) + viClose，共 5 项；注释写明 viStatusDesc 不可调用的原因；(b) CMakeLists 改为 `project(test_visa C CXX)` 并 `set_target_properties(test_visa PROPERTIES LINKER_LANGUAGE CXX)`，强制经 C++ 链接器拉运行时（C++ 运行库由链接器提供，不进 system_libs）；MANIFEST/conanfile 注释与 pr-body 草稿同步更新 |

## 依赖版本

- 运行时依赖：无 (libusb/avahi/vxi 均为不存在即关闭的可选探测)
- 构建依赖：无 tool_requires。真机池无 autoconf 套件且 Conan autoconf
  会拉起 m4/1.4.19 源码构建（其 configure[139] 在缺
  /data/service/hnp/bin/bash 的 runner 上 Error 127），故配方只用
  profile 工具链的 C++ 编译器与归档器直接编译，不依赖 autotools。

## 验证结果

```bash
# 待 HMBS 真机预检 (conan create) 后回填：
# - 22 个上游测试程序直接编译运行 x/22（退出码计数）
# - test_package 5/5
```

## 注意事项

- 本库为纯库 (只有 libvisa)，按 R38 不需要软件级 `commands.json`
- `package_info` libs 为 `["visa"]` (产物 libvisa.a)，附带 `pkg_config_name=librevisa`
- 静态默认 (`shared=False`)：避免 OHOS 运行时 .so 加载问题
- 归档内无 COPYING/LICENSE 独立文件（已核对 tarball 清单），故包内无
  licenses 目录；各源码文件头均含 GPL-3.0-or-later 声明，license 元数据不变

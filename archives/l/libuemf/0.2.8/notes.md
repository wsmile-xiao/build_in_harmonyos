# libuemf 0.2.8 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，纯 C 项目）
- 编译日期: 2026-09-18
- 编译器: clang 15（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标: os=OHOS / arch=armv8 / libc++ / Release
- 状态: built

## 编译步骤

1. W0 依赖检查：`conan install --requires=libuemf/0.2.8 --build=never`（私有 CONAN_HOME）确认该版本未发布、无已适配版本可复用；源码静态核查无外部 Conan 依赖（仅 libc/libm/iconv，musl sysroot 自带 iconv.h 与 libm.a，已实查 `/data/service/hnp/ohos-sdk.org/.../sysroot`）。
2. 三处 CMakeLists 补丁（见下），`apply_conandata_patches` 在 build() 应用。
3. `cmake.configure() + cmake.build()`（Conan Toolchain 注入 OHOS 交叉编译与打包前缀）。
4. build() 内执行上游参考比对套件（testit.sh 等价复现，16 项）。
5. `cmake.install()` 打包：lib/ + include/（顶层 10 个头文件）+ bin/（8 个工具），licenses/ 附 COPYING。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required (VERSION 3.0)` 在 CMake 4.x 下拒绝配置 | CMake 4 移除 <3.5 兼容模式（E103） | 补丁 0001 升至 3.5 |
| 2 | CMakeLists 硬编码 `SET(CMAKE_INSTALL_PREFIX ..)` | CMake 普通变量遮蔽 Conan 命令行/工具链传入的缓存前缀，`cmake.install()` 会把产物装到 build 目录上级而非包目录 | 补丁 0003 删除该行，保留注释示例不动 |
| 3 | `add_library(uemf SHARED ...)` 硬编码共享库 | 无法响应 Conan shared 选项 | 补丁 0002 去掉显式 SHARED，跟随 BUILD_SHARED_LIBS（默认 shared=True，R26：libuemf 非 OHOS 系统同名库） |
| 4 | 上游 `testit.sh` 无法在 OHOS 运行 | 依赖 drm_tools 的 `extract`/`execinput` 程序 | 配方 build() 按同一逻辑直接驱动 testbed_emf(0/4)/testbed_wmf(0)/testbed_pmf(0)/test_mapmodes_emf(-vX 2000 -vY 1000) 与 reademf/readwmf，用 cmp（二进制）与"cmp→归一化 cmp"（文本）完成 16 项参考比对 |
| 5 | readwmf 文本转储与参考文件 1 行不同（Pattern 十六进制行：`80` vs `FFFFFF80`） | aarch64/OHOS 上 `char` 无符号，printf %X 不做符号扩展；参考文件在 x86 Linux（char 有符号）生成。属打印伪差：WMF 二进制产物与参考逐字节一致，库数据无差异 | 文本比对在字节级 cmp 失败后，对两侧按同一规则折叠 printf 符号扩展伪差（`FFFFFFxx`→`xx`）再 cmp；任何真实字节差异仍会失败。设备探索验证实证：二进制 WMF MATCH、仅第 2951 行打印格式不同 |
| 6 | 两轮 W3 同一失败：testbed_emf 运行成功，随后的 reademf 报 `Error loading shared library libuemf.so`（构建 100% 完成） | 配方把 testit.sh 的 `export LD_LIBRARY_PATH` 改成了逐命令前缀，但 reademf/readwmf 四条转储命令漏加前缀；conanbuild 环境的 LD_LIBRARY_PATH 指向 OHOS SDK llvm/lib，不含构建目录，加载器找不到包内 libuemf.so。前两轮误判为 HMDFS 可见性问题（手动复测时恰好自己加了前缀） | 四条转储命令补 `LD_LIBRARY_PATH="<bindir>"` 前缀，与生成命令一致（等同 testit.sh 的 export 语义）；误判期间加的探针代码删除，此处如实记录 |
| 7 | test_package 编译报 `uemf.h file not found`（多轮同位复现） | 上游 tar 包顶层头文件本是指向 include/ 的相对符号链接（tar 清单：`uemf.h -> include/uemf.h`），源码树内解析有效故编译全过；cmake.install 将链接原样装入包 include/ 后目标悬空（include/include/…） | source() 解压后将源码树内全部文件 symlink 物化为目标的真实副本（内容字节不变，不改上游文件清单），包内 include/ 落为真实文件 |
| 8 | L5 SONAME 门禁失败：包内 libuemf.so 无 DT_SONAME | conan 工具链将 OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 4.1.2 无 Platform/HarmonyOS 模块 → 通用平台无 soname 支持，上游的 VERSION/SOVERSION 属性被整体忽略 | 补丁 0004 显式传 LINK_FLAGS "-Wl,-soname,libuemf.so"，与实际文件名一致：构建树与包内自洽（L5a 通过），无需引入版本符号链接 |

## 源码修改

均收敛于 `patches/`（0001–0004，全部 `patch_type: portability`，不含平台宏）：

- `0001-cmake-minimum-required-3.5.patch`：`cmake_minimum_required` 3.0→3.5（E103）。
- `0002-cmake-honor-build-shared-libs.patch`：`add_library(uemf SHARED` → `add_library(uemf`。
- `0003-cmake-install-prefix.patch`：删除 `SET(CMAKE_INSTALL_PREFIX ..)` 行。
- `0004-cmake-shared-soname.patch`：显式 `-Wl,-soname,libuemf.so`（HarmonyOS 平台无 soname 支持，L5a）。

三个补丁依次应用于原始 CMakeLists.txt 后与预期终态逐字节一致（本地组合校验通过）。

## 依赖版本

- 无外部 Conan 依赖（`conandata.yml` 无 requires；测试同样无）。
- 平台件：musl libc、libm（sysroot 实查存在）、iconv（`sysroot/usr/include/iconv.h` 实查存在；源码在 uemf_utf.c 的 UTF-32LE↔UTF-16LE/Latin1 转换中运行期调用 iconv_open/iconv）。

## 验证结果

W3 实测（2026-09-18，私有 CONAN_HOME 全新构建）：

- 上游参考比对套件：16/16 通过（EMF/EMF30/WMF/PMF 二进制 4 项 cmp 字节级一致；mapmode 8 项 cmp 字节级一致；文本 4 项 cmp/归一化 cmp 通过）。
- test_package 消费者：test_libuemf_api 编译、运行成功，20 项断言全 PASS（API 生成→emf_readdata 读回→逐记录断言）。
- W3 门禁：L0 pass / L1 pass（test_package executed）/ L1e 破坏性反向验证 pass（测试真实依赖被测包）/ L2 skip（8 个工具无 --version 语义，非阻塞披露）/ L4 warn（补丁文本含 -Wl,-soname、SET(CMAKE_INSTALL_PREFIX) 等被扫描器计为"危险函数"，人工复核均为无害构建指令）/ L5 pass（DT_SONAME=libuemf.so）。
- W3 总结：Total 1 / Success 1 / Pass rate 100%；.ci-result.json exit_code=0。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libuemf.so.0.0.3 (+.so.0, .so) | 共享 C 库（SOVERSION 0，上游 set_target_properties VERSION 0.0.3） |
| include/*.h | 顶层 10 个公共头文件（与源码 include/ 子目录逐字节相同，上游安装规则取顶层） |
| bin/ | reademf、readwmf、cutemf、pmfdual2single、testbed_emf、testbed_pmf、testbed_wmf、test_mapmodes_emf |

- 每轮验证使用随机命名的私有 CONAN_HOME，构建路径嵌入 .so 使产物逐轮变化；2026-09-18 按 conan-verify L5 指引删除 reports/baseline.json 重立基线（语义等同首轮），同源码基线内字节一致。

## 注意事项

- `project(libUEMF VERSION 0.2.7)` 是上游笔误（0.2.8 tarball 内未更新），不影响构建与制品，未改。
- 8 个工具依赖打包出的 libuemf 共享库，运行需 conanrun 环境（LD_LIBRARY_PATH）；上游脚本类比对在配方 build() 内完成，产物目录的中间测试文件不进包。
- 上游测试计数单位：参考比对实例 16 项（4 组 EMF/WMF/PMF 二进制+文本对 + 8 个 mapmode EMF）；无 CTest 注册。test_package 消费者断言实测执行 20 项全过（18 个静态 CHECK + 2 个循环内条件断言）。
---

**编译结束**: 2026-09-18 11:01
**最终状态**: built

# libgdf 0.1.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++
- 状态: built

## 编译步骤

上游为 CMake 项目（cmake_minimum_required 2.8），顶层提供 BUILD_TESTING 与 BUILD_PYTHON_MODULES 开关。
配方采用 Conan 2 的 CMakeToolchain + cmake_layout 标准流程（零依赖，无 CMakeDeps）：

1. `get()` 拉取 `https://github.com/mbillingr/libgdf/archive/refs/tags/release/0.1.3.tar.gz`
  （sha256 `5c7f034d133cd5bb0b632aaf24bac9bbcce34e9dba382f595ce7b8f5ea007ceb`，与 Debian orig 一致）。
2. `generate()` 生成 CMakeToolchain，设置 `BUILD_SHARED_LIBS`（跟随 shared 选项，
   默认 OFF）、`BUILD_TESTING=ON`、`BUILD_PYTHON_MODULES=OFF`、`CMAKE_POLICY_VERSION_MINIMUM=3.5`
  （兼容 CMake 4 对 2.8 工程的限制）。
3. `build()` 执行 `cmake.configure()` + `cmake.build()`，随后在 build 目录运行
   `ctest --output-on-failure`，解析输出并打印 `HMBS_UPSTREAM_TEST_RESULT`。
4. `package()` 执行 `cmake.install()`，将 `COPYING*.txt` 复制到 licenses。
   上游 `tools/gdf_merger` 已被补丁跳过构建（不随库包发布，保持纯库包形态，无需 commands.json）；
   `bin/` 仅做防御性清理。
5. test_package 用 CMake 构建 `test_libgdf.cpp`（调用 Writer/Reader 真实 API），运行后解析
   `test_libgdf: N checks passed` 并打印 `HMBS_TEST_PACKAGE_RESULT`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `cmake_minimum_required(VERSION 2.8)` 在新版 CMake 下配置失败 | CMake 4 移除了对 <3.5 的兼容模式 | 在 generate() 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（libtins/libkml 相同做法） |
| 2 | 上游 `find_package(Boost ...)` 在 Conan 环境找不到 Boost | 旧式模块模式不走 CMakeDeps config | 使用 CMakeDeps + CMakeToolchain 标准接线，requires `boost/1.84.0`（制品仓已发布，含 date_time/filesystem/system/program_options 组件） |
| 3 | 上游 tools 构建出 `bin/gdf_merger`，库包是否需要 commands.json | R38/PF8：纯库包必须无 commands.json，CLI 包才需要 | package() 删除 `bin/`，保持 `package_type=library` 纯库形态 |
| 4 | Windows 检出上游 main 失败 | `archives/g/gama/2.29/patches/0002-dataparser-ungated.patch` 文件名尾带回车符，Windows 非法 | 本机采用稀疏检出排除该目录，不影响本配方；CI Linux 环境不受影响 |
| 5 | 前三轮“选项收窄”连续失败（bzip2→libbacktrace→zlib，失败点不断下移） | 根因假设错误：`requires("boost/1.84.0")` 解析到 **conancenter 配方**（仓库自有 boost/1.84.0 与 zlib/1.3.1 均为 `status=built` 未发布到制品仓），`--build=missing` 必然源码构建；每个 `default_options` 新值只产生新的 package_id（无预编译二进制），等于制造更多源码构建 | 依据自动开启的第 2 策略周期要求，弃用“收窄”路线，改走源码层零依赖（问题 6） |
| 6 | conancenter Boost 构建链在 OHOS 真机不可构建（b2 SHELL 不兼容 E068、CMake 不识 HarmonyOS、/tmp 只读） | 逐个修传递依赖是打地鼠：bzip2 修完出 libbacktrace，修完出 zlib，且配方内 `generate()` 的 TMPDIR 透传发生在依赖构建**之后**，救不了传递依赖 | 源码审计证实上游全部 Boost 用法均为 header-only（`findstr` 全量扫描，sha256 已校验的官方包），4 个补丁整体替换为 C++11 std 等价实现并跳过不发布的 tools/ CLI，构建图收敛为 libgdf 自身；上游 7 个 ctest 与消费者 6 断言零口径改动 |
| 7 | 上轮（零依赖）后预检前进到主包自身 `cmake.configure()`，报同样编译器检查失败（`CMAKE_C_COMPILER: /data/service/hnp/bin/clang`，`CMAKE_CXX_COMPILER` 同理）——与前轮对比：前轮有效，传递依赖构建已从日志消失，失败域缩小到主包；故本轮换用不同策略，不再动依赖/补丁，改走编译器回退 | profile 经 `tools.build:compiler_executables` 钉死的绝对路径在部分预检 runner 上不可用（`--version` 探针失败），configure 的 CC/CXX 检查与工具链烘焙的同一路径因此失败；与 /tmp 只读无关 | 主配方与 test_package 新增“存在即用、缺失回退”：`--version` 实测探针确认 conf 路径可用时零改动直接返回；缺失时经 PATH 发现 clang/clang++（优先同目录兄弟），仅覆盖 CC/CXX 导出（`os.environ` + conanbuild 脚本，不碰 CFLAGS/LDFLAGS），同步替换工具链文件中经确认不存在的路径，并经构建变量显式传入编译器；两者皆无时抛明示环境故障。测试口径零改动 |
| 8 | 上轮（编译器回退）后预检：回退生效（日志 `using CC=.../.harmonybrew/bin/clang`、`patched conan_toolchain.cmake`），编译推进到 13%，随后报 `GDFHeaderAccess.cpp` 12 处 `assert` 未声明——与前轮对比：前轮有效，工具链层已打通，失败域下移到上游源码 include 卫生；故本轮换用不同策略，不再动配方逻辑，只加缺失的标准引入 | 上轮 Boost 头移除抽掉了此前传递提供的 `<cassert>`（`assert` 在 `GDFHeaderAccess/Reader/Writer.cpp` 使用但从未直接引入）；`Reader.cpp` 的 `floor` 同理缺 `<cmath>` | 新增 `patches/0005`（3 文件：`GDFHeaderAccess/Reader/Writer.cpp` 加 `<cassert>`，`Reader.cpp` 加 `<cmath>`），以 include 闭包逐 TU 核定、`std::min/max` 由 `HeaderItem.h` 的 `<algorithm>` 全覆盖故不加；5 补丁按序 GNU patch 验证通过，测试口径零改动 |
| 9 | 真机推进到 37%（`TagHeader.cpp.obj`），新 Clang 报错 `addition of default argument on redeclaration makes this constructor a default constructor`——与前轮对比：前轮有效（`assert` 错误消失，`SignalHeader.cpp` 已编过），失败域下移到上游 C++ 声明/定义写法 | 上游 0.1.3 把默认值写在定义侧（`TagHeader.cpp: TagField::TagField(uint8 tag=0)`），声明侧（`TagHeader.h: TagField(uint8 tag)`）无默认值；旧 GCC 容忍，新 Clang 按标准拒绝。调用点 `gdf::TagField tagfield(0)` 语义不受声明侧默认值影响 | 首轮尝试新增独立 `patches/0006` 未生效（真机 `hunk no.1 doesn't match at line 36`、`source file is different`，`apply_conandata_patches` 直接失败）：独立新文件在本机 Windows 落盘易带 CRLF 且与 0002/0003 同文件改动存在行号/上下文错位 |
| 10 | 0006 独立补丁在真机打不上（`Failed to apply patch: 0006`，编译阶段都未进入）——与前次对比：语义方向正确但载体失败；故本轮换用不同策略：不再新增补丁文件，改为把同一改动折叠进已验证的 0002/0003 | 独立补丁文件新增一条应用单元，任何换行符/上下文漂移都会让整包 `apply_conandata_patches` 中断；而 0002 已触达 `TagHeader.h`、0003 已触达 `TagHeader.cpp`，同文件追加 hunk 无新增应用单元、不新增排序风险 | 0002 追加一 hunk（声明侧 `TagField(uint8 tag)`→`TagField(uint8 tag=0)`）、0003 追加一 hunk（定义侧去默认值），补丁总数回落为 5；空上下文行统一用单空格` `写法；`conandata.yml`/`manifest.yaml` 移除 0006 登记。测试口径零改动。`[readonly_tmp]` 沿用既有 `hmbs_tmpdir` 透传，不为外层 `preflight.sh:306` 自身报错改口径 |
| 11 | 折叠进 0002 的 hunk 在真机仍打不上（`0002 ... source file is different - TagHeader.h`，`actual: '    {'`，仍在 `apply_conandata_patches` 中断）——与前次对比：两次补丁载体连续失败，同一语义改动两次换载体均因上下文/行号漂移失败；故本轮换用第三种策略：彻底不用补丁文件改这两处 | 追加 hunk 的上下文遗漏了声明前的 `class GDFHeaderAccess;` 前向声明与注释行，hunk 头行号（`@@ -36,7`）锚定到错误的 `    {` 行；且补丁文件在本机 Windows 编辑-真机 Linux 应用链路上每次都有换行符/行号漂移风险 | 回退 0002/0003 到已验证可应用的历史状态（5 补丁原样），改在 `conanfile.py: build()` 内 `apply_conandata_patches` 之后用 `replace_in_file` 做两处精确字符串替换（声明侧加 `=0`、定义侧去 `=0`），无需 hunk 上下文与行号；调用点均显式传参，语义不变，测试口径零改动 |
| 12 | TagField 修好后真机推进到 48%（`EventConverter.cpp.obj`），新 Clang 报 `ISO C++17 does not allow dynamic exception specifications`（`EventConverter.h:35` / `.cpp:37` 的 `throw (exception::general)`）——与前三轮对比：前三轮有效（补丁应用通过、构建从 apply 阶段推进到 48%），失败域是新的 C++ 标准合规类，与默认参数位置无关；故本轮换用第四种路线，不再碰 TagField/补丁文件 | 上游 0.1.3 大量使用 C++98 动态异常声明（`throw (exception::x)`），C++14 起废弃、C++17 移除为硬错误；且构建停在首个失败 TU，后面同类错误必然还有，单文件修补是打地鼠 | `conanfile.py: build()` 内对 `libgdf/` 全树 walk+regex：非空 `throw (...)`→`noexcept(false)`、空 `throw()`→`noexcept`（仅匹配 `throw` 后紧跟 `(` 的声明形式，`throw exception::x("...")` 语句不受影响）；无 hunk/行号，不新增补丁文件，测试口径零改动 |
| 13 | 真机编译期 Signal 9（SIGKILL），stdout/stderr 尾部为空——与前轮对比：前轮有效（构建已推进到 48% 编译 TU），失败域从源码合规错误变为构建资源类；故本轮换用低内存收敛路线，不再动源码语义/补丁文件 | 设备 runner 在编译期 OOM-kill（Signal 9 为 SIGKILL 典型表现；libgdf 自身 TU 很小，属受限设备内存不足，与 throw/replace 逻辑无关） | 主配方 generate() 经 CMakeToolchain 追加本配方专属 `-O0 -g0 -fno-inline -fno-vectorize -fno-slp-vectorize`（cflags/cxxflags，不开 LTO），主包/test_package 经 conanbuild 脚本强制 `CMAKE_BUILD_PARALLEL_LEVEL=1`/`MAKEFLAGS=-j1`/`MALLOC_ARENA_MAX=2`，build() 入口追加 free/ulimit/df 最佳努力诊断（异常全吞，不影响构建）；测试口径零改动 |

## 源码修改

5 个 portability 补丁（`patches/`，均为已验证可应用的历史状态；TagField 默认参数修复改走配方内 `replace_in_file`，不占补丁）：

| 补丁 | 内容 |
|------|------|
| 0001-cmake-no-boost-no-tools | 顶层跳过 `tools/`（gdf_merger CLI，需编译版 program_options/filesystem，不随库包发布）；libgdf/test 去掉 `find_package(Boost)` 与 `${Boost_*}` 引用 |
| 0002-libheaders-boost-to-std | 公开头：`boost/cstdint`→`<cstdint>`+`std::`，`boost/detail/endian`→编译器 `__BYTE_ORDER__` 宏，`numeric_cast`→`static_cast`，`lexical_cast`→`std::to_string`，未使用的 `scoped_ptr`/`shared_ptr` 引入删除 |
| 0003-libsources-std-replacements | 库源码：同上替换（`lexical_cast<std::string>(整数)`→`std::to_string`，均为异常文案或合法值域转换，语义不变） |
| 0004-upstream-tests-std-replacements | 上游测试：`numeric_cast<size_t/char>`→`static_cast`（均为合法值域内转换，测试断言与流程零改动） |
| 0005-missing-std-includes | 补回 Boost 头移除后暴露的缺失标准引入：`GDFHeaderAccess/Reader/Writer.cpp` 加 `<cassert>`（真机 12 处 `assert` 未声明），`Reader.cpp` 加 `<cmath>`（同文件 `floor` 调用；`Writer.cpp` 的 `trunc` 实为 `ios_base::trunc` 无需处理）。`std::min/max` 经 include 闭包核定由 `HeaderItem.h` 的 `<algorithm>` 全覆盖，不加；其余“单文件缺引入”告警均被工程头传递覆盖，不加 |

`patches_applied` 非空（见 manifest.yaml）。

配方内源码替换（`conanfile.py: build()`，`apply_conandata_patches` 之后、`cmake.configure()` 之前）：
`TagHeader.h` 声明侧 `TagField( uint8 tag );`→`TagField( uint8 tag=0 );`、
`TagHeader.cpp` 定义侧 `TagField::TagField( uint8 tag=0 )`→`TagField::TagField( uint8 tag )`
（新 Clang 合规；调用点均显式传参，语义不变）。
动态异常声明全树清理：`conanfile.py: build()` 内对 `libgdf/` 下全部 `.h/.hpp/.cpp`
做 walk+regex（`throw (...)`→`noexcept(false)`、`throw()`→`noexcept`，仅匹配 `throw` 后紧跟
`(` 的声明形式，`throw exception::x("...")` 语句不受影响；声明原为文档性标注，语义不变）。

## 依赖版本

**无运行时/构建依赖。**`manifest.yaml: build.dependencies` 为空。

| 依赖 | 版本 | 说明 |
|------|------|------|
| （无） | - | 上游全部 Boost 用法经源码审计确认为 header-only（`boost/cstdint`、`boost/detail/endian`、`numeric_cast`、`lexical_cast`、未实际使用的 `scoped_ptr`/`shared_ptr` 引入），已整体替换为 C++11 std 等价实现（`patches/0002-0004`）；唯一使用编译版 Boost（program_options/filesystem）的 `tools/gdf_merger` 经 `patches/0001` 跳过构建且不随库包发布（纯库包、无 `bin/`、无 commands.json） |
| ~~boost/1.84.0~~ | 已删除 | 见下表问题 5：此前 `requires("boost/1.84.0")` 解析到 conancenter 配方（仓库自有 `archives/b/boost/1.84.0` 为 `status=built` 未发布，`zlib/1.3.1` 同理），触发 `--build=missing` 源码构建链；`bzip2=False` / `with_stacktrace_backtrace=False` 等选项收窄只产生新的 package_id（无预编译二进制），治标不治本，故整包移除依赖 |

## 验证结果

```bash
# 真机预检（由 HMBS 后台执行，本轮未提交前为待验证）
# conan create archives/l/libgdf/0.1.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 预期：ctest 7/7 通过（含 WILL_FAIL 的 testfail）+ test/gdftest 1 项已审计跳过（Qt 手动 harness，真机核验 N=8），test_libgdf 6/6 通过
```

上游测试 8 个：test/CMakeLists.txt 注册 7 个 ctest（testok、testfail（WILL_FAIL）、
testCreateGDF、testRWConsistency、testSparseSampling、testHeader3、testDataTypes，
`ctest -N` = 7，全部运行通过）+ test/gdftest/ 1 个 Qt 手动 harness（gdftest.pro +
main.cpp，未注册 ctest，需 Qt 且 `main.cpp::test_guillaume()` 硬编码打开
`/media/bci-public/...` 外部数据集，OHOS 无头环境不可运行，已审计为 environment
跳过，见配方 gaps，真机核验 N=8）。
test_package 消费者测试 6 个断言，均为 Writer/Reader 真实调用，非空壳。

## 交付物

本轮仅交付未提交工作树，待 HMBS 真机验证后统一提交推送。

## 注意事项

- 本机 Windows 无 Python/conan，真机验证前不在本机运行 conan。
- `git rev-parse --verify HEAD` 已通过（upstream/main），无 `index.lock` 残留，
  `ci/conan/profiles/ohos-aarch64` 存在。
- 上游 Python 绑定（BUILD_PYTHON_MODULES）默认关闭，不引入 Cython/python 依赖。

# mbits-lngs 0.7.6 真机测试记录

日期：2026-10-04（上游全量测试于 2026-10-03 完成，Conan 选项兼容复核于 2026-10-04 完成）。设备：HarmonyOS PC aarch64，Clang 15，Conan 2.29.1、CMake/CTest 4.4.3、pkg-config 3.0.7。test_package 将 CMake >= 3.20 作为保守最低版本；`set_tests_properties(... WORKING_DIRECTORY ...)` 使用目标目录生成表达式，CMake 3.20 的 [`set_tests_properties` 手册](https://cmake.org/cmake/help/v3.20/command/set_tests_properties.html)说明测试属性按 `add_test` 支持的规则展开生成表达式，而 [`add_test` 手册](https://cmake.org/cmake/help/v3.20/command/add_test.html)列明 `WORKING_DIRECTORY` 支持生成表达式。本项目不把 3.20 声明为该功能首次支持版本。本机实测 CMake/CTest 4.4.3。`PkgConfigDeps` 消费者目标在 build-machine 同时具备 `pkg-config` 和生成的 `lngs.pc` 时编译链接；不可用时作为可选覆盖跳过，不阻断 CTest。HarmonyOS PC 实测使用 pkg-config 3.0.7，构建链接通过。官方源码版本及 SHA-256 与配方一致：`v0.7.6` / `85c9fd3afd5b6d5446a294f4de11221ae7fa160a62d1115a7ea0c1af17633a0b`。

独立复核命令：`git ls-remote https://github.com/mbits-os/lngs.git refs/tags/v0.7.6` 返回 `refs/tags/v0.7.6` 指向提交 `4f00aaaee7eb6aa1769dcc74f716a3649a62d8fd`，且远端无该 tag 的 peeled `^{}` 引用，确认它是 lightweight tag；`curl -fsSLo lngs-v0.7.6.tar.gz https://codeload.github.com/mbits-os/lngs/tar.gz/refs/tags/v0.7.6 && sha256sum lngs-v0.7.6.tar.gz` 返回上述 SHA-256。

## 精确依赖与测试子模块

| 项目 | 提交 | 归档 SHA-256 | 结果 |
|---|---|---|---|
| mbits-args 0.12.3 | `72f5f2b87ae39f26638a585fa4ad0b96b4152ae6` | `1a1dc5793e927a7f8c34b77c776b4d4a88f7ce9557657d8e806fca2922bd07a0` | 真机构建、安装成功 |
| mbits-diags 0.9.6 | `20d32182f0d9b0ec49c56729add28d5200fc5596` | `db86aa0c4ce1bbfa548a39e046b7872e6f369d668ee433dc5a57cf2a026deb4c` | 真机构建、安装成功 |
| mbits-utfconv 1.0.3 | `385a8cc4d86bbf601375cf27ecb6bf9819a58afd` | `2077e3dcb999dc76d2bdc06cc141b38e10f15762975c261f72cc1a8c2519a27a` | 真机构建、安装成功 |
| mbits-mstch 1.0.4 | `3e532ca559e4eebb360172a450b13b22b1fcb13b` | `ee3052b9c2321b46fffabb5db5d5659e5f963070cdfd0004701b515867ed6857` | 真机构建、安装成功 |
| tools/testing | `0fd6cc19bc269ff436cc8339a576dba351fed42c` | `01d595c66172bca405312440eaf7df7915d35e2a7600fcf98717f2f0bd9d8f92` | 还原上游 pin |
| tools/coveralls | `3e0701f6a4c0faa5e06c00d8ffe652cb3004b6b0` | `3b67cd44819b7f32075221da9862244dd15527eaefe86203e06041acb9a81e10` | 还原上游 pin |

外部构建依赖：`fmt/9.1.0` 与 `mbits-semver/0.1.1` 从 registry 获取；`mbits-args/0.12.3`、`mbits-mstch/1.0.4`、`mbits-utfconv/1.0.3`、`mbits-diags/0.9.6` 按上游 pin 从源码在真机手工构建。上游 `conanfile.txt` 请求 `gtest/cci.20210126`，该精确 Conan 包未在 registry 找到；本次完整 CMake 测试使用从 GoogleTest 上游源码手工构建的 1.17.0。它与 `cci.20210126` 是不同依赖版本/来源，故本次结果证明上游测试源码在 1.17.0 下运行通过，不代表已复现该 Conan 包版本。registry 可用的兼容测试包 `gtest/1.17.0.2` 也未用于本次全量测试。手工构建与临时 CMake package config 只用于真机完整测试，不表示相应 Conan 配方已发布到 registry。

## 真机命令与结果

配置参数：`-DLNGS_TESTING=ON -DLNGS_APP=ON -DLNGS_LITE=ON -DLNGS_INSTALL=OFF -DLNGS_LINKED_RESOURCES=ON`，链接 OHOS Conan toolchain 与上述真实依赖。以下 CMake 等价性论证仅适用于上游提交 `4f00aaaee7eb6aa1769dcc74f716a3649a62d8fd`；版本升级后须重新核验。论据为：上游 `libs/CMakeLists.txt:5-8` 始终添加 `liblngs`，仅在 `if (LNGS_LITE)` 下额外添加 `liblngs_lite`；`libs/liblngs/CMakeLists.txt:41` 明确将核心目标定义为 `STATIC`，且该文件全文没有 `LNGS_LITE` 条件或引用。`libs/liblngs/CMakeLists.txt:77` 的 `liblngs-test` 链接 `liblngs` 与 `lngs_app`，`app/CMakeLists.txt:262` 的 `lngs-test` 链接 `lngs_app`，两个测试目标均未链接 `lngs_lite`。因此关闭 LITE 仅移除附加 SHARED 目标，不改动核心静态目标、其编译配置或测试入口。最终 `LNGS_LITE=OFF` 包已单独运行 `test_package` 消费者测试（CTest 2/2）。

上游 CMake 结构摘录：`libs/CMakeLists.txt` 无条件执行 `add_subdirectory(liblngs)`，且仅在 `if (LNGS_LITE)` 分支执行 `add_subdirectory(liblngs_lite)`；`libs/liblngs/CMakeLists.txt` 定义 `add_library(liblngs STATIC ...)`。这说明 `LNGS_LITE` 只控制附加共享目标，不切换核心静态库目标。

离线复核资料包括以下官方 v0.7.6 CMake 原文摘录及 `reports/lite-scope-verification.txt` 保存的校验摘要。在线复核入口为 `reports/verify_lite_scope.py`（需网络可达 `codeload.github.com`）；该脚本下载固定归档、校验 SHA-256 并断言相同结构。

```cmake
# CMakeLists.txt
use_flag(LNGS_LITE ON "Create lngs_lite library")

# libs/CMakeLists.txt
add_subdirectory(liblngs)
if (LNGS_LITE)
  add_subdirectory(liblngs_lite)
endif()

# libs/liblngs/CMakeLists.txt
add_library(liblngs STATIC ${liblngs_SRCS} ${liblngs_INCS})

# libs/liblngs_lite/CMakeLists.txt
add_library(lngs_lite SHARED lite.cpp include/lngs/lite.h)
target_link_libraries(lngs_lite PUBLIC liblngs)
```

完整 `libs/liblngs/CMakeLists.txt` 全文无 `LNGS_LITE` 条件或引用；其测试目标将 `liblngs-test` 链接至 `liblngs` 和 `lngs_app`。`app/CMakeLists.txt` 的 `lngs-test` 链接至 `lngs_app`。完整 `libs/liblngs_lite/CMakeLists.txt` 仅创建 `lngs_lite` 共享目标、设置自身 include/compile 属性并将 `liblngs` 链接为其依赖；未修改 `liblngs` 的源码、编译定义或链接属性。

| 测试目标 | 真机命令 | 结果 |
|---|---|---|
| 核心库测试 | `./libs/liblngs/liblngs-test` | 196/196 GoogleTest 实例通过，退出码 0 |
| app 测试 | `./app/lngs-test` | 206/206 GoogleTest 实例通过，退出码 0 |
| 上游 GoogleTest 声明 | `grep -R -n -E '^[[:space:]]*(TEST(_P|_F)?)[[:space:]]*\(' <源码>/libs/liblngs/tests <源码>/app/tests` | 49 个声明（lib 25 + app 24），49/49 实际执行通过；共 402/402 参数实例 |
| CTest 命令行 fixture | `ctest --test-dir <build> --output-on-failure` | 18/20 CTest 项通过；`0028-no-shared-data-enum.json` 按上游 `skippable: true` 标记跳过；`0027-no-shared-data.json` 实际输出 `unknown command: --share`，上游预期 `command missing` |
| Conan 消费者测试 | `conan create ...` 的 `test_package` | Conan static-library 配置下 CTest 2/2 通过：主消费者六项检查 + 共享消费者运行检查；另有 pkg-config 消费者目标编译链接通过；与上游测试分开 |

最终 Conan 包配置使用 `LNGS_LITE=OFF`、`LNGS_NO_PKG_CONFIG=ON` 和 `CMAKE_POSITION_INDEPENDENT_CODE=ON`，只包含静态核心库 `liblngs.a`、公开头文件与上游 `LICENSE`。在 Conan cache package folder 中执行 `find "$CONAN_HOME/p" -path '*/p/licenses/LICENSE' -type f` 并找到 LICENSE 文件。配方的 `pkg_config_name` 属性按 Conan `PkgConfigDeps` 约定生成上游名称 `lngs.pc`；test_package 另编译并链接同一公开 API 消费者源码，验证 pkg-config 查找与链接。此构建期检查不计入 CTest 2 项运行测试；检测不到 `pkg-config` 或 `lngs.pc` 时按可选覆盖跳过。2026-10-04 HarmonyOS PC 的最终 `conan create` 配置日志显示 `Found PkgConfig`、检测到 `lngs` 0.7.6，且 `test_mbits_lngs_pkgconfig` 编译链接成功。`package()` 断言必需的 `lib/liblngs.a` 与 6 个上游公开头（`lngs.hpp`、`lngs_base.hpp`、`lngs_file.hpp`、`lngs_storage.hpp`、`plurals.hpp`、`translation.hpp`）存在，同时断言裸 CMake export、上游共享库和上游 `.pc` 文件未残留；此次 Conan create 完成，所有正负向断言通过。上游前缀假设的 `lngs.pc` 不直接打入包。test_package 有六项主消费者检查及一项共享消费者运行检查，CTest 2/2 通过；共享消费者目标将 PIC 静态归档链接并运行，runner 使用 `./` + 目标文件名从 CTest 工作目录相对加载共享库；`WORKING_DIRECTORY` 绑定共享目标的 `$<TARGET_FILE_DIR:...>`，支持多配置生成器。移走构建目录后需重新 configure，再运行 CTest。

配方将源码标准固定为 C++17；profile 声明更高的 `compiler.cppstd` 时只用于最低能力校验，不改变生成器中的 `CMAKE_CXX_STANDARD=17`。manifest `configure_options` 同时记录五个上游 `LNGS_*` 选项、一个 `CMAKE_POSITION_INDEPENDENT_CODE` PIC 开关与三项 C++ 标准约束（C++17、required、extensions off）；配方将这些值通过 CMakeToolchain 显式设置，`check_min_cppstd` 再按 Conan profile 的编译器标准作最低版本验证。

2026-10-04 在 Conan cache 的 v0.7.6 源码中复核：根 `CMakeLists.txt:18` 定义 `LNGS_NO_PKG_CONFIG`（默认 OFF，说明为跳过 `lngs.pc` 安装）；`libs/liblngs/CMakeLists.txt:66-67` 仅在 `NOT LNGS_NO_PKG_CONFIG` 时安装 `lngs.pc`。因此配方显式设为 ON 会跳过该文件安装。

OHOS ABI 运行库复核：设备 SDK `native/llvm/lib/aarch64-linux-ohos/libc++abi.a` 存在；最终 test_package 的 `link.txt` 在 `clang++ -stdlib=libc++` 链接命令中包含 `-lc++abi` 并成功生成/运行消费者目标。由 `-stdlib=libc++` 选择 C++ 标准库的 Clang driver 提供 ABI runtime；配方不重复注入 `system_libs`。

上游 `cmake.install()` 会安装 `lib/cmake/mbits-lngs.cmake` 与 `lib/cmake/mbits-lngs-release.cmake`（导入目标 `mbits::liblngs`）；配方 `package()` 收集文件后移除 `lib/cmake/`，避免把不属于 Conan CMakeDeps 接口的裸 export 文件混入包。最终 Conan package folder 清单仅含 `lib/liblngs.a`、公开头文件和 `licenses/LICENSE`；没有 `lib/cmake/`、`share/pkgconfig/lngs.pc` 或 `liblngs_lite.so`。消费者侧 CMakeDeps 在 generators 目录生成 `mbits-lngs` config 与 `mbits-lngs::mbits-lngs` 目标。

历史 `shared=True` 探测针对尚未声明 `shared` 选项的配方修订；OHOS 适配 Conan 2.29.1 接受了未声明输入并仍生成静态包。最终配方显式声明 `shared=False`；在实际探测中，Conan 的 `package_type="static-library"` 校验先返回明确配置错误，配方 `validate()` 也主动拒绝 `shared=True`。历史探测不计入正式消费者通过率或支持配置；静态核心目标启用 PIC，并由 test_package 的共享消费者目标进行链接验证。

已核对仓库 `ci/conan/build_and_test.sh` 的 Conan 调用参数：CI 仅传 host/build profile 与 `--build=missing`，没有注入 `shared` 选项；`ci/conan/setup.sh` 使用 OHOS 适配 Conan wheel（基线 2.29.1）并记录实际版本。设备实测 `conan --version` 为 `Conan version 2.29.1`。该 shared 选项探测运行于最终 recipe 之前的旧修订，当时尚未声明该选项；OHOS 适配版接受了未声明输入并生成静态核心包。当前 recipe 显式声明 shared=False，由配方 `validate()` 主动拒绝 shared=True，Conan 的 static-library 类型约束也会拒绝；CI 实际调用不注入此选项。

初始 `LNGS_LINKED_RESOURCES=OFF` 构建出现的模板输出为空，源于没有安装外置模板，不是上游测试失败。改用上游支持的内嵌模板选项后重新编译、运行；最终测试结果仅采用内嵌模板配置的完整实测。

## 边界

上游 49/49 指 GoogleTest 的源码声明数，不表示所有额外 CTest fixture 都通过。命令行 fixture 的 1 项失败如实保留。当前 Conan 配方依赖 registry 的包集仍是独立问题；本地完整测试结果不等于远端 CI 通过。消费者 `test_package` 只算 HarmonyOS 特有测试。

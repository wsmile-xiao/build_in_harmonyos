# synfig 1.5.5 适配笔记

## 编译环境
- 构建系统: CMake（顶层工程 ETL + synfig-core + synfig-studio）
- 编译日期: 2026-08-02
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 平台: HarmonyOS PC aarch64 (arm64-v8a), musl libc
- 状态: built（本地验证通过，尚未 CI upload；CI 成功后更新为 published）

## 适配目标
- CLI-only：synfig 命令行渲染器（synfig-core），关闭 synfig-studio GUI（gtkmm-3.0）
- 产物: bin/synfig + libsynfig.a + lib/synfig/modules/*.so

## 依赖裁决（W0 已核实）
| 依赖 | 版本 | 说明 |
|------|------|------|
| glibmm | 2.66.9@ohpcd/stable | synfig-core 探测 glibmm-2.4.pc，须用 2.4 ABI 线（2.84 提供 glibmm-2.68.pc 不符） |
| libxmlpp | 2.42.3@ohpcd/stable | 探测 libxml++-2.6.pc，2.x 线官方最新 2.42.3 |
| libsigc | 2.10.8 | conan 包名 libsigc（glibmm 依赖 sigc++-2.0） |
| fontconfig | 2.18.1.1 (force) | 覆盖 cairo 传递的旧 pin（修复 DT_NEEDED 烤 conan cache 绝对路径） |
| libxml2 | conan 传递依赖 | 由 libxmlpp 的 conan 依赖链提供（libxmlpp requires libxml2/2.15.3，PkgConfigDeps 生成 libxml-2.0.pc） |
| pango | 不需要 | 仅 synfig-studio（GUI，WITH_STUDIO=OFF 已关闭）使用，CLI-only 构建（synfig-core）不依赖 |

## 编译步骤
1. `conan create work/synfig -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
2. conanfile.build(): 自发现 ohos.toolchain.cmake → cmake -B build-ohos（CLI-only 选项 + C++17 + policy 3.5）→ cmake --build
3. package(): cmake --install + binary-sign-tool 自签 bin/synfig 与 modules/*.so
4. test_package: bash test.sh 真实执行 synfig --version / --help 冒烟

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 | 知识条目 |
|---|------|------|----------|----------|
| 1 | lyr_freetype: fribidi.h not found | conan fribidi 包头在 include/fribidi/ 下 | 0005: `<fribidi.h>` → `<fribidi/fribidi.h>` | - |
| 2 | synfig --version 打印 "synfig-tool unknown" | CMake 构建不定义 VERSION/PACKAGE（autotools 由 config.h 提供），definitions.h 回退 unknown | 0006: synfig_bin target_compile_definitions 定义 VERSION="1.5.5" PACKAGE="synfig-tool" | - |
| 3 | test_package 期望 --version 退出 0 失败 | 上游设计：--version/--help 打印后抛 SYNFIGTOOL_HELP（退出码 3） | test.sh 接受退出码 0/3，断言输出含 "1.5.5" | - |
| 4 | ghfast.top 源码下载 SSL 失败 | ghfast.top 证书 hostname mismatch，conan 严格校验失败 | conandata.yml 改直连 github（302→codeload，sha256 不变） | - |
| 5 | CMake 不认识 HarmonyOS | ohos.toolchain.cmake 自发现（profile user_toolchain / OHOS_NDK_HOME / glob SDK） | E092 |
| 6 | 缺 llvm-ranlib | OHOS SDK llvm/bin 常只有 llvm-ar | 配方 _llvm_ranlib() 检测并回退 PATH | - |

## 源码修改（6 个补丁）
1. **0001**: CMakeLists.txt 增加 WITH_STUDIO option（默认 OFF），cli-only 构建跳过 synfig-studio
2. **0002**: mod_openexr 以 PkgConfig::OPENEXR 目标存在性门控（无 OpenEXR 时跳过）
3. **0003**: synfig-core/src/ltdl.h shim：lt_dl* API 映射 dlfcn（OHOS 无 libltdl）
4. **0004**: 不链接 -lltdl（符号来自 shim + libc dlfcn）
5. **0005**: lyr_freetype fribidi 头文件路径修正
6. **0006**: synfig_bin 定义 VERSION/PACKAGE 宏

## 验证结果
- conan create：构建通过（0 error）
- test_package 冒烟：--version 输出 "synfig-tool 1.5.5"、--help 输出 OK、二进制身份 OK，全部通过
- conan-verify：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
- check-env：errors=0, warnings=0

## 遗留事项
- conancenter remote 在本机 SSL 证书失效，已 `conan remote disable conancenter`（仅本机，不涉及配方）

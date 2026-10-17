# kysdk-ai-common 1.1.0.1 适配笔记

## 编译环境
- 构建系统: cmake (>=3.12，本机 4.1.2)
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++
- 平台: HarmonyOS PC (aarch64, os=OHOS)
- 状态: built

## 编译步骤

源码: https://gitee.com/openkylin/kysdk-ai-common.git tag upstream/1.1.0.1 (commit 8e1950b9)。
gitee 归档包: repository/archive/upstream/1.1.0.1.tar.gz, sha256 0044393aedbb50cfcf457f98e5fe15f60c15e477a6fdc40181878c5b29218b0d。

手动编译（模式 B Step 2，全部成功）:
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build build -j4        # [100%] Built target KysdkAiCommon
DESTDIR=$TEST_PREFIX cmake --install build   # 安装 libkysdk-ai-common.so / include/kylin-ai / KysdkAiCommonConfig.cmake
```
无外部依赖：CMakeLists.txt 无任何 find_package；recipe requires 为空。

## 上游测试申报表（R51 三步法）

| 项 | 值 |
|---|---|
| 清点数 | 0 |
| 运行数 | 0 |
| 通过率 | N/A（上游确无测试） |

清点证据（tag upstream/1.1.0.1, commit 8e1950b9）:
1. `find . -iname '*test*' -not -path './.git/*'` → 无结果
2. `ls tests` → "ls: tests: No such file or directory"
3. CMakeLists.txt 无 enable_testing()/add_test()，无测试目标
4. 仓库根目录仅有 CMakeLists.txt/LICENSE/README*/cmake/include/src/usr

test_package 消费者测试（实质 API 验证）: 链接 KysdkAiCommon::KysdkAiCommon，
调用 is_ai_subsystem_inited()（未初始化进程应返回 false，src/common.cpp:83 逻辑）、
校验 AiSdkCommonErrorCode/ModelDeployType 枚举值，3 项断言 → 3/3 通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 自动下载报 "下载内容是 HTML" | 工具只支持直接 tarball URL，不支持 gitee tag 归档路径 | 手动 git clone --branch upstream/1.1.0.1 + git archive/官方归档 URL + sha256 写入 conandata.yml |
| 2 | conan `get()` 报 sha256 不匹配且每次 Computed hash 不同 | **实测验证**：gitee 归档端点对 conan 的 Python urllib 下载器返回 46902B HTML 反爬页而非 16770B tar.gz（curl 默认 UA 7 次均稳定 0044393a…；python urllib/UA=Conan 均返回 HTML）；首次 `Computed hash: 3e490fc8…` 与二次 `b2523b6b…` 均为 HTML 页哈希 | source() 改用 Git clone 官方源 + `--branch upstream/1.1.0.1 --depth 1`，commit 8e1950b9 固定（R39 合规：官方正式源） |
| 3 | `git clone … .` 报 "destination path '.' already exists" | `export_conandata_patches()` 先把 patches/ 写进 source 目录，目标非空 | 克隆到临时子目录 `_git_src` 再搬回 source 根，rmtree 清理 |
| 4 | `git.checkout()` 报 "not a git repository" | conan Git.checkout() 在 source_folder（已无 .git）下执行 | 改用 clone `--branch <tag> --depth 1` 直接得到目标树，省去 checkout |
| 5 | conan package() 报 `file INSTALL cannot set permissions on "/usr"` | 上游 CMakeLists `install(DIRECTORY usr/ DESTINATION /usr)` 直写系统根（deb 打包遗留写法），pc 文件 Cflags 也硬编码 `-I/usr/include/kylin-ai` | patches/0001-no-install-usr-system.patch 移除该 install 行（conan cpp_info 接管 include/lib 路径，pkg-config 消费场景由下游 cpp_info 兜底） |
| 6 | test_package 链接失败 `KysdkAiCommon::KysdkAiCommon target not found`（CMakeDeps 生成的是 `kysdk-ai-common::kysdk-ai-common`） | CMakeDeps 默认目标名 = `pkg_name::pkg_name`，不读 cmake_file_name；上游导出名是 `KysdkAiCommon::KysdkAiCommon` | package_info 显式 `set_property("cmake_target_name", "KysdkAiCommon::KysdkAiCommon")`（cmake_file_name 只决定 Config 文件名，不影响 target 名） |

## 源码修改

patches/0001-no-install-usr-system.patch（1 行删除）：移除 `install(DIRECTORY usr/ DESTINATION /usr)`（该行在 conan package() 阶段直写系统 /usr 报 Operation not permitted）。零平台宏。

## 依赖版本

无依赖（纯 C++ 单库，仅 libstdc++）。

## 验证结果

```bash
# conan-verify G0-G4/L2/L4/L5: 全部 PASS（reports/conan-verify-report.md）
# W3 本地 CI: 1/1 通过（reports/w3-local-ci.log）
# conan create 内嵌 ctest: 1/1 passed（.ci_logs/conan_build_*.log）
# SONAME 实测: readelf -d libkysdk-ai-common.so → SONAME: libkysdk-ai-common.so
```

首次 W3 曾报 L5 SONAME 门禁失败（CMake 无 HarmonyOS 平台模块，`CMAKE_SHARED_LIBRARY_SONAME_FLAG` 为空，VERSION/SOVERSION 不生效，产物缺 DT_SONAME），已在补丁中加 `target_link_options(... "-Wl,-soname,libkysdk-ai-common.so")` 修复并复验通过。

## 平台注意

- cmake target 名 `KysdkAiCommon`，输出库 `libkysdk-ai-common.so`
- package_info: cmake_file_name=KysdkAiCommon, libs=['kysdk-ai-common'],
  includedirs=['include','include/kylin-ai'] — 下游 libkysdk-genai 可 find_package(KysdkAiCommon)
- `is_ai_subsystem_inited()` 内部用 popen 调 `ps`/`dpkg`，OHOS 上会自然返回 false（非失败路径），测试语义仍成立
---

**编译结束**: 2026-09-17 09:53
**最终状态**: built

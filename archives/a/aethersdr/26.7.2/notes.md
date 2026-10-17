# aethersdr 26.7.2 适配笔记

## 编译环境
- 构建系统: cmake（顶层 CMakeLists.txt，3552 行，project(AetherSDR VERSION 26.7.2 LANGUAGES C CXX)）
- 编译日期: 2026-08-24
- 编译器: clang/clang++（OHOS clang 15，目标 aarch64-unknown-linux-ohos）
- 状态: in_progress（Qt6 工具链已就绪：ohpcd 已发布 qtbase/6.11.1 + qtmultimedia/6.11.1 + qtshadertools/6.11.1，配方依赖已修正，待 finish --resume 验证 conan create + ctest）

## 编译步骤

1. **上游调查**（W0）
   - 任务指定上游 `https://www.aethersdr.org/aethersdr-26.7.2.tar.gz` 经实测是停放域名（curl -sI 返回 Content-Type: text/html, Content-Length: 114，内容为 window.location.href="/lander" 的 HTML 占位页）
   - 真实官方源：GitHub `aethersdr/AetherSDR` tag `v26.7.2`（Organization 类型，206 stars，fork=False，published 2026-07-12，CalVer 与任务 26.7.2 匹配）
   - 下载源码：`curl -sL https://github.com/aethersdr/AetherSDR/archive/refs/tags/v26.7.2.tar.gz` → 167,266,948 bytes，有效 gzip
   - sha256: 655ce58464bfe56221f0608ae219c0da36bc40c76ecef884f39ca10f80dffe99

2. **init-build**
   ```
   python3 scripts/ohc-run.py init-build aethersdr 26.7.2 \
     --url=https://github.com/aethersdr/AetherSDR/archive/refs/tags/v26.7.2.tar.gz
   ```
   - 源码下载解压成功（2547 个文件）
   - CMakeLists.txt 确认 3552 行，与任务描述完全吻合

3. **cmake configure**（实测）
   ```
   cd /storage/Users/currentUser/builds/aethersdr-26.7.2.work
   cmake -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
   ```
   - 崩溃点：`CMakeLists.txt:70 find_package(Qt6 6.2 REQUIRED COMPONENTS Core Concurrent Widgets Network Multimedia Test)`
   - 报错：`Could not find a package configuration file provided by "Qt6" (requested version 6.2) ... Qt6Config.cmake ... Configuring incomplete, errors occurred!`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure 在 CMakeLists.txt:70 失败 | Qt6 6.2+ 硬依赖，CI 环境完全缺失 | W0b 选型即止 env_unsupported |
| 2 | 任务指定上游 www.aethersdr.org 是停放域名 | 域名停放，非软件托管 | 改用官方源 GitHub aethersdr/AetherSDR tag v26.7.2 |
| 3 | conandata.yml sha256 占位符 | conan-init 模板默认值 | 实测 sha256sum 替换为 655ce584...ffe99 |
| 4 | conanfile.py 误用 Autotools 模板 | init-build 误识 cmake 为 autotools | 重写为 CMake 配方（CMake/CMakeToolchain, package_type=application） |
| 5 | test.c 空壳 printf | conan-init 默认模板 | 重写为 popen 执行 AetherSDR --version 的实质测试（R34） |

## Qt6 缺失三重验证（W0b 选型即止依据）

1. **系统层全空**：
   - `pkg-config --exists Qt6Core` → NOT FOUND
   - `which qmake6` → 空
   - `find /usr /opt -name Qt6Config.cmake` → 空
   - `dpkg -l | grep qt6` → 空
   - `apt-cache search qt6` → 空

2. **Conan registry ohpcd 双空**：
   - `conan list "qt/*" -r=ohpcd` → Found 0
   - `conan list "qt6/*" -r=ohpcd` → Found 0

3. **实际 cmake configure 报错**：
   - `CMakeLists.txt:70 find_package(Qt6 6.2 REQUIRED ...)` → `Could not find Qt6Config.cmake` → `Configuring incomplete, errors occurred!`

判定口径（SKILL.md）："换个网络正常的机器能否解决"——能 → dependency_missing；不能 → env_unsupported。
Qt6 在 CI 远端 clean 环境完全不存在且无法 tool_requires 补齐 → **env_unsupported**（非 dependency_missing）。

## 上游测试清单

- tests/ 目录：118 个 `*_test.cpp` 文件
- 顶层 CMakeLists.txt：110 个 `add_test` 测试目标
- third_party/crdv/tests/：2 个测试文件
- tests/ 中 run_*.cmake 脚本：2 个
- 合计上游测试用例：约 120 个

**上游测试执行结果：N/A — 未进入 ctest 阶段**
- 原因：cmake configure 阶段在 CMakeLists.txt:70 因 Qt6 缺失而失败，无法生成 build/ 测试目录
- ctest 无法执行，因此测试用例个数无法通过实测得到（按上游 CMakeLists.txt 静态统计约 120 个）

## 源码修改

无。本次为选型即止，未修改上游源码。

## 依赖版本

| 依赖 | 版本 | 类型 | 可用性 |
|------|------|------|--------|
| Qt6 | 6.2+ | 硬依赖（CMakeLists.txt:70 REQUIRED） | ❌ CI 环境完全缺失 |
| liquid-dsp | vendored | third_party/ | ✅ vendored |
| libmspack | vendored | third_party/ | ✅ vendored |
| rtmidi | vendored | third_party/ | ✅ vendored |
| opus | vendored | third_party/ | ✅ vendored |
| zlib | vendored | third_party/ | ✅ vendored |

## 验证结果

```bash
# 源码 sha256 实测
sha256sum sources/aethersdr/aethersdr-26.7.2.tar.gz
# → 655ce58464bfe56221f0608ae219c0da36bc40c76ecef884f39ca10f80dffe99

# cmake configure 崩溃点
cd /storage/Users/currentUser/builds/aethersdr-26.7.2.work
cmake -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo 2>&1 | grep -A3 "find_package"
# → CMake Error at CMakeLists.txt:70 (find_package):
# →   By not providing "FindQt6.cmake" in CMAKE_MODULE_PATH ...
# →   Could not find a package configuration file provided by "Qt6"
# → Configuring incomplete, errors occurred!

# Qt6 系统层验证
pkg-config --exists Qt6Core && echo FOUND || echo "NOT FOUND"
# → NOT FOUND

# conan registry Qt6 验证
conan list "qt/*" -r=ohpcd
# → Found 0 pkg/version recipes matching qt/* in ohpcd
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，package_type=application，Qt6 依赖声明（R32） |
| conandata.yml | GitHub 官方源 + 实测 sha256（R39） |
| manifest.yaml | 归档元数据，status=archived，build.system=cmake |
| test_package/test.c | 实质测试：popen 执行 AetherSDR --version（R34） |
| test_package/conanfile.py | self.run() 执行被测包二进制模式 |
| test_package/MANIFEST.yml | 上游测试清单（118 cpp + 110 add_test ≈ 120 用例） |
| notes.md | 本文件，完整适配记录 |

## 注意事项

1. **Qt6 是适配 aethersdr 的硬前置依赖**。若未来 CI 环境提供 Qt6（系统安装或 conan registry 上传 qt 包），可重新启动适配流程。
2. 本次为 **env_unsupported 选型即止**，非 failed_build。未进入 finish/conan create，无 .ci-result.json（合规：止损产物不生成 CI 结果文件）。
3. 上游测试 ~120 个用例**未执行**，因 Qt6 缺失导致 cmake configure 失败。这是已验证的技术事实（三重证据），非网络/环境借口。
4. conanfile.py 中 `tool_requires = "qt/6.5.3"` 是依赖声明，registry 实际无此包，故无法 tool_requires 补齐。
---

**编译结束**: 2026-08-24 19:53
**最终状态**: archived

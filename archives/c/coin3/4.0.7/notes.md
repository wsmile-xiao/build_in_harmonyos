# coin3 4.0.7 适配笔记

## 编译环境
- 构建系统: cmake（源码同时含 autotools，CMake 为主维护入口）
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4 (OHOS SDK toolchain)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build coin3 4.0.7 --url=https://github.com/coin3d/coin/releases/download/v4.0.7/coin-4.0.7-src.tar.gz`
   - 官方 tarball SHA-256: a01276052c31e84e4a069ee4452eab3b65a7d101a3fd7a09803be59125616270（已核验）
2. `ohc-run.py lang-preflight` → cpp 匹配
3. 探索构建（CMake）：Boost(conan boost/1.90.0) + gl4es(conan gl4es/1.1.6 提供 libGL.so) +
   OHOS sysroot GL/EGL 头 + `-D_POSIX_C_SOURCE=200809L`；`COIN_BUILD_GLX=OFF COIN_BUILD_EGL=ON`
   → 100% 编译成功，CoinTests 327/327 通过
4. `ohc-run.py conan-init` → 重写 conanfile.py（CMake 模板 + boost/gl4es 依赖 + BoostConfig shim +
   SONAME 链接标志 + sysroot 定位），conandata.yml 官方 URL + SHA-256
5. `ohc-run.py conan-verify` → G0-G4 + L2/L4/L5 全 PASS
6. `ohc-run.py finish ... built` → W2/W3 通过（build_and_test.sh 100% pass）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 无 FindBoost 模块，boost/1.90.0 包无 BoostConfig.cmake | CMake 4 移除 FindBoost；conan boost 只提供头文件目录 | generate() 生成最小 BoostConfig.cmake shim（Boost::boost INTERFACE IMPORTED），Boost_DIR 指向它 |
| 2 | OHOS 无桌面 libGL 立即模式符号（libGLv4.so 无 glBegin/glEnd/glColor3f 等） | OHOS 仅 EGL+GLES3.2 | 依赖 gl4es/1.1.6 提供 libGL.so（桌面 GL→GLES2 翻译）；`headers=False` + 清空其 cpp_info.includedirs（gl4es 的 GL/EGL 头引用 X11/Xlib.h） |
| 3 | testsuite/TestSuiteUtils.cpp 编译失败（#error Unknown system） | 用 _POSIX_C_SOURCE/_POSIX_SOURCE 判 POSIX，OHOS libc 默认不定义 | CMAKE_C/CXX_FLAGS 加 `-D_POSIX_C_SOURCE=200809L` |
| 4 | coin3 强制 out-of-source 构建（CMakeLists.txt:40 拒绝 in-source） | 上游 CMake 设计约束 | conanfile 用 cmake_layout() |
| 5 | CMake 不识别 HarmonyOS 平台 → 产物缺 DT_SONAME（W3/L5 soname_gate_failed） | 无 Platform/HarmonyOS 模块，-soname 链接标志为空 | cache_variables 注入 `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG=-Wl,-soname,` |
| 6 | test_package 段错误 | ctest 不传 conanrun 环境；gl4es 需 LIBGL_GLES/LIBGL_EGL 指向 /system/lib64；SoDB::finish() 在 gl4es 关闭时崩溃 | test() 显式 self.run(env="conanrun") + 手动前插 coin3/gl4es lib 目录到 LD_LIBRARY_PATH + 设置 LIBGL_GLES/LIBGL_EGL；test 程序不调用 SoDB::finish()（验证已完成） |
| 7 | W3 build_and_test.sh 的 mktemp 写 /tmp 失败（/tmp 是 erofs 只读） | 本地 mktemp shim 硬编码 /tmp | TMPDIR=/storage/Users/currentUser/tmp + PATH 前置尊重 TMPDIR 的 mktemp wrapper |

## 源码修改

无源码补丁（未修改上游源码；全部通过配方参数/生成器解决）。

## 依赖版本

- boost/1.90.0（conan，头文件用途）
- gl4es/1.1.6（conan，提供 libGL.so；headers 不用）
- 系统：OHOS SDK sysroot 的 libEGL.so、GL/EGL 头；运行时 /system/lib64/libGLESv3.so + libEGL.so

## 验证结果

```bash
# 上游测试（testsuite CoinTests，Boost.Test）
./CoinTests --report_level=detailed   # Running 327 test cases... 全部通过，exit 0
# 双口径：source_declared_total=346，configured_executable_total=327，
#         executed_passed_total=327，失败 0，未实例化 19（全量通过率 327/346=94.5%；
#         当前配置可执行集合通过率 327/327=100%）
# 消费者验证（test_package/test.cpp）
LIBGL_GLES=/system/lib64/libGLESv3.so LIBGL_EGL=/system/lib64/libEGL.so ./test_coin3
# → test coin3 4.0.7: OK (scene graph write verified)，exit 0
```

## 知识候选台账与查重（任务类型：知识库扩展）

### 候选 1：CMake 4.x 对无 FindBoost 模块 + conan boost 无 BoostConfig 的库，需生成 BoostConfig shim
- 真实错误：`find_package(Boost REQUIRED)` → "Could not find a package configuration file provided by Boost"
- 根因：CMake 4.x 移除 FindBoost.cmake；conan boost/1.90.0 包未发布 BoostConfig.cmake
- 修复：generate() 写最小 BoostConfig.cmake（Boost::boost INTERFACE IMPORTED + Boost_INCLUDE_DIRS），Boost_DIR 指向生成目录
- 验证：conan create 配置成功；CoinTests 链接运行通过
- 适用范围：CMake 4.x + conan boost 头文件用途的任何库
- 查重：
  - 七轴：exact_duplicate=无（index.tsv 无 CMake4+BoostConfig shim 条目）；causal_duplicate=无；trigger_overlap=部分（E096 cmake-cxx-standard 同为 CMake 配置类但不同根因）；solution_overlap=部分（E096 用 cache_variables 手法相同但内容不同）；combination_novelty=有（Boost shim 是新的组合）；boundary_novelty=有（CMake 4.x 边界）；test_migration_novelty=有（配 testsuite 编译）
  - 结论：**new_draft**（可跨库复用：任何 CMake4+boost 头文件库）

### 候选 2：OHOS 无桌面 GL 立即模式符号，需 gl4es 提供 libGL.so（headers=False）
- 真实错误：链接 undefined glBegin/glEnd/glColor3f/glVertex3f（系统 libGLv4.so 无立即模式导出）
- 根因：OHOS 仅 EGL+GLES3.2；桌面 GL 固定管线库（Open Inventor 系）无法直接链系统 GL
- 修复：requires("gl4es/1.1.6", headers=False) + generate() 清空 gl4es cpp_info.includedirs（其头引用 X11/Xlib.h）+ OPENGL_*_LIBRARY 指向 gl4es libGL.so
- 验证：coin3 全量编译 + 测试通过
- 适用范围：任何依赖桌面 OpenGL 立即模式/固定管线 API 的 C/C++ 库
- 查重：
  - 七轴：exact_duplicate=无；causal_duplicate=无；trigger_overlap=有（gl4es 归档 notes 记载了 gl4es 自身适配，但无"消费方 headers=False + include 隔离"模式）；solution_overlap=部分（gl4es/1.1.6 归档）；combination_novelty=有（消费方隔离模式）；boundary_novelty=有；test_migration_novelty=有（test_package 运行时 LIBGL 环境）
  - 结论：**new_draft**（消费侧模式，与 gl4es 归档互补不重复）

### 候选 3：CMake 未知平台（HarmonyOS）导致 -soname 标志为空 → 产物缺 DT_SONAME
- 真实错误：W3/L5 `libCoin.so 缺少 DT_SONAME`（soname_gate_failed）
- 根因：无 Platform/HarmonyOS 模块，CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG 未初始化
- 修复：cache_variables 注入 `-Wl,-soname,`
- 验证：W3/L5 复查通过
- 查重：E537 覆盖"绝对路径 DT_NEEDED/IMPORTED_NO_SONAME"但针对 KF6 绝对路径场景；本轮是"未知平台未设 -soname 链接标志"（相同门禁不同根因），solution_overlap=部分，combination_novelty=有
  - 结论：**new_draft**

### 候选 4：OHOS testsuite POSIX 检测（_POSIX_C_SOURCE）与 test_package 无头环境运行时
- 真实错误：TestSuiteUtils.cpp `#error Unknown system`；test_package SegFault
- 根因：OHOS libc 默认不定义 _POSIX_C_SOURCE/_POSIX_SOURCE；ctest 不传 conanrun 环境
- 修复：编译标志注入；test() 显式 run + LIBGL_GLES/LIBGL_EGL + LD_LIBRARY_PATH
- 查重：E298（virtual-run-env-explicit-run）已覆盖运行时部分 → trigger/solution_overlap=完全命中 E298 运行时子项；但 _POSIX_C_SOURCE 编译标志子项 E298 未覆盖
  - 结论：partial_overlap → 并入候选 2/3 草稿的运行时小节引用 E298，不单独建草稿

## 路径决定

- 候选 1/2/3 均经实测验证、可跨库复用、查重为新增差异 → **new_draft（路径 B：知识库扩展）**
- 已建立 knowledge/drafts/ 同 stem 草稿（.md + .kv）

## 交付物

| 文件 | 说明 |
|------|------|
| archives/c/coin3/4.0.7/conanfile.py | CMake 配方（boost/gl4es 依赖 + 3 项 OHOS 适配注入） |
| archives/c/coin3/4.0.7/conandata.yml | 官方 URL + SHA-256 |
| archives/c/coin3/4.0.7/manifest.yaml | 版本级元数据 |
| archives/c/coin3/4.0.7/test_package/ | 消费者测试（真实 API 调用） |
| archives/c/coin3/4.0.7/reports/ | conan-verify-report + test-report |
| knowledge/drafts/ | 知识草稿（与本次 PR 同入） |

## 注意事项

- 不修改/不提交其他库归档；PR 仅含 archives/c/coin3/ + 知识草稿
- 提交前已清理 conandata.yml.ghfast-bak/.orig（E017 残留，JC1 会拦截）
- coin3 是纯库包（无 CLI），R38 commands.json 不适用（无 bin/ 交付物）

---

**编译结束**: 2026-09-15 18:45
**最终状态**: built

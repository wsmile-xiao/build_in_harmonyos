# dawn 0.0-git20260529.432db5d7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 1. 源码 (官方 googlesource commit 432db5d793fab353075fc2f445f4a20ef84f337a,
#      通过官方 GitHub 镜像 codeload tarball 获取, 内容逐文件一致)
# 2. conan create (配方): cmake -G Ninja + CMAKE_SYSTEM_NAME=Linux
#    依赖: abseil/20260526 + googletest/1.12.1 + spirv-headers (ohpcd 已发布)
# 3. 配置: DAWN_ENABLE_NULL=ON, 关闭 Vulkan/GL/Metal/D3D/GLFW/X11, 测试单独跑
# 4. 构建: webgpu_dawn 静态库 (dawn native + tint)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 googlesource 超时 | 网络无法直连 dawn.googlesource.com | 使用官方 GitHub 镜像 google/dawn (codeload tarball), SHA-256 逐一与 googlesource 内容核对一致 |
| 2 | tarball 解压后 HermeticXcode/ranlib 孤立符号链接导致 copytree 失败 | 上游 gitlink 符号链接 (macOS 专用) 无目标 | 移除该 macOS 专用符号链接 (构建不使用) |
| 3 | 21 个 third_party 子模块为空 (gitlink) | dawn 使用 gclient/DEPS 管理依赖 | 配方注入 ohpcd 已发布包: abseil/googletest/spirv-headers; CMAKE_PROJECT_INCLUDE 内提前 find_package 满足 Dawn "NOT TARGET" 守卫 |
| 4 | 大量 C++20 编译错误 (std::ranges/std::format/std::views/lexicographical_compare_three_way/span-from-string_view CTAD/P0960 聚合括号初始化/lambda 捕获结构化绑定/缺少 typename) | OHOS SDK clang 15 libc++ 缺少新版 C++20 设施, 上游基线使用更新 clang | 0001-ohos-libcxx-compat.patch: 替换为可移植等价实现 (std::copy/std::equal/手工三路比较/显式构造/CIED 引导), 补全 dependent typename |
| 5 | CMake 不认识 OHOS 平台, UNIX 分支失效 | CMake 无 HarmonyOS platform 模块 | 配方 generate() 设 CMAKE_SYSTEM_NAME=Linux (对应用 aarch64), 显式关闭 X11/GLFW/后端子项 |
| 6 | DAWN_SUPPORTS_GLFW_FOR_WINDOWING 无条件打开 | 上游在 UNIX 下强制 ON 但 GLFW 关闭时测试引用 dawn::dawn_glfw | patch: 该宏与 DAWN_USE_GLFW 联合判定; tests/CMakeLists.txt 同步 |
| 7 | gtest captured-stream 临时文件写 /tmp 失败 | OHOS /tmp 只读 (SKILL E002) | patch gtest-port.cc: 通用分支尊重 TMPDIR 环境变量 |
| 8 | google_source tarball 无法结出 webgpu_dawn bundle 内嵌套 abseil archive | bundle_libraries 把 conan IMPORTED 库 .a 文件作为成员打包, lld 无法解析嵌套 archive | patch BundleLibraries.cmake: 跳过 IMPORTED 目标, 消费者另行链接 abseil (test_package 链接 libabsl_*.a) |
| 9 | 产物链接缺 libc++ 符号 | test_package 仅 C 语言链接 | test_package project() 启用 CXX, 测试源改用 test.cpp |
| 10 | 上游测试 (tint_unittests/dawn_end2end_tests) | — | 在本地 build-min 全量运行: tint 44484/44484, end2end 292/292 (NULL 后端) |

## 源码修改

patches/0001-ohos-libcxx-compat.patch (29 个文件):
- generator/templates/dawn*: std::ranges::copy/equal → std::copy/std::equal
- src/dawn/common/{GPUInfo,MutexProtected,Sha3,ityp_vector}.{cpp,h}: 三路比较手写/typename/结构化绑定→显式变量
- src/dawn/native/{Blob,BlobCache,Queue,TintUtils,stream/*}: ranges → std:: copy/equal; TMPDIR
- src/tint/**/{vector.h,swap.h,buffer_reader.h,const_param_validator.cc,multiplanar_external_texture.cc}: typename/overloaded 引导/span 显式构造
- src/dawn/tests/{DawnTest,Replay,ResourceTableTests,CopyTests,MockCallback,CMakeLists}: std::format→to_string; P0960 括号→大括号; CXX 链接
- src/cmake/BundleLibraries.cmake: 跳过 IMPORTED 依赖

## 验证

- conan create (W3): 通过, test_package test_dawn 真实调用 wgpuCreateInstance/wgpuInstanceRelease PASS
- 上游测试: tint_unittests 44484/44484 (100%), dawn_end2end_tests 292/292 (100%, Null backend)
- 本库为纯静态库 (libwebgpu_dawn.a), 无 bin/ 产物, 无系统同名库冲突 (R26)

## 后续事项

- 仅启用 Null 后端; Vulkan/GL 等图形后端需鸿蒙图形栈支持, 超出本配方范围
- 上游提交后的新版本适配可查本 notes 的 libc++ 兼容清单

## 知识候选台账与查重（路径 B）

### 候选 1: OHOS clang15/libc++15 C++20 兼容全谱（系统性组合）

- 真实错误/根因/修复/验证: 见上文"遇到的问题"1-10 与 patches/0001-0029;
  验证 = conan create PASS + tint 44484/44484 + end2end 292/292
- 适用范围: 任何 C++20/Chromium 生态大型库在 OHOS 的适配
- 四范围查重:
  - 正式知识 (knowledge/graph): E130 (libc++ 需 C++17), E092 (CMake 无
    OHOS 平台), E002 (/tmp 只读), E236 (libtool .la 嵌套 archive — 触发
    面不同, lld 报错同形); 均未覆盖本组合
  - 图谱草稿 (knowledge/drafts): 已有 5 条同根因草稿 (ohos-libcxx15-
    missing-cpp20-ranges-algorithms, format-ranges-capability-gap,
    missing-cpp20-spaceship, missing-std-views, graaf-ranges), 覆盖
    ranges/format/views/spaceship 经典替换; 未覆盖 P0960 聚合括号初始化、
    结构化绑定 lambda 捕获、IMPORTED bundle 跳过、gtest TMPDIR 补丁
  - 归档 notes (archives/*): 无 dawn 级全谱系统性记录
  - 草稿目录新增: DRAFT-dawn-0.0-git20260529-libcxx15-cpp20-compat-ensemble
    (.kv/.md 配对)
- 七轴查重:
  - exact_duplicate: false (无全同条目)
  - causal_duplicate: partial (ranges/format/views/spaceship 与既有草稿同
    根因 libcxx15; P0960/结构化绑定/IMPORTED bundle 根因不同)
  - trigger_overlap: partial (编译期 "no member named" 重叠; 链接期
    "archive member neither ET_REL" 与 E236 同形但根因不同)
  - solution_overlap: partial (经典算法替换一致; P0960 大括号/显式变量/
    IMPORTED 跳过为新增)
  - combination_novelty: true (单一大型 Chromium 生态库全谱系统性首例)
  - boundary_novelty: true (P0960、结构化绑定捕获、bundle IMPORTED 三条
    新边界; E236 仅 libtool)
  - test_migration_novelty: true (gtest TMPDIR 补丁 + 44776 用例全量证据链)
- 关系: similar_to = E130/E092/E236 + 5 条 libcxx15 草稿;
  caused_by = 无 (工具链固有); prerequisite_of = 无; conflicts_with = 无
- 决定: **new_draft**（新增差异已由真实日志验证且可跨库复用）
---

**编译结束**: 2026-09-19 06:31
**最终状态**: built

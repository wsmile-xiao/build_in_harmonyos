# eastdc 0.0.0-fbcc34e 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4（OHOS aarch64, profile ohos-aarch64）
- 状态: built（本地全流程验证通过；Conan 发布受 EAThread/EAAssert 依赖发布阻塞，见下）

## 官方来源
- 上游 URL: https://github.com/electronicarts/EAStdC
- 版本: master HEAD `fbcc34e89c63636054334888f3a5bd7ac2fd4b76`（与任务版本 0.0.0-fbcc34e 一致）
- SHA-256: `857cf2bf88146bd41df128b1aa0a8c2db935a5a7cc3889b95e3100ddab774c79`
  （官方 GitHub archive tarball 本地实测；本地 GitHub 直连不可达，经 ghfast.top 镜像原样拉取官方 archive 计算）

## 依赖分析
| 依赖 | 仓库 HEAD | 制品仓状态 | 用途 |
|---|---|---|---|
| EABase | 0699a15efdfd20b6cecf02153bfa5663decb653c | **已发布** eabase/0699a15 | 库本体 27 处 include `<EABase/eabase.h>` |
| EAAssert | e5e181255de2e883dd1f987c78ccc42ac81d3bca | **未发布**（查找命令: `conan list "eaassert/*" -r=ohpcd` → 0 matches，首次跳过与最终回报前各查一次均 0） | 库本体 18 处 include `<EAAssert/eaassert.h>` |
| EAThread | a77e2276a3fe1489a7c6206c3f77ea10f7a5daf7 | **未发布**（查找命令: `conan list "eathread/*" -r=ohpcd` → 0 matches，首次跳过与最终回报前各查一次均 0） | EAStdC 公开头文件 EACallback.h/internal/Thread.h 无条件 include `<eathread/eathread_atomic.h>`、`<eathread/eathread_mutex.h>`，是库本体编译的硬依赖（非测试专用） |

> 依赖状态结论：EABase 已发布 ✓；EAAssert/EAThread 截至最终复查（2 次：首次跳过 + 回报前）制品仓均无可解析配方。
> 恢复条件：EAAssert（eaassert/0.0.0-e5e1812）与 EAThread（eathread/a77e227）发布到 ohpcd 制品仓后，
> 恢复 `conan create` → `finish` → W3，即可完成发布链。本任务内已用官方源码镜像在本地完整验证构建/测试/消费者/专项测试，无质量问题被依赖掩盖。

## 编译步骤
主库（本地探索，含镜像抓取的 EA 测试子模块头文件）：
```bash
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_CXX_FLAGS="-fPIC -I<src>/test/packages/EABase/include/Common -I<src>/test/packages/EAAssert/include -I<src>/test/packages/EAThread/include"
make -j4            # → libEAStdC.a 编译成功
```

Conan 配方（clean source 树）：
```bash
conan create . --profile:host=ohos-aarch64 --profile:build=default
```
- 配方源码 URL / SHA-256 通过并复现官方 tarball；
- 补丁 0001（cmake_minimum_required 3.1→3.5，CMake 4.x 兼容）、0002（CommonCppFlags include 守卫）应用成功；
- 依赖 include 注入（eabase/eaassert 已安装头文件）后编译推进至 EAStdC 源文件；
- 现仅剩 `eathread/eathread_atomic.h` 等 EAThread 头文件缺失（eathread 未发布）→ **外部依赖阻塞**，非本库配方/代码问题。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 报 `cmake_minimum_required(VERSION 3.1)` 兼容错误 | CMake ≥4 移除 <3.5 兼容 | patch 0001 提升到 3.5（与 eaassert 配方同款做法） |
| 2 | clean 源码树 `include(CommonCppFlags)` 失败 | 该 cmake 模块位于 EA 测试子模块树，纯净 tarball 不存在 | patch 0002 增加 EXISTS 守卫 |
| 3 | clean 源码树找不到 EABase/EAAssert 头 | 上游 CMakeLists 用 plain-name 链接，无目标传播 | recipe `generate()` 用 `self.dependencies[...].cpp_info.includedirs` 注入 `-I` |
| 4 | EAThread 头文件缺失（`eathread_atomic.h` 等） | eathread 未发布到制品仓 | **外部依赖阻塞**，已在依赖分析记录恢复条件 |
| 5 | EAThread 在 OHOS 编译失败（本地测试树） | OHOS musl 无 `pthread_setaffinity_np`/`pthread_getaffinity_np`/`pthread_setcancelstate`，仅 `sched_setaffinity` | 本地测试树已适配（`__OHOS__` 分支走 `sched_setaffinity(0,...)`/`syscall`）；EAThread 自身为独立待适配包，不作为本库补丁提交 |
| 6 | 上游 EABase 测试树 aarch64 未定义 `EA_SYSTEM_LITTLE_ENDIAN` | 官方 eabase 配方的 OHOS 补丁未随测试子模块 | 本地测试树同步该定义（与已发布 eabase/0699a15 配方等价） |
| 7 | EAStdC 调试 `operator new[]`(6 参) 未定义（消费者链接） | Config.h 契约要求 user-provided（上游 EAStdCTest.cpp 同款提供） | test_package 增加 `ea_allocator_impl.cpp` 契约实现（消费者侧，非修改被测库） |

## 源码修改
- patches/0001-cmake-min-version-3.5.patch（CMake 4.x 兼容，portability）
- patches/0002-guard-commoncppflags-include.patch（clean 源码树配置修复，portability）

## 依赖版本
- EABase 0699a15（制品仓已发布 eabase/0699a15）
- EAAssert e5e1812（**待发布**）
- EAThread a77e227（**待发布**）
- 测试子模块 EAMain 24ca8bf / EATest a59b372 / EASTL e323f67（仅测试构建用）

## 验证结果

### 上游测试（双口径台账）
- 源码声明独立用例（`int TestXxx()` 顶层测试函数）: **21**
- 注册/执行（EAStdCTest.cpp `AddTest`）: **21**，全部实际运行
- 结果: **21/21 PASSED**, RETURNCODE=0（TestEndian/TestDateTime/…/TestInt128）
- 日志: `reports/upstream-test-run.log` SHA-256 `d86bbcdb366be8c6b56a07d3072c17866f2046968c7569f59284ab7a51bff49b`
- 通过率: 21/21 = 100%（执行集 == 声明集，无未实例化项）

### 消费者验证（公开 API，仅 public 头文件）
- 5 项检查全部通过: CRC32 / Sprintf / Memclear+IsAligned / RandomLinearCongruential / UTF8Validate+UTF8Length
- 命令: `clang++ -std=c++17 … consumer_test.cpp libEAStdC.a`（含 ea_allocator_impl.cpp 契约实现）
- 退出码 0

### HarmonyOS 专项测试
- EA_SYSTEM_LITTLE_ENDIAN 定义 / ToBigEndian-FromBigEndian 往返 / int128_t 乘法
- 命令: `clang++ -std=c++17 … ohos_special_test.cpp libEAStdC.a`
- 退出码 0（ALL OK）

## 交付物
- archives/e/eastdc/0.0.0-fbcc34e/conanfile.py
- archives/e/eastdc/0.0.0-fbcc34e/conandata.yml
- archives/e/eastdc/0.0.0-fbcc34e/patches/0001-cmake-min-version-3.5.patch
- archives/e/eastdc/0.0.0-fbcc34e/patches/0002-guard-commoncppflags-include.patch
- archives/e/eastdc/0.0.0-fbcc34e/test_package/{conanfile.py,CMakeLists.txt,MANIFEST.yml,consumer_test.cpp,ohos_special_test.cpp,ea_allocator_impl.cpp}
- archives/e/eastdc/0.0.0-fbcc34e/reports/upstream-test-run.log

## 注意事项
- EAStdC 主库**编译期**无条件依赖 EAThread 头文件（EACallback.h/internal/Thread.h），不是仅测试依赖；
  EAThread 是独立的第三方库（electronicarts/EAThread），其 OHOS 适配（musl 缺 pthread_setaffinity_np 等 API）应作为单独任务完成。
- 本库不产出 CLI（构建产物仅 .a 静态库），按 R38 不创建 commands.json。
- 消费者侧须提供 EAStdC Config.h 契约的 user-provided 调试 operator new/delete（上游测试主文件同款做法），
  test_package 已包含 `ea_allocator_impl.cpp` 作为示例实现。
---

**编译结束**: 2026-09-18 12:22
**最终状态**: built

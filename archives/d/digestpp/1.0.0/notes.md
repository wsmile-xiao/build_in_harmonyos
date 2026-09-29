# digestpp 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 header-only INTERFACE 目标 + 官方安装规则）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，OHOS aarch64 profile）
- 状态: built

## 源码来源
- 上游: https://github.com/kerukuro/digestpp
- 上游无任何 tag/release（`git ls-remote --tags` 为空，GitHub API tags/releases 均为空列表），
  version 1.0.0 取自上游 `CMakeLists.txt` 的 `project(digestpp VERSION 1.0.0 ...)`。
- 固定官方 master commit `4beae7541f5c280389898ae6e6111028852f466a`（pushed_at 2026-02-14）
  作为 1.0.0 源码，conandata.yml 使用官方 commit tarball：
  `https://github.com/kerukuro/digestpp/archive/4beae7541f5c280389898ae6e6111028852f466a.tar.gz`
- tarball SHA-256: `47b68a98477a88ffb039d549b2497dfb1cb71d18f61017ed567de7bf9d75ffbe`（实算）

## 编译步骤
1. `ohc-run.py init-build digestpp 1.0.0 --url=<官方 commit tarball>` — 下载/解压/骨架
2. `ohc-run.py lang-preflight` — detected=cpp，通过
3. 手工编写 header-only 配方（conanfile.py / conandata.yml / test_package/）
4. `ohc-run.py conan-verify digestpp 1.0.0`（G0-G4 + L2/L4/L5 全过，含 conan create）
   - conan create 使用 `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, clang 15, libc++）
5. 上游测试按官方 `test/CMakeLists.txt`（find_package(digestpp 1.0.0)）对已安装制品构建并全量运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | LSH256/LSH512 全部测试向量在 -O2 下失败（-O0 通过） | 上游 `detail/functions.hpp` 的 `rotate_left(x,n)` 实现为 `(x<<n)|(x>>(32-n))`；LSH 的 G256/G512 旋转表中含 **n=0**（G256={0,8,16,24,...}, G512={0,16,32,...}），n=0 时 `x>>32`/`x>>64` 是移位越宽 UB。clang -O0 下硬件移位取模（32&31=0）恰好正确；-O2 下 LLVM 将 `x>>32` 视为 poison 并确定性折叠，导致全部 LSH 摘要错误（其余算法旋转常量无 0，不受影响） | 补丁 `patches/0001-fix-lsh-rotate-zero-shift-and-uninit-read.patch`：rotate_left 增加 `n ? ... : x` 零旋转保护（32/64 位两处），消除 UB，所有优化级别输出一致 |
| 2 | LSH init() 首次 transform 读取未初始化成员 | `lsh_provider::init()` 在 `memset(msgexp,0)` **之前**调用 `transform(msg,1)`，而 `msgexpand()` 从不写 `msgexp` 第 1 行 → 首次 transform 的 step(1) 读取未初始化内存（UB） | 同一补丁：把 `memset(t)`/`memset(msgexp)` 移到首次 transform 之前 |
| 3 | 消费者用例 blake2b 带 key 断言失败 | 测试预期值笔误（非库缺陷；Python hashlib.blake2b 独立核验确认库输出正确） | 修正 test_package/test_digestpp.cpp 预期值 |

> 上游 master（2026-02-14）与 pin 版本该文件完全相同，bug 在上游仍存在。上游 CI 默认无 -O 优化
> （CMAKE_BUILD_TYPE 未设）故未暴露；任何 Release(-O2) 消费者都会命中。补丁为真上游 bugfix，
> 无平台宏，可回馈上游。

## 依赖版本
- 无编译依赖（header-only，零依赖，W0 预检通过：ohpcd registry 无 digestpp 亦无需依赖发布）
- 工具链: conan 2.29.1 / cmake 4.1.2 / clang 15.0.4 / make 4.4.1

## 上游测试双口径台账（-O2 Release，对已安装补丁制品全量运行）

| 项目 | 数值 | 说明 |
|------|------|------|
| source_declared_total | 243 | 官方源码可复制枚举的独立用户用例：test.cc 148（90 个命名 compare + 57 个 update() 分块测试 + 1 个 XOF squeeze 测试）+ test_vectors.cc 95 个算法向量套件 |
| configured_executable_total | 3 | 上游 test/CMakeLists.txt 实际实例化 3 个可执行目标：examples / test / test_vectors |
| executed_passed_total | 243 | test 148/148 通过（Self-test completed with 0 errors）；test_vectors 95/95 套件通过（0 FAILED）；examples 作为样例冒烟运行通过（不计独立用例） |
| 失败数 | 0 | — |
| 未运行/未实例化 | 0 | — |

映射（源码声明 → 构建条件 → 构建目标 → 执行日志）：
- test.cc（148 项：`errors += !compare("NAME",...)` × 90、`update_test(...)` × 57、`xof_test(...)` × 1）
  → 无条件编译，`add_executable(test test.cc)` → `test` → `upstream-r2-test.log`（SHA-256
  `xxxxxxxx`，见最终报告）
- test_vectors.cc（95 项 `test_vectors(hasher, "name", "testvectors/*.txt")`，每套件一个文件，
  内含 6809 个 MD 向量数据行）→ `add_executable(test_vectors test_vectors.cc)` → `test_vectors`
  → `upstream-r2-test_vectors.log`
- examples.cc（10 个样例函数，非独立用例，仅冒烟）→ `add_executable(examples examples.cc)`
  → `examples` → `upstream-r2-examples.log`
- 全量通过率: 243/243 = 100%；当前配置可执行集合通过率 243/243 = 100%（无互斥分支/未实例化项）

## 鸿蒙专项测试
- test_ohos/run_ohos_test.c：通过已安装公开头文件调用 digestpp 公开 API（sha256/sha3/blake2b/
  shake256/skein512）验证真实摘要输出（独立于上游与消费者用例，见 test_ohos/）
- 消费者用例: test_package/test_digestpp.cpp（5 个公开 API 断言，见 test_package/MANIFEST.yml）

## 验证结果
```bash
# 上游测试（-O2，对已安装制品）
cmake -S test -B test/build_ohos_r2 -DCMAKE_PREFIX_PATH=<pkg> -DCMAKE_BUILD_TYPE=Release ...
cmake --build test/build_ohos_r2 -- -j4
./test/build_ohos_r2/examples     # exit 0
./test/build_ohos_r2/test         # "Self-test completed with 0 errors."  exit 0
./test/build_ohos_r2/test_vectors # 95/95 套件 OK，0 FAILED，exit 0

# 消费者
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 ... → test_digestpp 5/5 PASS
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | header-only cmake 配方（官方 commit tarball + SHA-256） |
| patches/0001-fix-lsh-rotate-zero-shift-and-uninit-read.patch | 上游 LSH UB bugfix（旋转 0 移位越宽 + init 未初始化读取） |
| test_package/ | 消费者用例 test_digestpp.cpp（5 断言）+ MANIFEST.yml |
| test_ohos/ | 鸿蒙专项测试 run_ohos_test.c |
| notes.md / manifest.yaml | 本笔记与版本级 manifest |

## 注意事项
- digestpp 为 header-only：conanfile package_type=header-library，产物仅头文件 + CMake config。
- 上游无 tag，版本 1.0.0 = 官方 master commit 4beae75（CMakeLists 声明 VERSION 1.0.0），
  conandata 固定该 commit tarball，避免漂移。
- 非 CLI 库（无 bin 产物），不生成 commands.json（R38 不适用）。
---

**编译结束**: 2026-09-28 10:25
**最终状态**: built

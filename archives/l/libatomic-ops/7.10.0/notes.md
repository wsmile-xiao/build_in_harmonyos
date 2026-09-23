# libatomic-ops 7.10.0 — 适配笔记

> 创建时间: 2026-09-14
> 分支: feat/libatomic-ops-7.10.0
> 状态: 工作树已完成，待 HMBS 真机预检（未提交、未推送、未建 PR）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libatomic-ops |
| 版本 | 7.10.0 |
| 上游 | https://github.com/bdwgc/libatomic_ops |
| 发布页 | https://github.com/bdwgc/libatomic_ops/releases/tag/v7.10.0 |
| 构建系统 | CMake |
| 源码包 | libatomic_ops-7.10.0.tar.gz（543312 字节） |
| sha256 | 0db3ebff755db170f65e74a64ec4511812e9ee3185c232eeffeacd274190dfb0（FreeBSD FreshPorts distinfo；md5 与发布页 1de9631daa0781a8c5a8457053d57cf0 一致） |
| 依赖 | 无（仅系统 pthreads） |
| 包名说明 | 本任务目录用连字符 `libatomic-ops`；历史归档 `libatomic_ops`（下划线，7.8.2）是另一个 Conan 包名，本 PR 只动新目录 |

## 二、上游测试清点（R51 申报表）

上游 CMakeLists.txt（v7.10.0）在 `BUILD_TESTING` 为 ON 时注册：

| ctest 用例 | 来源 | 说明 |
|------------|------|------|
| test_atomic | tests/test_atomic.c | fetch_add、CAS、屏障 |
| test_atomic_generalized | tests/test_atomic.c（AO_PREFER_GENERALIZED + AO_TEST_EMULATION） | 通用化仿真路径 |
| test_atomic_pthreads | tests/test_atomic.c（AO_USE_PTHREAD_DEFS） | pthread 定义路径（OHOS 有 pthreads，应构建） |
| test_stack | tests/test_stack.c | 无锁栈 |
| test_malloc | tests/test_malloc.c | 原子 malloc |
| 合计 | | 5 |

7.10.0 变更：“Build tests by default in CMake script；Replace CMake build_tests option to standard BUILD_TESTING；Rename BUILD_SHARED_LIBS to AO_BUILD_SHARED_LIBS”。因此配方用 `AO_BUILD_SHARED_LIBS` + `BUILD_TESTING=ON`，`build()` 末尾跑 `ctest --output-on-failure`。

test_package 消费者测试（test.c，8 功能组、14 个 assert）：
1. AO_fetch_and_add1；2. AO_fetch_and_add；3. AO_store/AO_load；
4. AO_compare_and_swap 成功+失败；5. AO_test_and_set/CLEAR；
6. AO_pause（libatomic_ops 链接证明）；7. AO_malloc/AO_free（GPL 库链接证明）；
8. AO_stack_push/pop + is_empty。

## 三、配方要点

- `conanfile.py`：CMake；`settings` 四项齐全；`options shared/fPIC` 默认静态；`generate()` 只设 `AO_BUILD_SHARED_LIBS / BUILD_TESTING / enable_docs=OFF / enable_gpl=ON`；`build()` 按 configure→build→ctest 顺序；`package_info().libs = ["atomic_ops", "atomic_ops_gpl"]`；无 `requirements()`（无依赖）；无 `url = ""` 残留；无占位符。
- `conandata.yml`：`url` 为有序列表，gh-proxy 镜像在前、官方在后；`sha256` 不变（镜像与官方同一归档）。
- 无 `patches/`：CMake 构建不需要 config.guess/sub；7.8.2 的两个 autotools 补丁不适用。
- `test_package`：CMakeDeps+CMakeToolchain；`build()` 编译；`test()` 先 `cmake.test()` 再 `self.run` 真二进制；随后输出 `HMBS_TEST_PACKAGE_RESULT`（8/8）并重发 `HMBS_UPSTREAM_TEST_RESULT`（5/5，防缓存命中丢证据）。
- 证伪计划（真机轮执行）：① 确认 ctest 输出含 5 个 Passed 且参照非空；② 必要时把被测二进制换成 `exit 1` 桩重跑，确认 harness 能抓失败；③ 区分通过与静默跳过（pthreads 缺失会导致用例数变 4，届时按跳过计，不计通过）。

## 四、对话记录

### 对话 #1 — 2026-09-14
**操作**：同步上游 main，切出 feat/libatomic-ops-7.10.0；按 7.8.2 经验 + 7.10.0 CMakeLists 重写配方（ctest 接入 + 双 HMBS 标记 + 镜像列表）；写 pr-body 草稿。
**结果**：工作树文件齐备，未提交。
**发现的问题**：Windows 大小写不敏感导致 `archives/l/libXext` 与 `archives/l/libxext` 在本机碰撞为一个目录，`git status` 显示两处 modified，属检出 artifact，与本任务无关，未触碰。
**当前状态**：待 HMBS 真机预检（conan create + ctest 5 + test_package 8）。
**遗留问题**：pr-body 中测试数字待真机 evidence 回填；若 ctest 在真机出现平台相关失败，按“先低成本补齐、补不齐再如实放弃”处理。

### 对话 #2 — 2026-09-14（真机 compile 失败修复轮）
**真机证据**：preflight.sh[306] 报 `/tmp/shed7k5y.tmp: Read-only file system`（readonly_tmp）；`CMakeLists.txt:34 project()` 处 `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 配置失败，`System is unknown to cmake, Platform/HarmonyOS`。
**根因**：conan CMakeToolchain 把 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，worker 的 vanilla cmake 4.4.3 无此平台模块，编译器识别失败；叠加配方从未转发 HMBS 注入的可写 TMPDIR，clang 临时文件回退到只读 /tmp，且 `self.run` 经 `/bin/sh -c` 同样写只读 /tmp。
**改动**：主配方与 test_package 均去掉 CMake/CMakeToolchain/cmake_layout，改用配置编译器直接编译（复刻上游 CMake 语义：-Wall -Wextra/-D_REENTRANT/-DNDEBUG、intrinsics 保持开启、静态 ar 归档、共享版 SONAME 1/VERSION 1.3.0）；全链路经列表式 `_run_noshell`（subprocess 直调，不经 shell）并转发 TMPDIR/TMP/TEMP；上游 5 用例在 build() 内逐个编译运行，rc==0 且输出非空才计通过并输出 HMBS_UPSTREAM_TEST_RESULT；签名为尽力而为且无 shell。
**当前状态**：工作树已改，保持未提交，待 HMBS 真机预检。

### 对话 #3 — 2026-09-14（source() AttributeError 修复轮）
**真机证据**：`Error in source() method, line 66, _tmp = self._writable_tmpdir(self.base_source_folder), AttributeError: 'LibAtomicOpsConan' object has no attribute 'base_source_folder'`。
**根因**：真机 conan 版本/上下文中 source() 阶段尚无 `base_source_folder`（`build_folder` 同样不可用），直接引用即抛异常，与上游源码无关。
**改动**：`_writable_tmpdir()` 去掉 base 参数，改经环境变量/HMBS 回退/cwd 推导可写目录，不再触碰任何 `self.base_*`/`self.build_folder`；`_run_noshell` 的 cwd 同样经 getattr 回退。策略不变（仍是直接编译 + noshell + TMPDIR 转发），只是修复 helper 的上下文兼容性。
**当前状态**：工作树已改，保持未提交，待 HMBS 真机预检。

### 对话 #4 — 2026-09-14（package() 头文件子目录修复轮）
**真机证据**：上游 5/5 已通过（direct-cc）；test_package 编译失败 `fatal error: 'atomic_ops/sysdeps/gcc/aarch64.h' file not found`（atomic_ops.h:382）。
**根因**：package() 三次 copy 均用 keep_path=False，把 `src/atomic_ops/` 下头文件拍平，`sysdeps/gcc/` 等子目录结构丢失。
**改动**：顶层头文件保持 keep_path=False；`src/atomic_ops/` 改用 keep_path=True 递归复制，保留子目录树（与上游 CMake install 布局一致）。
**当前状态**：工作树已改，保持未提交，待 HMBS 真机预检。

## 五、源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| 无 | CMake 直编，无需改源码 | — | 无 patches/ |

## 六、结束记录

- 最终状态：工作树完成，保持未提交；等真机门禁。
- 真机信息（仅内部）：HarmonyOS PC 真机与官方 CI 同源，预检由 HMBS 后台统一执行；本轮不自行拼 rsync/ssh，不碰回环地址。

# snitch 1.2.3 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMakeLists.txt，设备 CMake 4.1.2）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 / clang++（profile `tools.build:compiler_executables`）
- 状态: built

## 编译步骤

1. **原生构建 + 上游测试**（设备侧，不进配方）：
   ```bash
   cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release -DSNITCH_DO_TEST=ON \
         -DSNITCH_UNITY_BUILD=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   cmake --build <build> -j4 --target snitch_runtime_tests snitch_approval_tests snitch_runtime_tests_self
   # 按上游工作目录约定直跑三可执行（详见 test_package/MANIFEST.yml）
   ```
   源码物化见「问题 1/2」：必须是 `…/snitch/tests/…` 布局 + git 检出。
2. **Conan 配方**（对齐 CCI `recipes/snitch/all`，同源 URL/sha256）：
   ```bash
   conan create archives/s/snitch/1.2.3 \
     -pr:h=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 \
     -pr:b=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 --build=missing
   # → rc=0；test_package: success: all tests passed (4 test cases, 18 assertions)
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | approval 套件 0/3 过、734/2782 断言失配（期望 `*testing_reporters.cpp:*` vs 实测完整绝对路径） | 归一化正则 `(.+/snitch/tests/…)` 硬编码上游 CI checkout 目录名 `snitch`；解包目录 `snitch-1.2.3.work` 不匹配 → 归一化完全不生效 | 源码复制到 `$TASK_DIR/native-src/snitch/`（路径含 `/snitch/tests/`）重编译；**DRAFT-E745** |
| 2 | 修完 1 后仍 11/2782 失配（期望 `v*`/`*.snitch` vs 实测 `v1.2.3`/`1.2.3.snitch`） | 版本归一化正则要求 4 段 `X.Y.Z.<githash>`；CMakeLists 靠 `git log -1 --format=%h` 拼 `SNITCH_FULL_VERSION`，tag 归档无 .git 只有 3 段 | 复制树内 `git init && git add -A && git commit`（hash 值被归一化为 `*`，值无关）；**DRAFT-E745** |
| 3 | `conan create` graph 阶段 `Invalid: Current cppstd (17) is lower than the required C++ standard (20)`（rc=6） | CI profile 固定 `compiler.cppstd=17`，上游 target 全部 `cxx_std_20` + CCI validate `check_min_cppstd(20)` | recipe 与 test_package 的 `configure()` 覆盖 `self.settings.compiler.cppstd="20"`（arrow/abseil 先例）；**DRAFT-E746** |
| 4 | 设备 CMake 4.1.2 拒绝 doctest v2.4.9 的 `cmake_minimum_required<3.5`（FetchContent 子依赖） | CMake 4.x 移除 <3.5 兼容 | 原生测试构建加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（佐证既有 **DRAFT-E321**；配方 `SNITCH_DO_TEST=FALSE` 不拉 doctest，CI 不受影响） |
| 5 | 首版配方 `cmake.configure` 报 `src/ 无 CMakeLists.txt` | 手写配方漏了 `def source()`（导出后从未下载源码） | 补 `source(): get(self, **self.conan_data["sources"][self.version], strip_root=True)` |

## 源码修改

无补丁：上游源码零修改可在 OHOS/aarch64 构建（`patches: {}`）。

## 依赖版本

- 零运行依赖（W0-2 实查 CCI recipe 无 requirements/build_requirements；仅 system lib `m`）。
- 上游测试驱动：doctest v2.4.9（FetchContent，仅原生测试构建，不进配方/CI）。
- 设备工具：clang/clang++ 15.0.4、CMake 4.1.2、GNU Make 4.4.1。

## 验证结果

```bash
# 上游三套件（$TASK_DIR/native/，attempt3，沙箱 HOME）
approval-doctest: [doctest] test cases: 3 | 3 passed | 0 failed;  assertions: 2782 | 2782 passed | 0 failed
runtime-doctest:  [doctest] test cases: 102 | 102 passed | 0 failed; assertions: 3809 | 3809 passed | 0 failed
runtime-self:     success: all tests passed (104 test cases, 4574 assertions)
# 计数口径（四口径不混用，详见 test_package/MANIFEST.yml 与 reports/test-report.md）：
# 执行口径 N = 102 + 104 + 3 = 209；assertion 口径 = 3809 + 4574 + 2782 = 11165
# test_package（消费者/鸿蒙特有）：success: all tests passed (4 test cases, 18 assertions)
conan create archives/s/snitch/1.2.3 … → rc=0（local-create.log / local-create2.log）
```

## 注意事项

- 上游测试的两个隐含前提（目录名 + git 元数据）对任何 approval/快照套件通用，见 DRAFT-E745。
- `SNITCH_DO_TEST=FALSE` 为 CCI 同款口径：上游测试由设备原生构建独立运行并留档，
  配方侧由 test_package 从消费者视角验证已打包制品。
- snitch 断言计数含隐式 `no exception caught`（每次用例执行 pass 1 条，section 用例
  执行 2 遍得 2 条）——消费者 18 = 13 显式（版本指纹 4 + 其他 9）+ 5 隐式，勿与源码宏数混用。

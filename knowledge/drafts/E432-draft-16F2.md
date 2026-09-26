# E432 — 上游测试文件未被任何目标接入且缺 include：最小补丁纳入测试目标

## 错误特征
- 编译上游测试目标时报：
  `variable has incomplete type 'BuildConfig'` / `unknown type name 'StatusPrinter'`
- 或 `src/status_test.cc` 存在但从未被构建（不在任何测试目标注册表、`ninja_test` 注册数不含它）
- 典型日志：`ninja_test` 注册 409 → 补丁纳入后 411

## 触发条件
- 测试/工具：ninja 1.13.2 src/status_test.cc（上游 CMakeLists.txt 与 configure.py 均遗漏接线）
- 阶段：compilation/testing
- 平台：无关（上游遗漏模式，跨平台通用）

## 根因分析
上游仓库存在独立的测试文件（枚举得到测试声明），但未被 CMakeLists.txt / configure.py
的任何测试目标接入，且文件自身缺 `status_printer.h`/`build.h` include 导致无法编译。
按"源码测试入口恢复规则"：核对无上游排除条件后，以最小补丁将该文件纳入正确测试目标
（ninja_test），并补齐缺失 include，即可编译运行。

## 解决方案

### 推荐方案
最小补丁纳入 + 补 include：
```bash
# patches/0001-CMakeLists.txt.patch：ninja_test 目标追加 src/status_test.cc
# patches/0002-src-status_test.cc.patch：追加 #include "status_printer.h" / #include "build.h"
cmake -B build -DBUILD_TESTING=ON -DNINJA_FORCE_PSELECT=ON
cmake --build build --target ninja_test -j2
./build/ninja_test --gtest_filter=StatusTest.*   # 2 用例通过
```
注册数变化：409 → 411（纳入 status_test 2 个用例）。

### 禁止做法
- ❌ 为凑注册数把有明确上游排除条件的文件强行纳入（WIN32-only 的 includes_normalize_test/msvc_helper_test 保持未实例化）
- ❌ 只注册不编译、只编译不运行

## 验证
```bash
cmake -DBUILD_TESTING=ON; ./ninja_test --gtest_filter=StatusTest.*  # 2/2 通过
```

## 适用边界
- 适用：上游仓库存在但未接线测试文件的 C/C++ 项目（测试纳入关系补全）
- 反例：上游存在显式排除条件（WIN32 守卫、USE_PPOLL 守卫等）时不得强行纳入

## 查重差异
- exact_duplicate: false；causal_duplicate: false（E269/E301/E302 均不同测试执行面）
- test_migration_novelty: true —— 双口径台账中"未实例化→最小补丁纳入→注册数 409→411"的可复现迁移路径

## 关联条目
- similar_to: E269/E301/E302（测试执行面条目族）
- caused_by: 上游遗漏接线
- prerequisite_of: 双口径台账可执行口径准确
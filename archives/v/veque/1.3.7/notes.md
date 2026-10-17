# veque 1.3.7 适配笔记

## 编译环境
- 构建系统: custom（header-only：上游 tarball 无 CMakeLists.txt / Makefile / configure，配方不运行任何上游构建系统）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos，libc++；conan profile `ci/conan/profiles/ohos-aarch64`，cppstd=17）
- 状态: built

## Bootstrap 来源核验（2026-09-25，W0 生死关）

- 官方仓库: https://github.com/Shmoopty/veque （唯一上游；conan-center-index `recipes/veque` 同源）
- tag 实核: `git ls-remote --tags https://github.com/Shmoopty/veque` 命中
  `refs/tags/v1.3.7` → `112cc9381e671f481c57c559117fe524ce5ae5b7`（annotated tag）
  解引用 commit `426a63fe0906c03741c5153b6f101ba146503b82`
- 官方 tarball: https://github.com/Shmoopty/veque/archive/refs/tags/v1.3.7.tar.gz （150207 B）
- sha256（实测下载值，两种 URL 形态 `archive/refs/tags/...` 与 `archive/...` 同值）:
  `f67ae3ce3f3e16e60f63bc8d4df0c606a6dfbc8651e01cba5a6c4ed1209349b1`
  —— 与 conan-center-index `recipes/veque/all/conandata.yml` 的 1.3.7 全值逐字一致
- 依赖预检 W0: `w0-deps.txt = none`（头文件只 include C++ 标准库：algorithm/cstddef/cstring/
  iterator/limits/ratio/string/type_traits/stdexcept/utility，无外部依赖）
- 平台可移植性 W0-3: 全树 grep ISA 专属头（altivec/mmx/3dnow/immintrin/arm_neon/__asm__ 等）与
  glibc printf 钩子族（printf.h/register_printf_*）——**库本体 `include/veque.hpp` 0 命中**；
  仅 `test/catch.hpp` 有 6 处调试断点 trap 宏（Catch 的 CATCH_TRAP，按编译器/架构条件编译，
  属测试框架自身、且为备用路径档），实测编译运行全过 ⇒ 不在交付构建面上。
- 语言预检 R47（lang-preflight）: `cpp`，通过；prescan critical 命中 0。

## 编译步骤

1. `task_init.sh veque 1.3.7 --allow-unpublished`（新包三道闸已过）→ 分支 `feat/veque-1.3.7`
   基于 `upstream/main@32018bae04ef`，`origin` 为用户 fork。
2. `init-build --url <官方源>` 解源码到 `$WORKSPACE_ROOT/tmp/builds/veque-1.3.7.work`。
3. 配方（`archives/v/veque/1.3.7/`）：
   - `package_type = "header-library"`，`settings` 四项齐全，`no_copy_source`；
   - `source()` 走 conandata 官方源；`build()` 只 `apply_conandata_patches`（零补丁，不编译、不伪造日志 R34）；
   - `package()` 只拷 `include/veque.hpp` 与 `LICENSE`；`package_id` 清空；
   - `package_info()` 显式 `cmake_file_name=veque` / `cmake_target_name=veque::veque`，libs/bindirs/libdirs 置空；
   - `validate()` 在 profile 声明 cppstd 时 `check_min_cppstd(self, 17)`（上游 README 明示 C++17）。
4. 上游测试（`test/` 自带 catch.hpp）按 TU 编译 → 分程序链接 → 沙箱 HOME 实跑，
   细节与取数见 `reports/test-report.md`。
5. `conan create`（G2）+ `test_package` 消费者实跑（`self.run` 直跑，rc≠0 即失败）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试编译报 `fatal error: 'veque.hpp' file not found` | 测试源 `#include "veque.hpp"`（相对名），库头在 `include/`，首版命令只给 `-I test` | 编译命令同时给 `-I <src>/test -I <src>/include`；逐 TU 判 rc |
| 2 | 多 TU 一次链接报 `ld.lld: duplicate symbol: val<...>` | `test/test_types.h` 对变量模板做**无 inline 的显式特化**（`template<> const std::string val<std::string,0> = ...`），每 TU 出强符号；上游无构建系统、从未把它们链在一起（上游构建缺口，非平台问题） | **按 TU 分程序**：`main.o` 分别与每个测试 `.o` 链成 10 个程序逐个运行；不改上游源码、不加 `--allow-multiple-definition` |
| 3 | 计数直觉（源码 `TEST_CASE(` = 10）与实跑（800 case）不一致 | 上游用 Catch2 模板用例宏：9 处 `TEMPLATE_PRODUCT_TEST_CASE` + 1 处 `TEMPLATE_LIST_TEST_CASE`，一处宏按「模板 × 类型组合」展开几十上百 case | 四口径分列：源码宏 10 / 框架注册 800 / 实跑 800 / assertion 13762477，**N 取最大候选 800** 并按文件逐项归因差额（表见 `reports/test-report.md`） |
| 4 | `init-build` 对本包三件模板（conanfile/conandata/test_package）全部「模板不可用，跳过」，且生成的 manifest 占位含 `status: published` | 工具按猜测的 `build_system=autotools` 找模板名，header-only 模板未接入；无构建文件的包本就没有对应模板 | 手工按 header-only 模板与仓库既有示例逐项生成并审查（工具生成 ≠ 正确）；manifest 占位全部改写、`status: "built"`（O5）。已记 `feedback/pending/2026-09-25-veque-1.3.7.md` F1 |

## 源码修改

- **无补丁、源码零修改**：`patches: {}` / `patches_applied: []`，
  `git diff upstream/main...HEAD` 中不含上游源码与 `test/` 路径。

## 依赖版本

- 无外部依赖（W0 `w0-deps.txt = none`）；构建/测试仅用设备自带 clang 15.0.4、cmake 4.1.2 与上游自带单头测试框架。

## 验证结果

- 上游测试：10 个测试程序 / **800 case 全过**（PASS 800，FAIL 0，SKIP 0，NOT_RUN 0），
  断言 13762477；通过率 800/800（100%）。取数与逐程序明细见 `reports/test-report.md`。
- 消费者测试（`test_package`）：`VEQUE-CONSUMER checks=67 failures=0`，rc=0；通过率 67/67（100%）。
- Conan 侧：`conan create` 冒烟 rc=0（`Packaged 1 '.hpp' file: veque.hpp`）；采信轮（清缓存干净轮）
  与 finish 证据按 §3.3 固序执行，见 `$TASK_DIR/evidence-index.json`。

```bash
# 上游测试（沙箱 HOME）
HOME="$TASK_DIR/test-home" "$TASK_DIR/upstream-test/bin_test_vector_parity"
# → All tests passed (1332153 assertions in 48 test cases)  rc=0
# 消费者测试
HOME="$TASK_DIR/test-home" ./test_veque
# → VEQUE-CONSUMER checks=67 failures=0  rc=0
```

## 注意事项

- header-only：conan-verify 的 G4/L2/L4/L5 对本包走「跳过」分支（设备事实 §二.17 已知形态，
  自动 ✅ 与跳过并存时以跳过为准）→ 按口径做人工补测，写 `reports/conan-verify-supplement.md`。
- `finish` 内嵌 G0（clean_verify）会报「未找到任何构建入口」——本包无构建系统，属预期非阻塞告警
  （manifest `build.system: custom` 已声明）。
- 上游测试断言数受 `rand()` 驱动，逐次运行的 assertion 计数会浮动；**case 计数恒定 800**，
  对账以 case 口径为准（assertion 只作附注）。

---

**编译结束**: 2026-09-25 23:20
**最终状态**: built

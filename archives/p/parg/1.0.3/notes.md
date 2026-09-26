# parg 1.0.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，aarch64-unknown-linux-ohos）+ cmake 4.1.2
- 状态: built

## 编译步骤

Conan 配方走标准 CMake 链（`templates/conanfile-cmake.py.tmpl` 形态）：

```bash
conan create archives/p/parg/1.0.3 \
  -pr:h=$HOST_PROFILE -pr:b=$HOST_PROFILE -c tools.build:jobs=4
```

- `generate()`：`CMakeToolchain` 注入 `BUILD_SHARED_LIBS=OFF`（默认静态）与 `BUILD_TESTING=ON`
  （上游 `include(CTest)` 注册 `test_parg`）。
- `build()`：`cmake.configure()` → `cmake.build()` → `can_run(self)` 时
  `cmake.test()` 跑上游 CTest 注册的 greatest 套件，随后直跑一次 `test_parg`
  把 greatest 汇总行（32 用例 / 196 断言）打进 `conan create` 日志。
- `package()`：**上游 CMakeLists.txt 没有 install() 规则**，`cmake.install()` 是空操作，
  因此按构建树显式 `copy()`：`include/parg.h`、`lib/libparg.a`、`licenses/LICENSE`。
- `test_package/`：消费者二进制 `test_parg` 以 `link|short|long|reorder` 四个子命令注册
  4 个 CTest 条目，全部针对**已安装制品**（`find_package(parg)` → `parg::parg`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 把本包 `BUILD_SYSTEM` 判成 `autotools`，`conan-init` 随之套用 autotools 模板生成 `AutotoolsToolchain` 配方 | `scripts/ohc/init_build.py::_guess_build_system()` 只按 **URL 关键词**猜（URL 不含 "cmake" 即回落 `autotools`），`conan_recipe.py::_detect_build_system()` 又把该环境变量放在**第一优先级** | 以 `lang-preflight`（manifest→构建系统→源码统计三级）与 `prescan` 的实测读数 `build_system=cmake` 为准，改用 `templates/conanfile-cmake.py.tmpl` 形态重写配方；`manifest.yaml` 两处 `build_system/build.system` 钉 `cmake`（`clean_verify` G0 探测链 CMake > meson > configure > Makefile 才会走对入口）。已取知识号 `DRAFT-E734` 沉淀 |
| 2 | 上游无 `install()` 规则，`cmake.install()` 不产出任何文件（G4 产物完整性会空手） | 上游 `CMakeLists.txt` 只有 `add_library(parg parg.c parg.h)` + 测试目标，从未写 `install()` | 不加补丁（R1：能不改上游就不改），`package()` 显式 `copy()` 头/库/许可证 |
| 3 | 上游测试只有 CTest 注册的 1 个条目，日志汇总行只显示 `out of 1`，正文计数没有可复算的设备证据 | `ctest` 汇总按**注册条目**计数，greatest 的 32/196 只打印在测试程序 stdout | `build()` 在 `cmake.test()` 之后直跑一次 `test_parg`，让 greatest 汇总行进 `conan create` 日志（`reports/conan-create.log`） |

## 源码修改

无（零补丁，上游文件一个都没改；`patches_applied: []`）。

## 依赖版本

- 运行依赖：**零**（上游 CMakeLists 无 `find_package`、无外部链接库；W0 `grep` 实核）
- 构建工具：clang 15.0.4 / cmake 4.1.2 / GNU Make 4.4.1（设备 HNP 自带）

## 验证结果

```bash
# ① 本地 conan create（配方自包含 + 上游测试 + test_package）
conan create archives/p/parg/1.0.3 -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 -c tools.build:jobs=4
#   → rc=0；上游 greatest：Total: 32 tests, 196 assertions, Pass: 32, fail: 0, skip: 0
#   → test_package：100% tests passed, 0 tests failed out of 4

# ② 沙箱 HOME 原生跑上游套件（HOME=$TASK_DIR/test-home，空环境 env -i）
ctest --test-dir build-upstream --output-on-failure    # 1/1 Passed
./build-upstream/test_parg                             # 32 tests / 196 assertions 全 PASS

# ③ 采信轮（清缓存后干净构建）
sh tools/conan_verify_round.sh parg 1.0.3 --repo $TARGET_REPO --task-dir $TASK_DIR
#   → 见 reports/conan-create.log 与 evidence-index.json
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `include/parg.h` | 7329 B | 公共头（含 `PARG_VER_STRING "1.0.3"`） |
| `lib/libparg.a` | 8800 B | 静态库（`BUILD_SHARED_LIBS=OFF`） |
| `licenses/LICENSE` | — | MIT-0 许可证 |

## 注意事项

- 本包为**新包**（`upstream/main` 无 `archives/p/parg`），`task_init.sh` 带 `--allow-unpublished` 初始化；
  分支 `feat/parg-1.0.3` 满足「分支名去前缀 == 包目录名-版本」的 CI 门禁。
- `manifest.yaml` 状态保持 `built`（O5：合并 + release upload 确认前不标 `published`）。
- 测试计数口径：上游 N=32（`RUN_TEST` 注册数 = `TEST` 宏数 = greatest 汇总 `Total`，三口径一致；
  196 是 assertion 数，单列不与用例数混）；消费者 4 用例 / 44 断言计「鸿蒙特有测试」行，不进上游分母。

## 最终状态

- 状态: built（采信轮 + finish built，详见 `reports/`）
- W4 独立审计: 见 `reports/audit-result.json`（工作区 ignored 证据，不入库）
- 最终状态记录时间: 2026-09-25

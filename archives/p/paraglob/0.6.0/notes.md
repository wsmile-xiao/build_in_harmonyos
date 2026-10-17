# paraglob 0.6.0 适配笔记

## 编译环境
- 构建系统: cmake（**非** autotools——见问题表 #1）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 / clang++（`/data/service/hnp/bin/`，设备无 `cc`/`c++`/`gcc`）
- 状态: built

## 编译步骤

原生（设备侧实测，证据 `$TASK_DIR/w0/native-build.log`）：

```bash
CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
cmake -S . -B build-ohos \
      -DCMAKE_INSTALL_PREFIX="$TEST_PREFIX" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
      -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
cmake --build build-ohos -- -j4
cmake --install build-ohos
```

三段 rc 全 0；`cmake --install` 后清点安装树 **6 件**：

| 路径 | 说明 |
|---|---|
| `bin/paraglob-test` | 上游 CLI/benchmark 驱动（btest 套件被测程序） |
| `lib/libparaglob.a` | 静态库（内含 vendored `src/ahocorasick/` 目标文件） |
| `include/paraglob/{exceptions,node,paraglob,serializer}.h` | 4 个公开头 |

配方侧：`manifest.build.system: cmake` → `conanfile.py` 走 `cmake_layout` +
`CMakeToolchain` + `CMake` 三件套，`package()` = `cmake.install()` +
拷 `COPYING` 到 `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 把本包判成 autotools（`manifest.build_system=autotools`、`.build-context` 写 `BUILD_SYSTEM=autotools`、conanfile 模板提示「autotools 模板不可用」） | 上游根目录的 `configure` 是**CMake 便捷包装脚本**（`# Convenience wrapper ... Adapted from Bro's wrapper`），init-build 的构建系统探测见 `configure` 即判 autotools；而 `_detect_build_system()` 中 **`BUILD_SYSTEM` env 优先级高于 `manifest.build.system`**，错误值被固化 | 手工把 `manifest.yaml` 的 `build_system` 与 `build.system` 改 `cmake`，跑 `conan-init` 时显式 `export BUILD_SYSTEM=cmake`（不 source `.build-context`），模板随之切到 `conanfile-cmake.py.tmpl`。知识 **E707** |
| 2 | 设备无 `cc`/`c++`，CMake 编译器探测可能落空 | 设备 PATH 只有 `clang`/`clang++` 绝对路径（`/data/service/hnp/bin/`），无 `cc`、`gcc` 别名 | 原生构建显式传 `-DCMAKE_C_COMPILER/-DCMAKE_CXX_COMPILER` 绝对路径；配方侧由 profile `tools.build:compiler_executables` 经 CMakeToolchain 注入，无需补丁 |
| 3 | 上游 btest 套件 **4/4 全部失败**，报 `btest-diff: TEST_DIFF_CANONIFIER failed` + `/tmp/test-diff.$$.tmp: Read-only file system` | `/tmp` 只读（device-facts §一.1）而 `btest-diff` 第 189/204 行**硬编码** `/tmp/test-diff.$$.*.tmp`：规范化输出写不进去 ⇒ **比对从未执行**却判失败（假绿的镜像形态——假红） | 按 §一.1 口径「改到可写目录」：把 ohpcd 的 btest 包 `bin/` 整套复制成**任务私有副本** `$TASK_DIR/btest-bin/`，仅把两处 `/tmp/` 改成 `${TMPDIR:-/tmp}/`（原 conan 缓存文件 sha256 未动，`7a9dd830…e9c61c` 原样），私有副本置于 PATH 首位后真实重跑 → **3/4 通过**。知识 **E706** |
| 4 | 唯一失败 `driver.time` 输出 `Failed.` vs 基线 `Passed.` | 该用例是**墙钟性能阈值断言**（`paraglob-test -b 10000 20000 10 3` ⇒ build+search 合计 ≤ 3s 才打 `Passed.`），非功能断言；源码 0 处 `assert(`，与 NDEBUG 无关 | 定量实测归因（见「验证结果·非 PASS 段」）：build 1.655–1.770s + search 1.287–1.413s = **3.028–3.068s**，骑在 3.0s 阈值上 1–2% ⇒ 随上游随机工作负载（`std::random_device` 每次播种不同）在 `Passed./Failed.` 间抖动。**按四分项如实计 FAIL**，替代验证 = 小规模对照 5/5 通过 + 吞吐实测 114648 queries/s。知识 **E708** |
| 5 | 首次 btest 运行 `.tmp` 残留失败产物 | 复跑未清 `.tmp` 会让上一轮失败状态污染判读 | 每轮 `rm -rf .tmp` 后重跑，并保留 `.tmp/driver.*` 全套 `.diag/.log/.stdout/.stderr` 作证据 |

## 源码修改

**无。零补丁。** 依据：
- W0-3 平台判据四族（ISA 专属头 / glibc printf 钩子 / 内联 asm / 平台分支+字节序）
  **全部 rc=1 零字面命中**（`$TASK_DIR/w0/w0-3-platform-grep.txt`）；
- 原生 cmake configure/build/install 三段 rc=0，无需任何源码或构建脚本改动；
- `conandata.yml` `patches: []`、`manifest.yaml` `patches_applied: []`。

## 依赖版本

- **运行/编译依赖：空集**（W0-2）。Aho-Corasick 是 vendored 源码
  （`src/ahocorasick/{AhoCorasickPlus,ahocorasick,mpool,node,replace}.*`，
  经 `src/ahocorasick/CMakeLists.txt` 编进本包），`find_package` /
  `pkg_check_modules` / `ExternalProject` / `FetchContent` / `pkg-config`
  全部零命中，`requirements()` 为空。
  动态面：`conan install --build=missing -pr:h/-pr:b`（双绝对路径 profile）
  rc=0 且依赖图只有 consumer 一个节点 —— 证据 `$TASK_DIR/w0/w0-2-conan-install.txt`。
- 工具链：profile `ci/conan/profiles/ohos-aarch64`（clang 15 / libc++ /
  cppstd=17 / build_type=Release）。
- 测试侧 harness：`btest/1.0.0`（**仅设备侧验证用**，不入配方依赖图，
  故不计入上表的空集结论）。

## 验证结果

### 上游测试（btest 套件，与 test_package **分栏**）

驱动：`btest -c btest.cfg -d`（`TestDirs=driver`），被测程序 = 已安装的
`bin/paraglob-test`，比对基线 = `testing/Baseline/**`（`btest-diff`）。
证据 `$TASK_DIR/w0/btest-run.log`、`btest-diff` 私有副本 diff 前后 sha。

| 用例 | @TEST-EXEC 数 | 结果 |
|---|---|---|
| `driver.basic_matches` | 2 | PASS |
| `driver.empty_patterns` | 2 | PASS |
| `driver.serial` | 4 | PASS |
| `driver.time` | 2 | **FAIL**（见下） |

四分项：`TOTAL=4 = PASS 3 + FAIL 1 + SKIP 0 + NOT_RUN 0`；
btest-diff 断言数 5（serial 占 2），逐条归因：4 条 PASS、1 条 FAIL
（`driver.time/out`：`---Passed.` / `+++Failed.`）。

**非 PASS 段（driver.time，环境性能限制 + 替代验证）**

- 归因命令与读数（`$TASK_DIR/w0/bench-probe.body.md`、`bench-driver-time.log`）：
  - 明细模式 `-b 10000 20000 10 0` ×3：`Build time` 1.655/1.707/1.770 s、
    `Search time` 1.287/1.321/1.413 s，**合计 3.028 / 3.057 / 3.068 s**
    vs 上游阈值 **3.0 s**（超 0.9%–2.3%）；
  - 判定模式 `-b 10000 20000 10 3` ×20：`Passed.` **2/20**、`Failed.` 18/20，
    wall 3.467–3.870 s（均值 3.635 s）；
  - 小规模对照 `-b 1000 2000 10 3` ×5：**5/5 `Passed.`**；
  - 同规模功能明细 `-b 1000 2000 10 0`：`Build 0.120 s`、`Search 0.017 s`、
    **`Queries/second: 114648`**（功能路径正常）。
- 结论：**硬件墙钟性能阈值骑在本设备性能边界**，随机工作负载导致抖动；
  源码 0 处 `assert(`，与编译旗标/NDEBUG 无关；非功能缺陷、非适配缺陷。
- 替代验证：上述小规模对照 + 吞吐实测；库消费者 7 条 API 断言与
  CLI 消费者 4 条断言全部通过（覆盖同一功能路径）。

### test_package 消费者测试（鸿蒙特有测试）

| 分栏 | 断言数 | 结果 |
|---|---|---|
| 库消费者 `test_paraglob.cpp`（A1–A5 + A6a/A6b） | 7 | PASS |
| CLI 消费者 `test_cli.sh`（C1–C4） | 4 | PASS |
| **合计（= PR「鸿蒙特有测试」行）** | **11** | **11/11** |

本地预验（仅用安装后的头+库编译、直跑安装后的 CLI）见
`$TASK_DIR/w0/test_package-local-preverify.log`：compile rc=0、
`paraglob consumer: PASS`、`paraglob CLI consumer: PASS (4/4)`。

## 注意事项

1. **零补丁**，`patches/` 与 `patches_applied` 均为空——如后续返修补丁，
   按 `refresh_patch` 两面同步（conandata + manifest）。
2. `cmake` 配置期会打印 `System is unknown to cmake, create:
   Platform/HarmonyOS ...`——已知良性提示（设备 cmake 4.1.2 无 OHOS 平台
   模块），配置与构建均成功，不作失败判据。
3. 本包同时交付**库**与**CLI**：`package_type="library"` +
   `cpp_info.bindirs=["bin"]`，故按 R38/PF8/L0k 提供**软件级**
   `archives/p/paraglob/commands.json`（`type=tool`、`versions["0.6.0"].ref`
   = `paraglob/0.6.0`）。
4. `options.shared` 仅作 package_id 语义（上游 `add_library(... STATIC ...)`
   硬编码，`BUILD_SHARED_LIBS` 不影响产物），故 `generate()` **不注旗**。

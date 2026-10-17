# sexpp-cli 0.9.2 适配笔记

## 基本信息
- 上游：https://github.com/rnpgp/sexpp tag `v0.9.2`
  - tarball `https://github.com/rnpgp/sexpp/archive/refs/tags/v0.9.2.tar.gz`
  - sha256=`00c47b56a4dd5e80aba6b15df4e86d276a2a369737c6b467be1f51a9c29af31e`
  - （W0 双源实证：gh-proxy 信道与官方信道下载字节全等；gh-proxy 属镜像黑名单
    14 域，**验证信道不落盘**，conandata 只写官方 URL，classify=None）
- 构建系统：cmake（init-build 按 URL 猜 autotools 属误判，实测以 CMake 为准）
- 编译器：clang/clang++；产物：`bin/sexpp`（application 单二进制）
- 运行期 conan 依赖：**0 个**；`gtest/1.17.0` 仅 `test_requires`

## 一、父包归属判据（为什么本包不 requires 父包）

| 事实 | 读数 |
|---|---|
| 父包（库）在制品仓的版本 | `conan list "sexpp/*" -r=ohpcd` → **sexpp/0.8.7、sexpp/0.9.1 在档** |
| 目标版本 0.9.2 | **不在档**（任务卡 W0-2 实核） |
| 上游仓库形态 | 库与 CLI 同仓同 tarball（CMake 目标 `sexpp` 库 + `sexpp-cli` 可执行） |

判据取**制品归属**而非版本可得性：

1. 库制品（`libsexpp.a`、`include/sexpp/*`、`sexpp.pc`）归父包
   `archives/s/sexpp`；本包名 `sexpp-cli`，交付物就是 `bin/sexpp` —— 与
   `<父>-tools`/`<父>-cli` 子包家族（DRAFT-10251 两条路线表）同构，但本例
   **父包已有适配、只是版本不齐**（0.8.7/0.9.1 在档、0.9.2 缺席）。
2. 不 `requires("sexpp/0.9.2")`：该 ref 不存在，conan create 会直接
   `dependency_missing`（W0 止损判据 2）；也不降级 `requires("sexpp/0.9.1")`：
   交付的将是 0.9.1 库面 + 0.9.2 声明，版本错配（同 DRAFT-E618 forbid_3
   「不 requires 一个功能/版本不匹配的既有包」）。
3. 不在本 PR 升级父包（R36 升级父包是另一任务面，单包闸 PF1 也不允许一 PR
   动两个包目录）。
4. 因此：**源码整编**——下载 v0.9.2 tarball，`BUILD_SHARED_LIBS=OFF` 把
   libsexpp 静态内嵌进 CLI，`package()` 只拷 `bin/sexpp`（显式反静默：目标
   不存在即 `ConanException`），`package_info()` 清空 includedirs/libdirs/libs，
   包内不出现 `lib/`、`include/`，不与父包制品同名双份。
5. 归属反证：`cmake.install()` 会带出 lib/include/pc/man（父包面），故
   **不用** `cmake.install()` 交包（与「只交 CLI」判据直接冲突）。

## 二、接线：GTest_DIR 依据（上游测试如何在真机跑起来）

问题链：

- 上游 `WITH_SEXP_TESTS=ON` 时用 CMake `FetchContent` 从
  `github.com/google/googletest.git` 拉 googletest —— 真机不可达 ⇒
  **`DOWNLOAD_GTEST=OFF`**，改 `find_package(GTest REQUIRED)`；
- `DOWNLOAD_GTEST` 的 else 分支写死 **FindGTest 模块模式**目标
  `GTest::Main` / `GTest::GTest`，而 Conan **CMakeDeps 只导出
  `gtest::gtest` 命名** ⇒ 只靠 CMakeDeps 会在 `target_link_libraries`
  报「Target "sexpp-tests" links to target "GTest::Main" but the target
  was not found」；
- 修法（**依据 1 = W0 探针实证**）：`w0/gtest-probe/` 用最小 CMake 工程
  `find_package(GTest REQUIRED)` + `target_link_libraries(probe PRIVATE
  GTest::Main GTest::GTest)`，把 `GTest_DIR` 指到 conan gtest 包内
  `lib/cmake/GTest/GTestConfig.cmake`（googletest 上游安装产物，导出
  `GTest::Main`/`GTest::GTest` 别名），**configure+build rc=0**
  （cfg.log: `Found GTest: …/p/lib/cmake/GTest/GTestConfig.cmake
  (found version "1.17.0")`，bld.log: `Built target probe`）；
- **依据 2 = 父包 0.8.7 同法**：其配方 `generate()` 同样把 `GTest_DIR`
  钉到 `gtest.package_folder/lib/cmake/GTest`，`conan create` 实测通过。

配方落点（本包 conanfile.py `generate()`）：

```python
gtest = self.dependencies.get("gtest")
if gtest:
    tc.variables["GTest_DIR"] = os.path.join(
        gtest.package_folder, "lib", "cmake", "GTest").replace("\\", "/")
```

机制：`find_package(GTest)` config 模式**优先读 `<pkg>_DIR` cache 变量**，
确定性命中包内上游 config，不受 CMakeDeps 生成物/模块模式先后影响。

**采信轮 round-1 G2 红→修法（「探针绿/配方红」分叉的实测定位）**：
GTest_DIR 本身**已进** CMakeCache（`GTest_DIR:STRING=…/gtestf4671c6de073b/p/lib/cmake/GTest`，读数实证），
但 `conan_toolchain.cmake:137` 无条件 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`
⇒ conan create 下 `find_package(GTest)` 走 **config 模式**直载包内 `GTestConfig.cmake`，
而该 config（`GTestTargets.cmake`）只导出 `GTest::gtest / gtest_main / gmock…` 现代名、
**无** `GTest::Main / GTest::GTest` 旧别名 ⇒ `target_link_libraries` 报
「Target "sexpp-tests" links to: GTest::Main but the target was not found」
（round-1 首错，`CMakeLists.txt:270`）。W0 探针是**裸 cmake**（无 conan 工具链、
PREFER_CONFIG 未开）⇒ 走**模块模式**，设备 `FindGTest.cmake` 自建兼容别名
（`add_library(GTest::Main INTERFACE IMPORTED)`，模块内 323–328 行）⇒ 探针 rc=0
——两面分叉根因即此开关，与「变量没进工具链」无关。
修法按**父包 0.8.7 先例**加 `0002-CMakeLists-gtest-imported-targets.patch`：
else 分支 `if(TARGET GTest::Main)` / `if(TARGET GTest::GTest)` 双拼写条件兼容，
模块/配置两种模式都能链接；GTest_DIR 保留（钉死 config 来源，消除 CMakeDeps
小写 `gtest-config.cmake` 的歧义）。

捕获流复活（与接线同链）：gtest/1.17.0 含
`0001-tmpdir-ohos-sandbox.patch`，`CaptureStdout` scratch 只认 `TMPDIR`
（`TMP`/`TEMP`/`TEST_TMPDIR` 实测无效；`/tmp` erofs 只读）⇒ `build()`
跑 ctest 前 `Environment().define("TMPDIR", <build>/gtest-tmp)`，父包卡死的
2 个用例（`ExceptionTests.SexpWarning`、`G23ExceptionTests.G23Warning`）
在本包复活（W0 preview 70/70 实证）。

## 三、gtest 取数命令（复现/回查，全部设备可直跑）

```sh
# ① 在档核对（W0 实测：1.17.0 / 1.17.0.1 / 1.17.0.2 三版在册）
conan list "gtest/*" -r=ohpcd
# ② 双 profile install 冒烟（W0 实测 rc=0；profile 用绝对路径——相对名会命中
#    $CONAN_HOME/profiles 陈旧副本）
conan install --requires=gtest/1.17.0 \
  -pr:h "$PWD/ci/conan/profiles/ohos-aarch64" \
  -pr:b "$PWD/ci/conan/profiles/ohos-aarch64" --build=missing
# ③ 包目录回查：conan cache path 只给 export 目录（device-facts §二.17），
#    包 folder 在配方内用 self.dependencies["gtest"].package_folder 取；
#    手查：
ls -d "$HOME"/.conan2/p/gtest*/p/lib/cmake/GTest   # GTestConfig.cmake 所在
```

## 四、双口径测试台账（N 清点，§3.5）

- **N（源码宏清点，候选数法最大值）= 82**：
  `grep -c -E "(^|[[:space:]])(TEST|TEST_F)\(" tests/src/*.cpp` →
  baseline 3 / exception 24 / primitives 26 / g10 1 / g23 9 /
  g23-exception 7 / **traits 12** / compare-files 0（helper，无宏）。
- 上游 v0.9.2 的 `add_executable(sexpp-tests)` **仍遗漏 traits-tests.cpp**
  （与 0.9.1 同）→ 未补丁时 ctest 只实例化 70（W0 preview：
  `100% tests passed, 0 tests failed out of 70`，`70 tests from 6 test
  suites ran`）。差额 12 = 上游构建面遗漏，非环境不可跑。
- 处置：最小补丁 `0001-CMakeLists.txt.patch`（与父包 0.9.1 逐字节同款，
  dry-run/patch_ng strip=0 双证可 apply）纳入该文件 → 构建面 82，
  **ctest 实跑目标 82/82**（70 + 12；12 个 traits 用例在 0.9.1 同补丁下
  12/12 通过先例）。
- test_package 消费者断言 **3**（test.sh，分栏统计，不并入上游 N）。

## 五、实测与验证（最终读数以采信轮日志为准，回填于此）

- W0：四关全过（版本可得/依赖在档/平台 grep 三档 0/缺依赖 ∅）；
  双源 tarball sha 全等 + 同法取 0.9.1 sha == 父包 conandata 声明（信道内证）。
- 探针：`w0/gtest-probe/` configure+build rc=0；`w0/preview/` 原生整编
  + ctest 70/70 + 直跑 70/70 PASSED。
- CLI 行为（preview 二进制实测）：`sexpp -h` rc=0 打印帮助；`--version`/
  `--help` 报 `Unrecognized switch` rc=255（**无版本旗标，上游原样**）；
  `printf '(hello (world "42"))' | sexpp -c` → `(5:hello(5:world2:42))`
  rc=0；`-a` → 原样 advanced 格式 rc=0。
  - L2 冒烟门：官方探针只试 `--version`/`--help`（会判失败）；
    overlay 探针序列为 `--version/--help/-V/-h`，**`-h` 命中 rc=0 → PASS**
    （采信轮按任务书带 `OHC_FRAMEWORK_OVERLAY=1`）。CI 侧 L2 为 non-blocking。

## 六、源码修改

- `patches/0001-CMakeLists.txt.patch`：`sexpp-tests` 目标纳入
  `tests/src/traits-tests.cpp`（上游遗漏的测试入口，最小补丁，portability；
  与父包 sexpp/0.9.1 同款）。
- `patches/0002-CMakeLists-gtest-imported-targets.patch`：else 分支目标名
  `if(TARGET …)` 双拼写条件兼容（父包 0.8.7 同款；round-1 G2 首错的修复，
  机制见第二节「探针绿/配方红」段）。
- 无平台宏（`__OHOS__` 等）注入；上游源码其余零改动。
- 补丁应用序列已验：conan 实走 patch_ng strip=0 按 0001→0002 顺序双 True、
  终态与目标树逐字节一致；GNU patch -p1 双补丁终态同证。

## 七、知识沉淀（路径 B）

- 取号：`E720`（`knowledge_id.py --claim` rc=0，回查未被占用）。
- 草稿：`knowledge/drafts/DRAFT-E720-sexpp-cli-parent-version-gap-attribution.md/.kv`
  —— 「父包在档但目标版本缺席」的 requires 判据与交付面归属（对
  DRAFT-10251 / DRAFT-E618 的边界增量），manifest `knowledge_gained`
  逐条行尾 `# knowledge_ref: E720`。
- GTest 接线与 TMPDIR 面**不重复建条**：已有
  `DRAFT-fast-cdr-2.3.5-upstream-test-enablement`、
  `DRAFT-sexpp-0.8.7-gtest-capture-stdout-tmpdir-only` 覆盖（本笔记只引用）。

## 八、已知限制

- 上游 CLI 无 `--version`/`--help`（只有 `-h`）：不改上游选项面；
  L2 探针经 overlay `-h` 回退通过，详见五。
- 父包 sexpp/0.9.2 升级（R36）不在本任务面；如后续需要 0.9.2 库制品，
  按父包任务单独适配，届时本包可改 `requires` 收敛整编面。

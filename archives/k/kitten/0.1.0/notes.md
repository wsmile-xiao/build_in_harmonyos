# kitten 0.1.0 适配笔记

## 编译环境

- 构建系统: custom（**配方侧无库编译阶段**：header-only，`build()` 直调编译器按上游 `tests/CMakeLists.txt` 口径编译并真跑上游测试；上游根 `CMakeLists.txt` 是 `add_library(kitten INTERFACE)`，本配方不走其 CMake 配置/安装步骤）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`，libc++ **15004**）
- Conan profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / compiler=clang 15 / libc++ / **cppstd=17** / Release）
- 状态: built

## 编译步骤

1. `source()`：`get()` 下载 GitHub tag 归档（**tag `0.1.0` 无 v 前缀**，见 conandata 注释的三路 sha256 取证），`strip_root=True`；随后 `apply_conandata_patches()` 应用唯一 1 个补丁。
2. `build()`：按上游 `tests/CMakeLists.txt` 的编译口径（`-Wall -Wextra -Werror -ansi -pedantic` + `cxx_std_17`）把 5 个上游测试翻译单元（`main.cpp` + 4 个 `*_test.cpp`）一次编成单个 `kitten_tests` 可执行文件，`-ansi` 之后显式 `-std=c++17` 复现上游「`target_compile_features(cxx_std_17)` 覆盖 `-ansi`」的同一结果；随后以 `-r compact` 真跑，按 Catch2 汇总行解析 test cases / assertions，并与源码 `SCENARIO` 声明数**交叉核对**（不等、或解析到 0 用例即 `ConanException` 构建失败），结果以 `HMBS_UPSTREAM_TEST_RESULT={...}` 一行写进 conan/CI 日志。
3. `package()`：`include/kitten/**.h` → `include/`、`LICENSE` → `licenses/`；`package_type="header-library"` + `package_id()` 清空 ⇒ 单一 package ID（`info.clear()`，与 ohpcd 的 `catch2/2.13.10` 同形态）；`package_info()` 置空 bin/lib，`cmake_target_name = rvarago::kitten`（跟上游 README「`find_package(kitten)` + `rvarago::kitten`」与 `install(EXPORT … NAMESPACE rvarago::)` 一致，也与 conan-center-index 的同包配方同名）。
4. `test_package`：消费者从**已安装包头** `#include <kitten/...>` 实调 5 类实例面 21 项断言，`test()` 用 `self.run(..., env="conanrun")` 直跑（R34），显式计数、任一失败非零退出。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `tests/sequence_container_test.cpp` 在 clang 下编译失败：`no type named 'type' in 'std::enable_if<false>'` + `functor.h:58: no matching function for call to 'fmap'` | 上游把 SFINAE 守卫写成 `enable_if_sequence_container<容器模板>`（按**模板身份**判定），而 **clang 不把 alias 模板规范化为模板模板实参**（GCC 会）⇒ 测试里的 `template<class T,class A=…> using SequenceContainer = std::vector<T,A>` 对 `is_sequence_container<别名>` 恒 false；且该守卫不依赖成员模板参数 `A`，在实例化 `functor<别名>` 时被**急切求值**成硬错误（非 SFINAE）。最小探针：`t<std::vector>` 断言通过 / `t<别名>` 断言失败（`-std=c++17` 与 `-std=c++20` 结论一致） | 加 1 个 **portability 补丁**（`patches/0001-…`）：守卫改为按**实例化类型** `SequenceContainer<A>` 判定（新增 `is_sequence_container_type`，对 `std::vector/deque/list` 实例化为真、其它为假），并让守卫依赖成员模板参数 `A` ⇒ 保持 SFINAE 语义。**上游测试文件零改动**，4 个 `SCENARIO` 全部原样运行；`tests/sequence_container_test.cpp` 的 `liftF<别名>` 路径与消费者第 12 项断言专门回归该路径 |
| 2 | 上游自带 `conanfile.py` 用的是 **Conan 1 API**（`from conans import ConanFile`、`build_requires "catch2/2.5.0@bincrafters/stable"`） | 上游配方面向 Conan 1.x + bincrafters 源，本机为 Conan 2.29.1，制品仓也无该引用 | 不复用上游配方，按本仓库模板新写 Conan 2 配方；测试依赖改为制品仓实有的 `catch2/2.13.10`（`conan download … -r=ohpcd` 实证可得，`info.clear()` 单一包 ID） |
| 3 | header-only 包 `conan-verify` 的 G4/L2/L4/L5 走「跳过」分支却并列打 `✅ PASS` | 路径解析缺陷（`device-facts` §二.17，必然命中而非偶发） | 报告中的 `⏭️ 跳过` 一律按显式 SKIPPED 处理，人工补测写 `reports/conan-verify-supplement.md`（G4 产物清单↔`package_info()`、L2 真跑消费者二进制、L4 ELF 属性、L5 聚合 sha256） |
| 4 | 上游 `tests/CMakeLists.txt` 同时给 `-ansi` 与 `cxx_std_17` | `-ansi` 即 `-std=c++98`，与 C++17 冲突；上游靠 CMake 把接口目标的 `cxx_std_17` 覆盖上去 | 配方命令行按同一顺序复现：`-ansi` 在前、`-std=c++17` 在后（clang 后者生效），实测全绿（`-Wall -Wextra -Werror -pedantic` 亦全过） |
| 5 | `refresh-patch --auto` 每次生成 `patches/.patch-backup-<时间戳>/` 从不清理 | 工具行为（`device-facts` §四.17 已登记垃圾） | 每次生成后立即删除备份目录，避免 `os.listdir(patches)` 抛 `IsADirectoryError` 与 L4 补丁扫描重复计数 |

## 源码修改

`patches/0001-include-kitten-instances-sequence_container.h.patch`（**仅 1 个文件、1 个 hunk，+26/-7**）：

- **修改原因**：clang（鸿蒙唯一可用编译器）不做 alias 模板的模板模板实参规范化，上游按模板身份判定的守卫在类实例化期被急切求值为硬错误 ⇒ 上游自带的 `liftF<SequenceContainer>` 测试无法编译。
- **修改内容**：`detail` 命名空间新增 `is_sequence_container_type<T>`（对 `std::vector/std::deque/std::list` 实例化为真）；`enable_if_sequence_container` 的参数由「容器模板」改为「实例化类型」；`monad`/`applicative`/`functor` 三处共 5 个守卫位由 `<SequenceContainer>` 改为 `<SequenceContainer<A>>`。模板身份 trait `is_sequence_container` 原样保留（对外语义不变）。
- **接受/拒绝集合不变**：仍只接受 `std::vector`/`std::deque`/`std::list` 三种容器的实例化（含其别名），其它模板一律 SFINAE 掉；差别只在「别名形态由不可编译变为可编译」。
- **不涉及**：上游任何测试文件、`__OHOS__` 平台宏、镜像/`file://` URL（PF5/PF7 面全净）。

## 依赖版本

- 交付依赖：**0**（头文件树，仅依赖 C++17 标准库）
- 测试期（`test_requires`，不随包交付）：`catch2/2.13.10`（ohpcd 制品仓实证可得）

## 验证结果（R51 三步法）

**清点（用例数四种口径，逐文件；`SCENARIO` 为 Catch2 BDD 用例声明宏）**

| 文件 | 源码宏数（SCENARIO） | 框架注册数 | BDD section 声明 | CHECK 断言 | 状态 |
|---|---|---|---|---|---|
| `tests/main.cpp` | 0 | — | 0 | 0 | 入口（`CATCH_CONFIG_MAIN`），不计用例 |
| `tests/function_test.cpp` | 1 | 1 | 6 | 1 | 实跑 PASS |
| `tests/optional_test.cpp` | 1 | 1 | 28 | 16 | 实跑 PASS |
| `tests/sequence_container_test.cpp` | 1 | 1 | 28 | 24 | 实跑 PASS |
| `tests/variant_test.cpp` | 1 | 1 | 6 | 4 | 实跑 PASS |
| **合计** | **4** | **4** | 68 | 45 | 候选数法取最大值 ⇒ **N = 4** |

- **口径不混用**：分母取「测试用例（test case）」；BDD section（68）与断言（45）是另外两口径，逐项列示但不进分母。
- **上游当前 HEAD 下界**（rule4）：`git ls-remote` 取上游 HEAD `f45705bc3026551c702b05281cee940b51511dc1`，其 `tests/*.cpp` 同口径源码宏 = **4**（`CHECK` 断言 45）与被审版本相同，**≤ 声明 N=4**，无少报空间。

**运行（同一 SHA，采信轮干净构建；权威读数取 `reports/conan-create.log`）**

```text
kitten_tests -r compact → Passed all 4 test cases with 45 assertions.   rc=0
kitten_tests（默认 reporter）→ All tests passed (45 assertions in 4 test cases)   rc=0
test_package            → kitten consumer checks: 21 run, 0 failed            rc=0
```

- `TOTAL = PASS + FAIL + SKIP + NOT_RUN`：上游用例 **4 = 4 + 0 + 0 + 0**（无 NOT_RUN、无 SKIP）。
- 消费者断言 **21** 项单列（鸿蒙特有测试行），不进上游分母。

## 注意事项

- 上游 0.1.0 的 `.travis.yml` 走 Docker + `make env-test`（容器内 GCC 环境），与本设备/CI 的 clang 工具链不同——问题 #1 正是两套编译器对 alias 模板处理差异的直接体现。
- 本包无 `commands.json`（纯库包，PF8 要求纯库包不得有）。

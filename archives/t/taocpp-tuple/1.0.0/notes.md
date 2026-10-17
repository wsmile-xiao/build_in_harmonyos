# taocpp-tuple 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only，无编译产物）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（OHOS aarch64, os=OHOS 6.0, cppstd=17）
- 状态: built

## 编译步骤

```bash
# 初始化（官方 tag 1.0.0 归档, codeload.github.com）
python3 scripts/ohc-run.py init-build taocpp-tuple 1.0.0 --auto \
  --url https://codeload.github.com/taocpp/tuple/tar.gz/refs/tags/1.0.0
python3 scripts/ohc-run.py lang-preflight taocpp-tuple 1.0.0 --src <work>   # detected=cpp, EXIT 0
python3 scripts/ohc-run.py conan-init taocpp-tuple 1.0.0

# header-only 库无编译阶段；conan create 完整验证：
conan create archives/t/taocpp-tuple/1.0.0 -pr ohos-aarch64   # exit 0，见 .ci-result
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `BadZipFile: File is not a zip file` | codeload tag archive URL basename 无 `.tar.gz` 后缀，`get()` 误按 zip 解包 | `source()` 中显式 `src["filename"]="taocpp-tuple-1.0.0.tar.gz"`（同仓先例 ctl 3.0 / drwav E276） |
| 2 | test_package 报 `Imported target "taocpp::tuple" includes non-existent path .../include` | `package()` 中 `copy(self, "tao", ...)` 只按目录名匹配、未递归复制目录树 | 改为 `copy(self, "*", src=include, dst=include)` 递归复制，保留 `tao/` 相对路径 |
| 3 | 上游 Release 构建 `-Werror unused variable 't5'` | 上游 `-Wall -Wextra -Werror`；Release 定义 NDEBUG 使 `assert()` 编译为空，仅被 assert 引用的 `t5` 变成未使用变量 | 上游测试用 Debug 构建实际运行（assert 生效），见测试台账；不影响 header-only 配方与 CI |

## 源码修改

无补丁（header-only 库，纯头文件直接可用）。

## 依赖版本

无第三方依赖（header-only，conanfile.py `requirements()` 为空）。

## 上游测试全量枚举台账（双口径）

### 枚举规则
官方 tag 源码中，测试声明来自 `src/test/tuple/CMakeLists.txt`：
`test_sources = (tuple_benchmark.cpp, tuple_cat.cpp, tuple_main.cpp)`，
每个源文件 `add_executable(<exename>)` + `add_test(NAME <exename> ...)`。
CMake 另有 glob 校验：`src/test/tuple/*.cpp` 必须全部在 test_sources 中，
当前 3 个 cpp 全部登记，无被忽略源文件。

### 逐项台账（源码声明 → 构建目标 → ctest 注册项 → 实际执行）

| 源码声明文件 | 分类 | 是否独立上游用例 | 构建目标 | ctest 项 | 实际运行 | 结果 |
|---|---|---|---|---|---|---|
| `src/test/tuple/tuple_main.cpp` | 用户测试源（主功能性断言） | ✅ 是 | `tuple_main` | 1: tuple_main | ✅ Debug 构建运行 | PASS（31 断言） |
| `src/test/tuple/tuple_cat.cpp` | 用户测试源（tuple_cat 功能） | ✅ 是 | `tuple_cat` | 2: tuple_cat | ✅ Debug 构建运行 | PASS（13 断言） |
| `src/test/tuple/tuple_benchmark.cpp` | 用户测试源（编译期基准） | ✅ 是 | `tuple_benchmark` | 3: tuple_benchmark | ✅ Debug 构建运行 | PASS |

### 双口径统计

- **source_declared_total = 3**（官方 CMakeLists 声明的独立可执行测试目标数）
- **configured_executable_total = 3**（当前 Debug 配置实际实例化的独立可执行用例数）
- **executed_passed_total = 3**，失败 0，未运行/未实例化 0
- 全量通过率：**3/3 = 100%**（当前配置可执行集合通过率同为 3/3 = 100%）

### 实际执行证据

```bash
cd <work>/build-upstream-tests
cmake .. -DTAOCPP_TUPLE_BUILD_TESTS=ON -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Debug
cmake --build . -j4        # 3 目标全部链接成功
ctest --output-on-failure  # 3/3 Passed, 0 failed, Total Test time 0.06s
```

Release 构建（NDEBUG）会编译掉 assert 导致上游 `-Werror` 报 unused 变量，
这是断言被编译掉的构建配置问题，**不是用例失败**；Debug 构建断言全部生效并通过。
上游测试均通过，无需最小补丁纳入（测试入口已由上游 CMake 正常实例化）。

## 验证结果

```bash
conan create archives/t/taocpp-tuple/1.0.0 -pr ohos-aarch64
# exit 0；test_package 消费者测试输出:
# test_taocpp_tuple: taocpp::tuple public API consumed OK
```

## 注意事项

- header-only 库，`package_id()` 已 `self.info.clear()`，单一 package_id。
- 消费者测试（`test_package/test.cpp`）调用 `tao::tuple`/`tao::make_tuple`/`tao::tie`/`tao::tuple_cat`/按类型 `get<>` 等公开 API，非空壳。

## 知识候选台账与查重（task_type=知识库扩展）

### 候选 1：codeload tag archive URL 无 `.tar.gz` 后缀 → `BadZipFile`
- 真实错误：`conan create` source() 报 `BadZipFile: File is not a zip file`
- 根因：`get()` 按 URL basename 推断格式，`.../tar.gz/refs/tags/1.0.0` 无扩展名 → 误按 zip 解压
- 修复：`source()` 中显式 `src["filename"] = "taocpp-tuple-1.0.0.tar.gz"`
- 验证：`conan create` exit 0；源码 SHA-256 与官方归档一致
- 适用范围：任何 codeload tag archive 下载的 C/C++ 库
- 四范围查重：**正式条目 E276 精确命中**（error_signature: `BadZipFile: File is not a zip file|codeload.github.com/.../tar.gz/refs/tags`；rec_approach: 显式传 filename）→ `exact_duplicate`，复用 E276
- 决定：`reuse_existing`（候选 1 不计入路径 B 新增）

### 候选 2：`copy(self, "tao", ...)` 不递归复制目录树 → 包缺 include
- 真实错误：test_package 报 `Imported target "taocpp::tuple" includes non-existent path .../p/include`
- 根因：`copy()` 按 glob 文件语义展开，指向目录时不递归内部文件，整目录静默不拷贝
- 修复：`copy(self, "*", src=include, dst=include)` 递归复制（保留 tao/ 相对路径）
- 验证：`conan create` exit 0，test_package 编译链接运行全通过
- 适用范围：无上游 CMake install/export、需手动拷头文件目录的 header-only 库
- 四范围查重：**草稿 DRAFT-emio-0.9.0-conan-copy-dir-recursion 精确命中**（error_signature: `Imported target.*includes non-existent path.*/p/include`；rec_approach: shutil-copytree）→ `exact_duplicate`，复用既有草稿
- 决定：`reuse_existing`（候选 2 不计入路径 B 新增）

### 候选 3：上游测试 Release(NDEBUG) 构建下 assert 编译为空 → `-Werror unused variable`
- 真实错误：上游 `tuple_main.cpp:18: error: unused variable 't5' [-Werror,-Wunused-variable]`（Release 构建）
- 根因：上游 CMake 测试目标带 `-Wall -Wextra -Wshadow -Werror`；Release 定义 NDEBUG 使 `assert()` 展开为 `((void)0)`，仅被 assert 引用的 `t5` 变成未使用变量 → 编译失败。不是用例失败，是"断言被编译掉"的构建配置问题
- 修复：上游测试用 **Debug 构建**实际运行（`-DCMAKE_BUILD_TYPE=Debug`，assert 生效），`ctest` 3/3 通过
- 验证：`cmake -DCMAKE_BUILD_TYPE=Debug && cmake --build && ctest --output-on-failure` → 3/3 Passed
- 适用范围：任何上游测试用 assert + `-Werror` 编译、且需在 OHOS/CI 下实际运行上游用例的库
- 四范围查重：E259（NDEBUG+assert 副作用不求值，rec: hoist-side-effect）**部分覆盖**但根因/症状/方案不同（E259 是 assert 内含副作用表达式；候选 3 是 assert 本身被编译掉导致 unused variable，方案是 Debug 构建运行上游测试）；E063（-Werror 其他 warning 类别）不覆盖；DRAFT-cpplocate（test_package NDEBUG 安全）不覆盖本场景；**无既有条目精确命中**
- 七轴查重：exact_duplicate=false；causal_duplicate=false（根因不同：编译期 assert 消失 vs 运行时副作用不求值）；trigger_overlap=true（同 NDEBUG，但触发面不同）；solution_overlap=false（Debug 构建 vs hoist/去 NDEBUG）；combination_novelty=true（NDEBUG×-Werror×unused variable 组合无既有覆盖）；boundary_novelty=true（适用边界：assert 仅被断言引用的变量 + -Werror，与 E259 的 assert 副作用场景可区分）；test_migration_novelty=true
- 决定：`new_draft` → 走路径 B，建立同 stem 的 .md/.kv 草稿

### 路径决定（七轴汇总）
- `reuse_existing`：候选 1（E276）、候选 2（DRAFT-emio）
- `new_draft`：候选 3（NDEBUG×-Werror×unused variable → Debug 构建运行上游测试）
- 路径判断：**路径 B（知识库扩展）**，PR 前缀【知识库扩展】，草稿随本库归档同 PR 交付
---

**编译结束**: 2026-09-19 22:12
**最终状态**: built

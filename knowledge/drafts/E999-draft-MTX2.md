# E999-draft-MTX2 — Conan 工具链用普通 CMake 变量注入 C++ 标准，项目内 cache_variables 无法覆盖

> **状态**：`draft: true`（路径 B 候选）
> **来源**：mtxclient 0.10.1 适配（PR #13832，commit `c770174d37`）
> **平台**：与平台无关（在 OHOS profile `compiler.cppstd=17` 上首次观测）
> **关联**：E216（Conan/CMakeDeps 数据传播缺口同族）
> **非重复声明**：四范围查重（正式库 / index.tsv / 草稿 / 本条候选）对本机制零命中，见 `archives/m/mtxclient/0.10.1/notes.md` 的查重记录。

## 错误特征

上游源码里包含 C++20 三路比较，但按 C++17 解析后大量报错：

```
identifiers.hpp:75:18: warning: '<=>' is a single token in C++20; add a space to avoid a change in behavior [-Wc++20-compat]
    auto operator<=>(User const &other) const noexcept { ... };
identifiers.hpp:75:10: error: 'operator<=' cannot be the name of a variable or data member
identifiers.hpp:75:20: error: expected ';' at end of declaration list
```

libc++ 侧还会派生：

```
variant:1617:43: error: no matching function for call to object of type 'std::not_equal_to<>'
  note: candidate template ignored: ... invalid operands to binary expression
```

关键误导点：这些报错**看起来像源码缺陷**（"运算符名不合法"），实际是**编译标准不对**。

## 根因

Conan 2 的 `CMakeToolchain` 由 `CppStdBlock` 依据 profile 的 `compiler.cppstd` 生成：

```cmake
message(STATUS "Conan toolchain: C++ Standard {{ cppstd }} with extensions {{ cppstd_extensions }}")
set(CMAKE_CXX_STANDARD {{ cppstd }})        # ← 普通变量（normal variable）
set(CMAKE_CXX_EXTENSIONS {{ cppstd_extensions }})
set(CMAKE_CXX_STANDARD_REQUIRED ON)
variable_watch(CMAKE_CXX_STANDARD conan_modify_std_watch)
```

`set()` 不带 `CACHE` 关键字 → 普通变量。而 CMake 的作用域查找里**普通变量优先于同名 cache 变量**，
所以 recipe 中这样写是**无效**的：

```python
tc.cache_variables["CMAKE_CXX_STANDARD"] = "20"   # 被工具链的普通变量遮蔽
```

结果：库实际按 profile 的 `cppstd` 编译。OHOS 官方 profile `ci/conan/profiles/ohos-aarch64`
固定 `compiler.cppstd=17`，于是 C++20 语法被当作 C++17。

判别证据（构建日志）：

```
-- Conan toolchain: C++ Standard 17 with extensions OFF     ← 工具链给出的实际标准
```

## 触发条件

- 在 recipe 里用 `tc.cache_variables` / `tc.variables` 提升 `CMAKE_CXX_STANDARD`；
- 且 profile 的 `compiler.cppstd` 低于所需标准；
- 且源码使用该标准才有的语法（三路比较、`std::strong_ordering`、`std::span`、`std::erase_if` 等）。

## 推荐方案

在 recipe 的 `generate()` 中直接改 setting，让工具链**自身**按新标准生成：

```python
def generate(self):
    # 必须在构造 CMakeToolchain 之前改，CppStdBlock 读的是 self.settings
    self.settings.compiler.cppstd = "20"
    tc = CMakeToolchain(self)
    ...
```

并**删掉** recipe 里试图提升标准的 `tc.cache_variables["CMAKE_CXX_STANDARD"]`——
它不但无效，还会让人误以为标准已提升（本库首轮适配就因此多花了一轮真机验证）。

工具链随后输出 `C++ Standard 20 with extensions OFF`，编译与链接均按 C++20。

### 验证

```sh
grep -m2 'C++ Standard' <conan-create.log>     # 期望 C++ Standard 20
```

真机实测：改前 9 个测试目标全部因 `operator<=` 失败；改后 15 个目标全部构建成功、
9 个离线用例 9/9 通过。

## 回退方案

若该库确实只能停在 C++17（例如依赖链里有仅支持 C++17 的静态库），
则在补丁中把三路比较改写为显式比较运算符，并逐个补齐 `<`、`<=`、`>`、`>=`、`==`、`!=`，
再跑完整上游测试。

## ★ 禁止策略 ★

- 不要用全局 `tools.build:cxxflags` 强塞 `-std=c++20`：绕过 Conan 的标准协商与 `package_id` 语义，
  且与 profile 层叠加时顺序不可控。
- 不要 `sed` 改 `CMakeLists.txt` 之类的生成/构建文件（R6），要用补丁或 recipe 表达。

## 备注

同类「recipe 侧设置被工具链覆盖」的模式可迁移到其他 setting：凡是 `CMakeToolchain` 会从
`self.settings` 派生并写成**普通变量**的项（C/C++ 标准、`BUILD_SHARED_LIBS` 等），
都应在 `self.settings` 上改，而不是在 `cache_variables` 上改。

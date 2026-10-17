# E587: OHOS libc++15 默认禁用 C++20 ranges 算法（_LIBCPP_HAS_NO_INCOMPLETE_RANGES）

## 错误特征

在 OHOS PC (arm64) + clang 15.0.4 / libc++ 15 工具链下，以 `-std=c++20` 编译使用了
`std::ranges::*` 算法的源码时，报：

```
error: no type named 'sort' in namespace 'std::ranges'
        std::ranges::sort(files);
        ~~~~~~~~~~~~~^
```

同类错误模式覆盖 `std::ranges::sort / replace / find / count / transform` 等全部
ranges 算法；`std::string` 的 spaceship（`operator<=>`）同样缺失
（`invalid operands to binary expression ('std::string' and 'std::string')`），
报错候选模板来自 pair/iterator 的 `<=>`，说明 `basic_string` 未定义三路比较。

## 触发条件

- 目标平台：OHOS SDK 配套 clang 15.0.4 + libc++（`_LIBCPP_VERSION 15004`）
- 编译标准：`--std=c++20`（或 cppstd=20）
- 源码：直接使用任意 `std::ranges::*` 算法，或对 `std::string` 使用 `<=>`

## 根因

OHOS SDK 的 libc++（LLVM 15）在 `__config` 中有如下逻辑：

```
#  if !defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)
#    define _LIBCPP_HAS_NO_INCOMPLETE_FORMAT
#    define _LIBCPP_HAS_NO_INCOMPLETE_RANGES
#  endif
```

即：**只要未定义 `_LIBCPP_ENABLE_EXPERIMENTAL`，libc++ 就主动定义
`_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，把整个 `std::ranges` 命名空间内的算法全部关停**，
无论 `<algorithm>` / `<ranges>` 头文件中是否含有完整实现（实际上
`__algorithm/ranges_sort.h` 等文件都在，只是被宏屏蔽）。

这与既有知识 `DRAFT-E5xx`（kholidays none_of）的归因不同：
E5xx 描述为"裁剪版 `<algorithm>` 只含 C++17 版本、未提供 C++20 ranges 版"；
而 scite 实测证明 **实现存在，只是被宏主动屏蔽**——加 `-D_LIBCPP_ENABLE_EXPERIMENTAL`
后 `std::ranges::sort` 立即可用（最小复现编译通过），证实是宏开关而非头文件缺失。

附带：`std::string::contains`（C++20）在该 libc++ 上也未实现；但
`std::set::contains` / `std::map::contains` / `std::string_view::starts_with/ends_with`
均可用（实测），`std::string::starts_with/ends_with` 也可用。

## 解决方案

### 方案 1（推荐，scite 5.6.4 采用）：改写为 C++17 标准算法

为 CI 可复现、不依赖实验特性宏，将 ranges 调用改写为迭代器对版本：

| ranges 调用 | C++17 等价 |
|---|---|
| `std::ranges::sort(v)` | `std::sort(v.begin(), v.end())` |
| `std::ranges::sort(v, cmp)` | `std::sort(v.begin(), v.end(), cmp)` |
| `std::ranges::replace(c, o, n)` | `std::replace(c.begin(), c.end(), o, n)` |
| `std::ranges::find(c, v)` | `std::find(c.begin(), c.end(), v)` |
| `std::ranges::count(c, v)` | `std::count(c.begin(), c.end(), v)` |
| `std::ranges::transform(r, out, f)` | `std::transform(r.begin(), r.end(), out, f)` |

spaceship 改写（`std::string` 无 `<=>`）：

```cpp
// 原：return fileName <=> other.fileName;
// 改：
const int cmp = fileName.compare(other.fileName);
if (cmp < 0) return std::weak_ordering::less;
if (cmp > 0) return std::weak_ordering::greater;
return std::weak_ordering::equivalent;
```

scite 5.6.4 共改写 24 处 ranges 调用 + FilePath.cxx 一处 spaceship，
11 个补丁，scintilla/lexilla/scite 三组件全部编译通过。

### 方案 2（后备）：编译宏启用

```bash
export CXXFLAGS="$CXXFLAGS -D_LIBCPP_ENABLE_EXPERIMENTAL"
```

实测可恢复全部 ranges 算法；属于实验特性开关，与后续 libc++ 版本行为可能变化，
仅作过渡。

## 验证

最小复现（scite 适配期实测）：

```bash
printf '#include <algorithm>\n#include <ranges>\n#include <vector>\nint main(){std::vector<int> v{2,1}; std::ranges::sort(v); return 0;}\n' > /tmp/t.cxx
clang++ --std=c++20 /tmp/t.cxx          # 报 no type named 'sort'（复现）
clang++ --std=c++20 -D_LIBCPP_ENABLE_EXPERIMENTAL /tmp/t.cxx -o /tmp/t  # 编译通过（根因证实）
```

完整验证：scite 5.6.4 `conan create` 通过（G1-G4 + L2/L4/L5），
scintilla 52 用例 / scite 11 用例 / lexilla 全 lexer 用例全部通过。

## 适用与不适用边界

适用：OHOS PC arm64 + clang15/libc++15 工具链下所有使用 C++20 ranges 的项目。
不适用：使用 gcc/libstdc++ 或其他完整支持 C++20 的工具链；libc++ 16+（ranges 已完整）。

## 关联条目

- 部分重复：DRAFT-E5xx（kholidays none_of 缺 ranges；未覆盖宏开关根因与启用路径）
- 相似：DRAFT-8945（botan3 报 `ranges::equal/any_of` 缺失、`std::array` 无 `<=>`）、
  DRAFT-332（openrct2 libcpp15 c++20 兼容坑）
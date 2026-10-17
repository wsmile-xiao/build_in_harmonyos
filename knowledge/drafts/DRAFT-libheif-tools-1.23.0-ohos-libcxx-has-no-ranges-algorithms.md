# DRAFT: OHOS 的 libc++ 有 `std::ranges` 命名空间，但没有 ranges 算法

> Contributor: username- | Status: DRAFT | Created: 2026-09-17
> 来源: libheif-tools 1.23.0 适配（`libheif/box.cc` 使用 `std::ranges::all_of` / `std::ranges::find`）

## 症状

上游 CMakeLists 自己写了 `set(CMAKE_CXX_STANDARD 20)` + `CMAKE_CXX_STANDARD_REQUIRED ON`，
构建到某个文件突然炸：

```
error: no member named 'all_of' in namespace 'std::ranges'
    return std::ranges::all_of(m_reference_types, [](uint32_t t) { ... });
error: no member named 'find' in namespace 'std::ranges'
```

第一反应是"这个文件少 `#include <algorithm>`"——但它已经包含了；
换个角度把标准降到 C++17，报错变成：

```
error: no member named 'ranges' in namespace 'std'
```

也就是说：**C++20 下 `std::ranges` 命名空间存在、算法不存在；C++17 下命名空间都没有。**
提标准解决不了问题，补头文件也不是问题所在。

## 判据（设备上一次小编译即可，不必跑整个工程）

```sh
cat > t.cc <<'EOF'
#include <algorithm>
#include <array>
int main(){ std::array<int,3> a{1,2,3}; return (int)std::ranges::count(a,2); }
EOF
clang++ -std=c++20 t.cc -o t && ./t
```

设备实测（OHOS SDK，clang version 15.0.4，`Target: aarch64-unknown-linux-ohos`）：

| 编译标准 | 结果 |
|---|---|
| `-std=c++20` | `no member named 'all_of' / 'find' in namespace 'std::ranges'` |
| `-std=c++17` | `no member named 'ranges' in namespace 'std'` |
| `-std=c++20` + 换成 `std::all_of` / `std::find` | 编译通过、运行正常 |

libc++ 把 C++20 ranges 分两部分交付：`std::ranges` 命名空间（views / concepts /
subrange）与 ranges 版算法。OHOS SDK 这份 libc++ 只交付了前者。

静态扫影响面：

```sh
grep -rn 'std::ranges::' <src>/ | grep -v '::views'
```

（用 `<ranges>` 的 views——管道、`filter`、`transform` 视图——一般没问题，
出事的只有 ranges 版算法。）

## 修复：换回迭代器版算法

```diff
-  return std::ranges::all_of(m_reference_types, [](uint32_t t) {
-    return std::ranges::find(supported_reference_types, t) != supported_reference_types.end();
-  });
+  return std::all_of(m_reference_types.begin(), m_reference_types.end(), [](uint32_t t) {
+    return std::find(supported_reference_types.begin(), supported_reference_types.end(), t) !=
+           supported_reference_types.end();
+  });
```

不带投影参数的 ranges 算法就是迭代器版的薄包装，语义完全一致，改动面小、
不需要引入 range-v3 之类的额外依赖。本包只有 `libheif/box.cc` 的 3 处调用。

## 同一次适配里的另外两个点

### `CMAKE_DISABLE_FIND_PACKAGE_<name>` 大小写敏感

`heifio/CMakeLists.txt` 探测输入格式用的是 `find_package(WEBP)`（全大写），
而配方里写的是 `CMAKE_DISABLE_FIND_PACKAGE_WebP=ON` —— **不匹配**，
于是设备 `/usr/local` 下那份 `WEBPConfig.cmake` 被拉了进来，而它引用的
`libsharpyuv.so.0.1.2` 在系统安装里根本不存在，configure 直接失败：

```
CMake Error at .../WebPConfig.cmake: ...
  The imported target "WebP::sharpyuv" references the file ".../libsharpyuv.so.0.1.2"
  but this file does not exist.
```

这个错误由 CMake 的 config 文件自己抛出，**即使 `find_package` 不带 `REQUIRED` 也会 fail**，
所以"反正不是 REQUIRED，找不到就跳过"的想法在这里不成立。
禁用开关必须逐字对上上游传给 `find_package()` 的那个名字——
先 `grep -n 'find_package' <src>/**/CMakeLists.txt` 列出来再写。

### 只看"缺了什么"容易漏掉"多探测到了什么"

同一个文件里还有 `find_package(libsharpyuv)`，默认 `WITH_LIBSHARPYUV=ON`，
探测的是同一族 `/usr/local` 下的坏 config。拆分包在关闭全部编解码器之后，
这条探测已经没有意义，直接一起关掉：

```python
tc.variables["WITH_LIBSHARPYUV"] = "OFF"
```

结论：系统前缀（`/usr/local`、`/usr`）里存在的第三方 CMake 包配置，
对"想保持 hermetic 的交叉构建"来说是负面因素——分包时必须显式禁用，
而不是指望它找不到。

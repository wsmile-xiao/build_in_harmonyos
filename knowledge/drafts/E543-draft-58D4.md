# E543 — conan 包公共头依赖第三方头/平台宏却未传播给消费者

- 状态：草稿（draft，待主编审核）
- 贡献者：58D4
- 触发事件：kea-hooks 3.0.3 适配（ISC Kea hooks 框架库，meson + Conan，OHOS aarch64）
- 日期：2026-09-16
- 相关条目：E085 / E127 / E507（boost + musl pthread_setcancelstate）、E481（MesonToolchain 工具链注入）

## 现象

`conan create` 的前两步都通过（库编译成功、上游测试 121/121 通过），到 **test_package** 阶段失败：

```
kea/util/bigints.h:14:10: fatal error: 'boost/multiprecision/cpp_int.hpp' file not found
#include <boost/multiprecision/cpp_int.hpp>
```

补上 boost 头路径后再编译，又出现：

```
boost/core/detail/sp_thread_sleep.hpp:73:5: error: use of undeclared identifier 'pthread_setcancelstate'
```

两条错误都发生在**消费者**（test_package）编译包含包内公共头时，而库自身构建完全正常。

## 根因

1. **头文件传播**：包安装的公共头 `include/kea/hooks/*.h` 经 `kea/cc/data.h` →
   `kea/util/bigints.h` 拉入 `boost/multiprecision/cpp_int.hpp`、`boost/shared_ptr.hpp`。
   `conanfile.py` 只用默认 `self.requires("boost/...")` 时，Conan 2 的 CMakeDeps **不会**把传递
   依赖的 include 目录加入 `kea-hooks::kea-hooks` 的 `INTERFACE_INCLUDE_DIRECTORIES`
   （生成的数据文件里 `kea-hooks_FIND_DEPENDENCY_NAMES` 只有 log4cplus，boost/openssl 缺席），
   消费者只有 `-I<pkg>/include/kea`。
2. **编译宏传播**：OHOS 的 musl `pthread.h` 不声明 `pthread_setcancelstate()`（实测 sysroot 内
   grep 计数 = 0），制品仓 boost 1.85 的 `sp_thread_sleep.hpp` 需要外部定义
   `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 才跳过该调用。库自己在 `generate()` 里用
   `tc.extra_cxxflags` 加了宏，但**没有**通过 `cpp_info.defines` 传给消费者。

隐蔽点：两个缺陷都不会让库本身构建失败，只有“编译一个真实消费者”时才暴露——这也是
test_package 必须代表真实消费者的原因（R34）。

## 修复（推荐）

```python
# requirements()：公共头 include 了它们，就必须声明头传递性
self.requires("boost/1.85.0", transitive_headers=True)
self.requires("log4cplus/2.2.0.1", transitive_headers=True)
self.requires("openssl/3.5.8.1", transitive_headers=True)

# package_info()：平台必需的宏随包传播
if self.settings.os == "OHOS":
    self.cpp_info.defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
```

修复后 test_package 一次通过（9 项检查全 OK），且消费者的 `-I`/`-D` 由包自身声明，
无需测试端或下游手工补。

## 验证方法

```bash
# 1) 消费者是否拿到第三方 include / 宏
grep -n "INTERFACE_INCLUDE_DIRECTORIES" -A3 <test_package_build>/generators/kea-hooks-Target-*.cmake
grep -n "INTERFACE_COMPILE_DEFINITIONS"  -A3 <test_package_build>/generators/kea-hooks-Target-*.cmake
# 2) 包内公共头是否真的依赖第三方头
grep -rn "^#include <\(boost\|openssl\|log4cplus\)/" <package_folder>/include
```

## 禁止做法

- 在 `test_package/CMakeLists.txt` 或 `test_package/conanfile.py` 里手工 `find_package(boost)` /
  追加 `include_directories()` / 加 `-D`：CI 会变绿，但真实消费者仍然红，属于掩盖缺陷。
- 跳过 test_package（`def test(self): pass`、注释掉 `cmake.build()`）：R9 欺骗性行为。

## 适用面

任何“公共头泄漏第三方依赖”的 conan 库包（Kea 系、Qt 系、boost 头显式暴露的包）；以及跨平台
适配中，把平台必需宏写进 `generate()`（只影响本包构建）却忘记写进 `package_info()`（影响消费者）
的场景。

# DRAFT-clipboard_lite-3.4-x11-cmake-injection：OHOS 上 CMake find_package(X11) 变量注入

> Contributor: pc1-48 (AtomCode) | Status: Draft | Updated: 2026-09-22
> Source: task clipboard_lite-3.4-r01-pc1-48-20260922T043531Z

## 背景

clipboard_lite 3.4 是 C++14 跨平台剪贴板库，上游 CMakeLists.txt 在 Linux/OHOS 分支
调用 `find_package(X11 REQUIRED)`，并把 `X11_INCLUDE_DIR` 并入编译 include 路径；
Test 子目录还消费 `X11_LIBRARIES`、`X11_Xfixes_LIB`、`X11_XTest_LIB` 做链接。
OHOS 交叉编译环境没有系统 X11 开发树，头文件分属 4 个 Conan 制品：

| 头文件 | 制品 |
|--------|------|
| X11/Xlib.h, X11/Xutil.h | libx11/6.4.0 |
| X11/Xatom.h, X11/X.h | xorgproto/2025.1 |
| X11/extensions/Xfixes.h | libxfixes/6.1.0 |
| X11/extensions/XTest.h | libxtst/6.1.0 |

## 错误链

1. **Xatom.h not found**：X11_INCLUDE_DIR 只注入 libx11 的 include → `fatal error:
   'X11/Xatom.h' file not found`（Xatom.h 属 xorgproto）。需把 4 个制品的 include
   目录用分号拼接注入。
2. **undefined symbol: XOpenDisplay**：X11_LIBRARIES 若传 lib 目录（而非实际 .so
   文件），CMake target_link_libraries 把目录传给 linker 时被忽略 →
   `ld.lld: error: undefined symbol: XOpenDisplay / XDefaultScreen /
   XCreateWindow / XInternAtom / XFixesQueryExtension ...`。必须传
   `<libx11>/lib/libX11.so` 这样的真实文件路径；Xfixes/XTest 库同理。

## 方案

conanfile.py `generate()` 内：

```python
tc.variables["X11_INCLUDE_DIR"] = ";".join(
    os.path.join(self.dependencies[d].package_folder, "include")
    for d in ("libx11", "xorgproto", "libxfixes", "libxtst"))
tc.variables["X11_LIBRARIES"] = os.path.join(
    self.dependencies["libx11"].package_folder, "lib", "libX11.so")
tc.variables["X11_Xfixes_LIB"] = os.path.join(
    self.dependencies["libxfixes"].package_folder, "lib", "libXfixes.so")
tc.variables["X11_XTest_LIB"] = os.path.join(
    self.dependencies["libxtst"].package_folder, "lib", "libXtst.so")
tc.variables["CMAKE_LIBRARY_PATH"] = os.pathsep.join(lib_paths)
```

## 验证

- 修正前: conan-verify G2 FAIL（Xatom.h not found → 补 xorgproto 后链接期 undefined
  symbol XOpenDisplay...）
- 修正后: conan-verify G2 PASS；W3 本地 CI L0-L5 + JC 全过，100% (1/1)
- 证据: archives/c/clipboard_lite/3.4/reports/conan-verify-report.md

## 适用边界

- 适用: OHOS 上 CMake 项目 + find_package(X11) + 消费 X11_* 变量的库。
- 不适用/反例: autotools/pkg-config 项目走 E480（transitive_headers +
  PKG_CHECK_MODULES）；纯头文件 X11 库（仅 include 无链接）只需注入 include。

## 查重差异

与 E480 部分重叠（同为 X11 头文件分发的根因），但 E480 面向 autotools/
PKG_CHECK_MODULES + transitive_headers 侧，本条目面向 CMake find_package(X11)
变量注入侧，机制与修复面不同，无 conflicts_with，属互补关系。

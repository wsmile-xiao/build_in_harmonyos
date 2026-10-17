# E547 — libtiff 4.7.0→4.7.2 CMake C++ 库选项改名（cxx→tiff-cxx）

## 现象

把 libtiff 4.7.2 配方的 `-Dtiff-cxx=OFF` 照搬到 4.7.0 构建：**无任何报错**，
但产物里出现 `libtiffxx.so`（C++ stream 封装库）——开关静默失效。

## 根因

上游在 4.7.0 与 4.7.2 之间把 CMake 选项改名（`cmake/CXXLibrary.cmake`）：

- 4.7.0：`option(cxx "Enable C++ stream API building (requires C++ compiler)" ON)`
- 4.7.2：`option(tiff-cxx ...)`（改名以对齐其他 `tiff-*` 前缀选项）

CMake 对未知的 `-Dxxx=OFF` 不报错，只写一个无效的 cache 条目——错误开关名
静默失效，纯 C 需求的构建被塞进 C++ 库。

## 影响

- 产物多出 `libtiffxx.so`，与 `package_info.cpp_info.libs = ["tiff"]` 不一致；
- 无谓引入 C++ 运行时 NEEDED（`libc++_shared.so`），放大部署面；
- 包体积膨胀。

## 修复

按**实际源码**的选项名传开关：

```bash
# 判定：看源码
grep -n "option(" cmake/CXXLibrary.cmake
# 4.7.0 → -Dcxx=OFF；4.7.2+ → -Dtiff-cxx=OFF
```

## 验证

```bash
find build-ohos -name "libtiffxx*" -not -type l
# 期望：无输出（纯 C 库）
```

## 实证

libtiff 4.7.0 适配（archives/l/libtiff/4.7.0，2026-09-05）：照搬 4.7.2 配方首建
产物含 `libtiffxx.so.6.1.0`；改 `-Dcxx=OFF` 后重建产物仅 `libtiff.so.6.1.0`，
conan create + 8 后端 roundtrip 测试全绿。

## 关键词

libtiff, tiff-cxx, cxx option, 4.7.0, libtiffxx, option renamed, cmake silent ignore

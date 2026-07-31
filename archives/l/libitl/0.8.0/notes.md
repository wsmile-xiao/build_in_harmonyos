# libitl 0.8.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-28
- 编译器: clang/gcc
- 状态: built

## 编译步骤

1. 源码：GitHub 官方归档 `https://github.com/arabeyes-org/ITL/archive/refs/tags/v0.8.0.tar.gz`（与 Debian orig 字节级相同）
2. 应用补丁：GNUInstallDirs + 共享库 + C99 前向声明 + `cmake_minimum_required(3.5)`
3. 构建：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -B build -S .
   cmake --build build -j2
   cmake --install build --prefix ... # 或 DESTDIR staging
   ```
4. 验证：运行 `demo_hijri` / `demo_prayer`；Conan `test_package` 调用 `G2H` + `getPrayerTimes`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误判为 autotools | 无 configure 时的默认模板 | 手写 CMake `conanfile.py` |
| 2 | 上游只编静态库 | CMakeLists 仅 `add_library(... STATIC)` | 引入 Debian `build_shared` 补丁，同时产出 `.so` |
| 3 | C99 隐式声明警告/错误 | 缺前向声明 | Debian `c99-fix` 补丁 |
| 4 | CMake 2.6 deprecation | 过旧 `cmake_minimum_required` | 升至 3.5 |
| 5 | CI `Failed to parse patch` on `0001-CMakeLists.txt.patch` | 补丁第 13–14 行缺 unified-diff 前缀，且把不存在的 `LIBRARY_VERSION_*` 行当上下文 | 对照上游 CMakeLists 重生成合法补丁（MAJOR/MINOR/PATCH=0.8.0） |

## 源码修改

- `patches/0001-CMakeLists.txt.patch` — 安装路径、共享库、CMake 版本
- `patches/0002-hijri-hijri.c.patch` — C99 前向声明
- `patches/0003-hijri-umm_alqura.c.patch` — C99 前向声明

## 依赖版本

无外部库依赖；链接 `libm`。构建工具：cmake ≥ 3.5。

## 验证结果

```bash
./demo_hijri   # PASS — Gregorian↔Hijri
./demo_prayer  # PASS — Abu Dhabi/London sample times match demo notes

# 容器 Conan（无真机）
conan create archives/l/libitl/0.8.0 -pr:h=default -pr:b=default \
  --build=missing --user=ohpcd --channel=stable -o "*:shared=True"
# → G2 PASS，test_package PASS
```

## 注意事项

- 头文件安装在 `include/itl/`（`#include <itl/hijri.h>` / `<itl/prayer.h>`）
- 库名 `libitl`，`cpp_info.libs = ["itl"]`
- 上游 CMake 同时构建 static+shared；Conan `shared` 选项在 `package()` 中裁剪产物
- `G2H(sDate*, day, month, year)` 成功返回 **1**（非 0）
- 真机 / `ohos-aarch64` profile 验证按需求跳过；无签名工具时 `package()` 仅告警不失败

---

**日期**: 2026-07-31
## CI L0 门禁：stub_test_method

`test_package/conanfile.py` 的 `test()` 仅调用 `cmake.test()`，无 `self.run()`，
触发 L0d `stub_test_method`。已改为 `can_run` 守卫下
`self.run(.../test_libitl, env="conanrun")`。同时主配方 demo 冒烟改为在
`build_folder` 下定位可执行文件，避免 `bindirs` 字面量误触发 L0k（库包无
package bin/ 产物，不需要 commands.json）。

# geos 3.14.1.1 编译笔记（HarmonyOS PC · Conan cmake）

## 版本说明
3.14.1.1 = 上游 3.14.1 + 适配修复（R37 版本递增）。
原 3.14.1 配方缺少 `export_sources()` 方法（conan 2.x 规范要求），导致 conan-verify G1 门禁失败。
本次修复添加 `export_sources` + `export_conandata_patches` 导入，版本递增为 3.14.1.1。

## 产物
`libgeos.so`、`libgeos_c.so`（C API）、`bin/geosop`（命令行几何运算工具）。

## 上游测试
508 项 ctest 全部通过（100%），0 失败，0 跳过，耗时 25.62s。
覆盖：算法（角度/面积/质心/凸包/缓冲区）、C API（WKT/WKB/GeoJSON/求交/包含/距离）、
健壮性（overlay 回归）、空间关系（Relate AA/AC/LA/LC/LL/PA/PL/PP）。

## 关键适配
- 完全沿用 3.13.1 的 cmake 模板（OHOS 工具链自发现 + 裸 cmake，绕开 conan_toolchain 的 OHOS 映射问题）。
- geos 3.14.1 无外部 C 依赖（CMakeLists 中唯一 find_package 是内部 dist 模块）。
- 产物 `.so` 与 `bin/` ELF 经 `llvm-objcopy` 去旧签名后由 `binary-sign-tool` 自签。
- 添加 `export_sources()` 方法以满足 conan 2.x 规范和 conan-verify G1 门禁。

## 状态
built —— 真机 `conan create` 通过；conan-verify 全部门禁通过（G1/G0/G2/G3/G4/L2/L4/L5）。
test_package 做真实几何断言（构造 WKT、求交、判面积、缓冲区、错误回调），非仅链接成功。
---

**编译结束**: 2026-09-09 01:10
**最终状态**: built

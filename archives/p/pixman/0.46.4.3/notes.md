# pixman 0.46.4.2 — 适配笔记

## 基本信息
- **软件**: pixman 0.46.4.2
- **上游**: pixman 0.46.4 (https://cairographics.org/releases/pixman-0.46.4.tar.gz)
- **构建系统**: meson
- **许可证**: MIT
- **类别**: gfx (图形渲染)

## 变更说明 (0.46.4.1 → 0.46.4.2)
- 添加 `package_type = "shared-library"` 属性（Conan 2.x 最佳实践）
- 明确声明共享库类型，便于下游依赖管理

## 构建配置
meson setup(禁 tests/demos/gtk/libpng/openmp) → ninja。核心库仅依赖 libm+pthread 系统库。

## 关键知识点
- 库 libpixman-1.so、pkg-config pixman-1、头 include/pixman-1/pixman.h
- cpp_info.includedirs=["include/pixman-1","include"]（pixman.h 内部 #include <pixman-version.h>）
- meson ar 须注入 conan_meson_native.ini（conan 不写 compiler_executables 的 ar）

## 验证结果
- conan create: PASS
- conan-verify G1-G4: PASS
- W3 本地 CI 模拟: PASS
- 真机 conan create + dlopen libpixman-1.so 通过
---

**编译结束**: 2026-07-15 21:19
**最终状态**: published

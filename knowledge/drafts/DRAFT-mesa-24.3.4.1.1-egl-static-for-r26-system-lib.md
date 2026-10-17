# DRAFT-mesa-24.3.4.1.1-egl-static-for-r26-system-lib

## 问题

mesa 24.3.4.1.1 在 ohos-aarch64 上启用 `-Degl=enabled` 后，conan-verify 的
**G3（R26 系统同名库隔离）** 门禁失败：

```
❌ R26 违规: 系统同名库输出了 .so
     libEGL.so.1.0.0: 与系统同名 .so 冲突
     libEGL.so.1: 与系统同名 .so 冲突
     libEGL.so: 与系统同名 .so 冲突
```

## 根因

OHOS PC 系统镜像 `/lib64` 自带图形栈共享库：`libEGL.so`、`libEGL_mesa.so`、
`libGLESv3.so`、`libegl_effect.z.so`（系统图形栈，r22 实测 `ls /lib64`）。
mesa 交付 `libEGL.so`（含 SONAME 复制链 libEGL.so / .so.1 / .so.1.0.0）后，
conan-verify G3 将包内所有 `.so` 基名去版本后缀后与 `/lib`、`/lib64` 比对，
同名即判 FAIL（CI 侧 `ci/conan/build_and_test.sh` L5/R26 同规则但对同名只报
`[warn]`，本地 conan-verify 为硬 FAIL；两者都指向 R26 的「系统同名库禁止动态
交付」约束）。

## 方案

按 R26 将系统同名库静态化（`BUILD_SHARED_LIBS=OFF / --disable-shared` 同义：

- 新增 `patches/0009-src-egl-meson.build.static-egl.patch`：把
  `src/egl/meson.build` 中 `libegl = shared_library(...)` 改为
  `libegl = static_library(...)`，并移除 `version` / `soversion` /
  `vs_module_defs` 参数（meson 1.11.1 的 `static_library` 不接受
  `version`/`soversion`，会报 `Got unknown keyword arguments`）。
- GLESv1_CM / GLESv2 / gbm / OSMesa 无系统同名冲突，保持共享交付。
- `egl.pc` 仍由 `pkg.generate` 生成；`pkg-config --libs egl` → `-lEGL` 解析到
  `libEGL.a`，最小公开头编译链接消费验证通过（exit 0）。
- 配方 `package()` 中 SONAME 复制 loop 使用 `glob`，需在 `package()` 内
  `import glob`（此前仅在 `_sign_shared_libs` 内局部导入，会 NameError）。

## 验证

- `conan create archives/m/mesa/24.3.4.1.1` → RC=0，`test_mesa: ALL PASS`。
- `conan-verify` → G0/G1/G2/G3/G4 全 PASS（RC=0）。
- 包内 `libEGL.a` 存在，无 `libEGL*.so` 输出；`pkg-config --modversion egl`
  rc=0（24.3.4）；最小消费者 egl_min（`#include <EGL/egl.h>` + `-lEGL`）
  编译链接运行均 exit 0。

## 适用边界

- 仅当 OHOS 系统 `/lib64` 已存在同名共享库时需要静态化；否则保持共享交付
  （反例：libGLESv1_CM/libGLESv2/libgbm/libOSMesa 系统无同名，仍为 .so）。
- `static_library` 不产出 SONAME，链路版本由 conan 包目录管理。
- 同规则适用于任何交付与系统图形栈同名的库（egl/gles/图形栈 API 类）。

## 关联

- similar_to: E104（version script 控制符号导出，机制不同）；DRAFT-mesa-24.3.4-gbm-static-libdrm-symbol-export（静态依赖符号泄漏进共享库导出表，机制不同）
- caused_by: OHOS 系统镜像自带 libEGL（系统图形栈）+ R26 隔离规则
- prerequisite_of: mesa EGL pkg-config 消费链；GLESv1_CM/GLESv2 共享库交付
- conflicts_with: 无
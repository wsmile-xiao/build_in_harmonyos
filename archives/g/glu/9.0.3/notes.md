# glu 9.0.3 适配笔记

## 编译环境
- 构建系统: meson（+ ninja）
- 编译日期: 2026-09-15
- 编译器: clang 15
- 状态: built

## 上游

| 项 | 值 |
|----|-----|
| 项目 | `gitlab.freedesktop.org/mesa/glu`（随 mesa 维护的独立库）|
| 版本 | 9.0.3（tag `glu-9.0.3`）|
| 发布归档 | `https://archive.mesa3d.org/glu/glu-9.0.3.tar.xz` |
| sha256 | `bd43fe12f374b1192eb15fe20e45ff456b9bc26ab57f0eee919f96ca0f8a330f` |
| 大小 | 218,968 字节 |
| 版权 | SGI-B-2.0 |

> **注**：只有 `.tar.xz` 一种格式（`.tar.gz` / `.tar.bz2` / `.tar.zst` 实测均 404）。
> Debian 源最新只到 **9.0.2**（bookworm/trixie/sid 均为 9.0.2-1.1），9.0.3 仅存在于
> 上游 gitlab 与 mesa 归档站——不要去 Debian pool 找 9.0.3。

## 编译步骤
```bash
conan create archives/g/glu/9.0.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

### 1. OHOS 没有桌面 GL —— 用 Mesa OSMesa 替代

GLU 是「桌面 OpenGL 的配套工具库」，直觉上会被判为不可适配（OHOS SDK 只有
EGL + GLES2/GLES3，无 `libGL.so` / `glx.h` / `glu.h`）。但实测有解法：

- **GLU 不引用 GLX**：源码 `glX` 命中 **0**（`grep -r glX src/ include/`）。它只需要
  一份提供 OpenGL API 的**实现**，并不要求 X11；
- **`mesa/24.3.4.1` 正好提供**：离屏软件桌面 GL（`libOSMesa.so`）+
  `include/GL/gl.h`，不需要 X11/Wayland/DRM，已发布 ohpcd；
- **glu 的 meson 原生支持**：`gl_provider` 选项的 choices 就是
  `['glvnd', 'gl', 'osmesa']` —— 用 `-Dgl_provider=osmesa` 即可。

故本包 `requires("mesa/24.3.4.1")` + `gl_provider=osmesa`。

### 2. 必须删掉 `gnu_symbol_visibility: 'hidden'`（补丁 0001）

`src/meson.build:106` **无条件**设置了 `gnu_symbol_visibility: 'hidden'`，而源码里
**没有任何 `visibility default` 标注**。后果极具欺骗性：

| 配置 | dynsym 导出 `glu*` 符号数 | 产物大小 |
|------|--------------------------|---------|
| 上游原样（带 hidden）| **0**（符号在 `.symtab` 里是 `LOCAL HIDDEN`）| 1,575,424 字节 |
| 删除该行 | **64**（`gluOrtho2D` = `GLOBAL DEFAULT`）| 1,714,688 字节 |

编译 `rc=0`、产物约 1.5 MB 看着完全正常，但**动态符号表里一个 `glu*` 都没有**，
消费者链接必然失败。这是本次适配中最隐蔽的坑——只有查 `.dynsym` 才暴露。

### 3. `.pc` 名字对不上导致 OSMesa 找不到

mesa 的 `package_info()` 只设了 `libs`/`cmake_file_name`/`cmake_target_name`，
**未设 `pkg_config_name`**（实测），故 conan 的 `PkgConfigDeps` 生成的是 **`mesa.pc`**；
而 glu 在 `gl_provider=osmesa` 时执行 `dependency('osmesa')` —— **名字不匹配**。

mesa 包内其实自带 `lib/pkgconfig/osmesa.pc`，但它写死了 `prefix=/` →
`libdir=/lib`，照用会让 pkg-config 发出 `-L/lib`，实测链接报：

```
ld.lld: error: unable to find library -lOSMesa
```

**解法**：`generate()` 里把 mesa 包内的 `osmesa.pc` 复制到生成目录，并把
`prefix=/` 改写为该包的 conan `package_folder`，使其指向真实路径。

### 4. cmake 4.x 不再兼容 `cmake_minimum_required(VERSION 3.1.2)`（实测注意事项）

本机 cmake 为 4.1.2，处理该工程时报
`Compatibility with CMake < 3.5 has been removed`。由于本包用 **meson** 构建，
不受影响；此处仅记录我在预研阶段做 CMake 探针时踩到、故改用 meson 直接验证。

## 依赖版本
- `mesa/24.3.4.1`（提供 OSMesa 桌面 GL 实现）

## 验证结果
```bash
# 见 test_package/MANIFEST.yml；test_package 真实编译并执行消费者程序
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（meson 构建，共享库） |
| conandata.yml | 源码 URL/哈希 + 补丁声明 |
| manifest.yaml | 归档元数据 |
| patches/0001-remove-gnu-symbol-visibility-hidden.patch | 恢复 glu* 符号导出 |
| test_package/ | 消费者编译链接 + 执行测试 |

## 注意事项
- GLU 需要一份 OpenGL 实现：本包绑定的是 **OSMesa**（软件渲染）。若消费者需要
  硬件 GLES，应改用其它 provider（glu 的 meson 也支持 `gl`/`glvnd`），届时需相应
  调整依赖与 `gl_provider`。
- `librt` 不在 OHOS 工具链中，若上游有 `-lrt` 需去除（本包构建未见该问题）。

---

**最终状态**: built

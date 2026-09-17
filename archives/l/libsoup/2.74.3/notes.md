# libsoup 2.74.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-25 (conan adaptation)
- 编译器: clang/clang++（llvm 工具链）
- 状态: built (conan adaptation)

## 背景

libsoup 2.74.3 是 libsoup2 API 版本（libsoup-2.4 库），与 libsoup3 (3.6.5-r1) 共存。
历史适配于 2026-05-13 在设备上完成（手动 meson 编译），但未进行 conan 适配。
本次进行 conan 适配，参照 libsoup3/3.6.5-r1 配方经验。

## 历史经验核验 (W0b)

### 历史编译配置（来自 PROGRESS.md）
```bash
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dtls_check=false -Dsysprof=disabled -Dtests=false \
  -Dgnome=false -Dintrospection=disabled -Dvapi=disabled -Dgtk_doc=false
```

### 环境语义可迁移性
- 历史 glib-compile-resources SIGBUS 崩溃问题：conan glib2 包提供了 glib-compile-resources 工具，
  在 conan 构建环境中可能正常工作（与设备原生环境不同）。
- 尝试不使用补丁，依赖 conan glib2 包的工具。如果失败，使用补丁。
- 历史 libpsl 手动编译：现在通过 conan 包 libpsl/0.21.5.1 解决。

### 历史踩坑比对
1. glib-compile-resources 崩溃 → conan glib2 包提供工具，在 generate() 中 pin
2. libpsl 缺失 → conan 包 libpsl/0.21.5.1
3. sysprof 编译错误 → -Dsysprof=disabled
4. libffi.so 损坏 → conan glib2 包管理
5. tls_check 失败 → -Dtls_check=false

## 编译步骤

```bash
# conan create
conan create archives/l/libsoup/2.74.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

> pkg-config 路径无需手动 export：conanfile.py 的 generate() 通过 deps-pc-fix
> 机制自动遍历所有依赖包，复制 .pc 并重写 prefix 为 conan 包真实路径后
> 注入 tc.pkg_config_path（禁止回退系统 /usr/local pkg-config，避免
> DT_NEEDED 含绝对路径导致产物不可移植）。

## 依赖版本

- glib2/2.88.0
- libpsl/0.21.5.1
- libxml2/2.15.3
- sqlite3/3.49.1
- brotli/1.2.0 (升级自历史 1.1.0，1.1.0 未发布到 ohpcd)
- libnghttp2/1.70.0
- zlib/1.3.1.1 (override for PIC variant)

## 注意事项

- libsoup 2.74.3 使用 libsoup-2.4 API（与 libsoup3 的 soup-3.0 API 不同）
- 包含目录: include/libsoup-2.4
- 库文件: libsoup-2.4.so.1.11.2
- OHOS strip 破坏 .codesign 哈希 → generate() 中 tc.strip = None
- meson install 可能破坏 DT_RUNPATH → package() 中复制原始构建产物
---

**编译结束**: 2026-09-03 21:48
**最终状态**: published

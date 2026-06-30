# grim 1.4.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 安装依赖：先编译 wayland-protocols 1.36 和 wayland 1.23.1（meson构建）
2. sign-elf 签名 wayland-scanner 二进制
3. 配置 grim：
   ```bash
   meson setup builddir --prefix=$DEFAULT_PREFIX -Dman-pages=disabled -Dwerror=false
   ```
4. 编译：`ninja -C builddir -j2`
5. 安装：`DESTDIR=$TEST_PREFIX ninja -C builddir install && ninja -C builddir install`
6. 签名验证：sign-elf grim

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | wayland-scanner 执行 Operation not permitted | ELF 未签名 | sign-elf 签名后可执行 |
| 2 | grim 运行时找不到 libwayland-client.so.0 | 无 RPATH | 使用 LDFLAGS=-Wl,-rpath,... 设置 RUNPATH |
| 3 | 构建系统类型误判为 autotools | manifest 默认值 | 手动修正为 meson |

## 依赖版本

- wayland-client 1.23.1
- wayland-protocols 1.36
- libpng 1.6.43
- pixman 0.46.4
- libjpeg 3.1.4.1

## 验证结果

```bash
grim -h
# 输出: Usage: grim [options...] [output-file]
```

## 注意事项

- grim 是 Wayland 截图工具，运行需要 Wayland compositor 环境
- 需要先编译安装 wayland 和 wayland-protocols
- wayland-scanner 需要 ELF 签名后才能执行
---

**编译结束**: 2026-06-03 23:59
**最终状态**: built

# pango 1.50.14 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 解压源码包到工作目录
2. 配置 meson 构建：
   ```bash
   meson setup build --prefix=$DEFAULT_PREFIX \
     -Dcairo=enabled \
     -Dxft=disabled \
     -Dintrospection=disabled
   ```
3. 编译：`ninja -C build`
4. 安装到 staging：`meson install -C build --destdir=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 cairo-ft 包 | cairo 编译时没有生成 cairo-ft.pc 文件 | 手动创建 cairo-ft.pc 文件 |
| 2 | meson 报错 Unknown option "documentation" | pango 1.50.14 的选项名是 gtk_doc，不是 documentation | 使用正确的选项名 |

## 源码修改

无补丁，源码无需修改。

## 依赖版本

- glib-2.0: 2.88.0
- harfbuzz: 14.2.0
- freetype2: 26.6.20
- fontconfig: 2.16.0
- fribidi: 1.0.13
- libpng: 1.6.43
- cairo: 1.18.2
- pixman-1: 0.44.0

## 验证结果

```bash
pkg-config --modversion pango
# 预期输出: 1.50.14
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pango-1.50.14-ohos-aarch64.tar.gz | TBD | 预编译包 |

## 注意事项

1. cairo 必须启用 freetype 支持，否则 pango 无法找到 cairo-ft 后端
2. 如果 cairo-ft.pc 缺失，需要手动创建（或在重新编译 cairo 时确保生成）
---

**编译结束**: 2026-05-19 15:41
**最终状态**: built

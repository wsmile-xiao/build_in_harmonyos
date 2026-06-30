# libraqm 0.10.5 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-20
- 编译器: clang
- 状态: published

## 编译步骤

1. 下载源码
   ```bash
   curl -L -o raqm-0.10.5.tar.xz "https://github.com/HOST-Oman/libraqm/releases/download/v0.10.5/raqm-0.10.5.tar.xz"
   tar -xf raqm-0.10.5.tar.xz
   cd raqm-0.10.5
   ```

2. Configure
   ```bash
   meson setup build --prefix=~/usr/local --wrap-mode=nofallback
   ```

3. 编译安装
   ```bash
   ninja -C build
   ninja -C build install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试程序链接失败 | libpng NEON 符号未定义 | 不影响主库，跳过测试 |

## 依赖版本

- freetype2 26.6.20
- harfbuzz 14.2.0
- fribidi 1.0.16

## 验证结果

```bash
pkg-config --modversion raqm
# 输出: 0.10.5
```

---
**编译结束**: 2026-05-20 11:43
**最终状态**: published
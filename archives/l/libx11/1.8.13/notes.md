# libx11 1.8.13 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-08
- 编译器: clang/clang++ (15.0.4 OHOS toolchain)
- 状态: built

## 编译步骤

1. 下载源码 tarball: libX11-1.8.13.tar.xz (sha256: 69606f485c2c07c14ef64f75b7bb326d48587af33795d9ab3e607c0b5f94f11c)
2. 解压并应用 OHOS autotools 修复:
   - configure shebang: `#! /bin/sh` → `#!/data/service/hnp/bin/bash`
   - umask: `umask 077` → `umask 022`
3. 配置:
   ```
   ./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
     --disable-docs --without-xmlto --without-fop --without-xsltproc \
     --enable-shared --disable-static
   ```
4. 编译: `make -j4`
5. 上游测试: `make check` (运行 nls/compose-check.pl)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure shebang 指向 /bin/sh | HarmonyOS 无 /bin/sh | 替换为 /data/service/hnp/bin/bash |
| 2 | umask 077 导致临时目录权限问题 | E002/HMDFS 限制 | 替换为 umask 022 |

## 依赖版本

| 依赖 | 版本 |
|------|------|
| xorgproto | 2025.1 |
| libxau | 1.0.11 |
| libxcb | 1.17.0 |
| xtrans | 1.4.0 |
| xcb-proto | 1.17.0 |

## 验证结果

```bash
make check  # 上游 compose-check.pl 测试
conan create archives/l/libx11/1.8.13/conanfile.py --profile=ohos-aarch64 --build=missing
```

---

**编译结束**: 2026-08-08
**最终状态**: built

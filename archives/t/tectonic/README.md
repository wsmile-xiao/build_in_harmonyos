# Tectonic

A modernized, complete, embeddable TeX/LaTeX engine. Tectonic is forked from the XeTeX extension to the classic "Web2C" implementation of TeX and uses the TeXLive distribution of support files. It is written in Rust with C/C++ bridge crates for font rendering, text shaping, and Unicode support.

- **Homepage**: https://tectonic-typesetting.github.io/
- **Repository**: https://github.com/tectonic-typesetting/tectonic
- **License**: MIT
- **Build System**: Cargo (Rust)
- **Type**: Command-line tool
- **Category**: doc (文档排版)

## 版本

| 版本 | 状态 | 构建日期 | 说明 |
|------|------|----------|------|
| 0.16.9 | built | 2026-07-23 | Rust TeX 引擎，8 个 C/C++ 依赖静态链接，LaTeX 编译功能正常 |

## 功能

Tectonic 将传统的 TeX 工具链（tex, xdvi, dvips 等）整合为单一可执行文件：

- **XeTeX 引擎**: 支持 Unicode 文本和现代 OpenType 字体
- **自动依赖管理**: 编译时自动从网络获取所需的 TeX 包
- **单一二进制**: 无需安装完整 TeX 发行版
- **可嵌入**: 提供 Rust 库 API，可作为其他应用的 TeX 后端
- **输出 PDF**: 直接生成 PDF 输出，无需 DVI 中间步骤

## 包结构

```
bin/tectonic       — wrapper 脚本 (#!/system/bin/sh, 自动设置 LD_LIBRARY_PATH)
bin/tectonic.real  — ELF64 aarch64 二进制 (~60MB, PIE, 未 strip)
lib/libexpat.so    — 唯一动态 C/C++ 依赖 (182KB, expat 上游 bug 无法静态)
```

**使用方式**: 直接运行 `tectonic` 即可，无需设置任何环境变量。

## 构建环境

| 组件 | 版本 | 路径/来源 |
|------|------|----------|
| Rust (rustc/cargo) | 1.97.1 | Harmonybrew (~/.harmonybrew/bin/) |
| Host triple | aarch64-unknown-linux-ohos | — |
| C/C++ 编译器 | clang 15.0.4 | HNP 工具链 (/data/service/hnp/bin/) |
| Conan | 2.29.1 (OHOS 适配版) | — |
| meson | 1.11.1 | pip3 install meson (fontconfig 重建需要) |
| Conan profile | ohos-aarch64 | ci/conan/profiles/ohos-aarch64 |

## C/C++ 依赖（8 个静态 + 1 个动态打包）

| 依赖 | 版本 | 用途 | 链接方式 |
|------|------|------|----------|
| freetype | 2.14.3 | 字体光栅化 | ✅ 静态 |
| fontconfig | 2.18.1 | 字体查找/配置 | ✅ 静态 |
| harfbuzz | 14.2.0.2 | 文本整形（含 graphite2 shaper） | ✅ 静态 |
| graphite2 | 1.3.14 | Graphite 智能字体系统 | ✅ 静态 |
| icu4c | 78 | Unicode 17.0 支持 | ✅ 静态 |
| libpng | 1.6.58 | PNG 图像解码 | ✅ 静态 |
| zlib | 1.3.1.1 | 压缩 | ✅ 静态 |
| openssl | 3.5.6 | TLS（网络下载 TeX 包） | ✅ 静态 |
| expat | 2.8.2 | XML 解析 (fontconfig 传递依赖) | ⚠️ 动态 (.so 打包) |

### expat 动态链接说明

expat 的 conanfile.py 硬编码了 `EXPAT_SHARED_LIBS = "ON"`（上游 bug），即使设置 `shared=False` 也只生成 .so。
解决方案：将 libexpat.so (182KB) 打包到 `lib/` 目录，wrapper 脚本通过 `LD_LIBRARY_PATH` 让二进制自动找到。

## OHOS 适配关键点

### 构建配置

1. **`.cargo/config.toml`**: 配置 OHOS target 链接器（clang + lld）、C/C++ 编译器（CC/CXX）、crates.io 镜像源（rsproxy.cn）
2. **`--features external-harfbuzz`**: 使用系统 harfbuzz（Conan 包）而非 git submodule
3. **`default_options = {"*:shared": False}`**: 强制所有 C/C++ 依赖静态链接
4. **`icu-uc.pc` 兼容**: Conan 生成 `icu4c.pc`，tectonic 期望 `icu-uc`，在 build() 中复制
5. **`DEP_FONTCONFIG_INCLUDE_PATH`**: engine_xetex 不直接依赖 bridge_fontconfig，需手动设置
6. **`SSL_CERT_FILE`**: 设置 `/etc/ssl/certs/cacert.pem`，使 reqwest 可下载 TeX bundle

### 打包方案

7. **wrapper 脚本**: Conan `copy()` 和打包后处理破坏 ELF `$ORIGIN` RUNPATH → 将实际二进制保存为 `tectonic.real`，创建 wrapper 脚本 `tectonic` 设置 `LD_LIBRARY_PATH`
8. **wrapper shebang**: 使用 `#!/system/bin/sh`（非 `#!/bin/bash`，OHOS 上不存在）
9. **libexpat.so 打包**: 将 .so 复制到 `lib/` 目录，wrapper 脚本指向该路径

### 已知限制

- **expat 动态链接**: 上游 conanfile.py bug，无法静态（已通过 .so 打包 + wrapper 脚本解决）
- **TeX bundle 首次下载**: 首次编译 LaTeX 文档时需从网络下载 TeX 包（~几分钟），之后缓存到本地
- **Fontconfig 警告**: 编译 LaTeX 时可能出现 "Cannot load default config file" 警告，不影响功能
- **二进制未 strip**: 60MB，strip 后约 20MB（可通过 `strip bin/tectonic.real` 减小体积）

## 验证结果

```
✅ tectonic --version → Tectonic 0.16.9
✅ tectonic --help → 显示所有选项
✅ LaTeX 编译 → 成功生成 test.pdf (6.5KB)
✅ conan-verify 8/8 门禁 PASS
✅ CI 干净构建 (conan create exit 0)
✅ 安全特性: PIE + NX + RELRO
✅ 无需 LD_LIBRARY_PATH 即可运行 (wrapper 脚本)
```

## 参考

- 官网: https://tectonic-typesetting.github.io/
- GitHub: https://github.com/tectonic-typesetting/tectonic
- 文档: https://docs.rs/tectonic
- 参考先例: archives/g/gifski/1.34.0/（同为 cargo 构建的 OHOS 适配包）

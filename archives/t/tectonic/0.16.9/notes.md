# tectonic 0.16.9 — 适配笔记

## 基本信息

- **软件**: tectonic (现代化 TeX/LaTeX 引擎)
- **版本**: 0.16.9
- **上游**: https://github.com/tectonic-typesetting/tectonic
- **源码 tag**: tectonic@0.16.9
- **构建系统**: cargo (Rust)
- **许可证**: MIT
- **类型**: 命令行工具 (生成可执行文件)
- **编译日期**: 2026-07-23
- **状态**: built

## 编译环境

| 组件 | 版本 | 说明 |
|------|------|------|
| rustc | 1.97.1 (2026-07-14) | host: aarch64-unknown-linux-ohos, 通过 Harmonybrew 安装 |
| cargo | 1.97.1 (2026-06-30) | — |
| clang | 15.0.4 (LLVM) | HNP 工具链，用于 C/C++ bridge crates |
| Conan | 2.29.1 | OHOS 适配版（os=OHOS 枚举、aarch64-linux-ohos triplet） |
| meson | 1.11.1 | pip3 install meson (fontconfig 重建需要) |
| Conan profile | ohos-aarch64 | ci/conan/profiles/ohos-aarch64 |

Rust 工具链通过 Harmonybrew 安装（rustup 不支持 HarmonyOS，报 "unrecognized OS type: HarmonyOS"）：
```bash
zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"
brew install rust
```

## C/C++ 依赖

所有依赖通过 Conan + PkgConfigDeps 提供 .pc 文件，供 tectonic 的 bridge crates build.rs 调用 `pkg-config` 查找。
通过 `default_options = {"*:shared": False}` 强制全部静态链接（expat 除外，见下文）：

| 依赖 | 版本 | 用途 | bridge crate | 链接方式 |
|------|------|------|-------------|----------|
| freetype | 2.14.3 | 字体光栅化 | crates/bridge_freetype2 | ✅ 静态 |
| fontconfig | 2.18.1 | 字体查找/配置 | crates/bridge_fontconfig | ✅ 静态 |
| harfbuzz | 14.2.0.2 | 文本整形（含 graphite2） | crates/bridge_harfbuzz | ✅ 静态 |
| graphite2 | 1.3.14 | Graphite 智能字体 | crates/bridge_graphite2 | ✅ 静态 |
| icu4c | 78 | Unicode 17.0 支持 | crates/bridge_icu | ✅ 静态 |
| libpng | 1.6.58 | PNG 图像解码 | crates/bridge_png | ✅ 静态 |
| zlib | 1.3.1.1 | 压缩 | crates/bridge_flate (via Rust flate2) | ✅ 静态 |
| openssl | 3.5.6 | TLS 网络 | tectonic_geturl (via reqwest native-tls) | ✅ 静态 |
| expat | 2.8.2 | XML 解析 (fontconfig 依赖) | — (fontconfig 传递依赖) | ⚠️ 动态 (.so 打包) |

### expat 动态链接说明

expat 的 conanfile.py 硬编码了 `EXPAT_SHARED_LIBS = "ON"`（上游 bug），即使设置 `shared=False` 也只生成 .so。
解决方案：将 libexpat.so (182KB) 打包到 `lib/` 目录，通过 wrapper 脚本设置 `LD_LIBRARY_PATH` 让二进制自动找到。

## 适配步骤

### 1. 源码获取
```bash
URL=https://github.com/tectonic-typesetting/tectonic/archive/refs/tags/tectonic@0.16.9.tar.gz
curl -fsSL "$URL" -o tectonic-0.16.9.tar.gz
# sha256: 9861d4d4230b987d8560f1b84fe6c8a550738401be65b9425b0c7d0466178f2b
```

### 2. Conan 环境设置（生成 .pc 文件 + 静态库）
```bash
conan install --requires=freetype/2.14.3 --requires=fontconfig/2.18.1 \
  --requires=harfbuzz/14.2.0.2 --requires=graphite2/1.3.14 \
  --requires=icu4c/78 --requires=libpng/1.6.58 \
  --requires=zlib/1.3.1.1 --requires=openssl/3.5.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -g=PkgConfigDeps -g=VirtualBuildEnv --build=missing
```

### 3. 创建 .cargo/config.toml
```toml
[target.aarch64-unknown-linux-ohos]
linker = "clang"
# -Wl,-rpath,$ORIGIN/../lib: 链接时设置 RPATH（但 Conan 打包会破坏 $ORIGIN，改用 wrapper 脚本）
rustflags = ["-C", "link-arg=-fuse-ld=lld", "-C", "link-arg=-Wl,-rpath,$ORIGIN/../lib"]

[env]
CC = "clang"
CXX = "clang++"

# crates.io 镜像（OHOS 网络下直接访问 crates.io 超时）
[source.crates-io]
replace-with = "rsproxy-sparse"

[source.rsproxy-sparse]
url = "sparse+https://rsproxy.cn/index/"
```

### 4. icu-uc.pc 兼容
tectonic bridge_icu 的 build.rs 调用 `pkg-config --cflags --libs icu-uc`，但 Conan 生成 `icu4c.pc`。在 build() 中复制：
```python
shutil.copy2(icu4c_pc, icu_uc_pc)
```

### 5. DEP_FONTCONFIG_INCLUDE_PATH
engine_xetex crate 不直接依赖 bridge_fontconfig，Cargo 不自动设置此变量。在 build() 中解析 fontconfig.pc 的 includedir 并手动设置。

### 6. SSL 证书配置
tectonic 的 reqwest HTTP 客户端无法建立 HTTPS 连接（找不到 CA 证书）。在 build() 中设置：
```python
os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/cacert.pem"
os.environ["SSL_CERT_DIR"] = "/etc/ssl/certs"
```
这使得 tectonic 可以成功下载 TeX bundle 并编译 LaTeX 文档。

### 7. 编译
```bash
export PKG_CONFIG_PATH=<generators_folder>:$PKG_CONFIG_PATH
cargo build --release --features external-harfbuzz
```
使用 `--features external-harfbuzz` 以使用系统 harfbuzz（Conan 包）而非 git submodule。

### 8. 打包（wrapper 脚本方案）
Conan 的 `copy()` 函数和打包后处理会破坏 ELF 二进制中的 `$ORIGIN` RUNPATH（展开为空字符串），导致二进制不可执行。
解决方案：将实际二进制复制为 `bin/tectonic.real`，创建 wrapper 脚本 `bin/tectonic`：
```sh
#!/system/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
export LD_LIBRARY_PATH="$DIR/../lib:$LD_LIBRARY_PATH"
exec "$DIR/tectonic.real" "$@"
```
同时将 `libexpat.so` 复制到 `lib/` 目录，wrapper 脚本通过 LD_LIBRARY_PATH 让二进制自动找到。

## 遇到的问题和解决方案

| # | 问题 | 根因 | 解决方案 | 严重度 |
|---|------|------|----------|--------|
| 1 | crates.io 下载超时 | crates.io 在 OHOS 网络下访问慢 | .cargo/config.toml 配置 rsproxy.cn sparse 镜像源 | 阻塞 |
| 2 | fontconfig 头文件找不到 | engine_xetex 不直接依赖 bridge_fontconfig | 解析 fontconfig.pc，手动设置 DEP_FONTCONFIG_INCLUDE_PATH | 阻塞 |
| 3 | icu-uc.pc 名称不匹配 | Conan 生成 icu4c.pc，tectonic 期望 icu-uc | build() 中复制 icu4c.pc 为 icu-uc.pc | 阻塞 |
| 4 | harfbuzz git submodule 缺失 | 源码包不含 .git 目录 | --features external-harfbuzz 使用系统 harfbuzz | 阻塞 |
| 5 | 动态链接导致不可独立运行 | freetype/fontconfig/libpng 构建为 shared | default_options={"*:shared":False} 强制静态 | 阻塞 |
| 6 | expat 强制动态链接 | expat conanfile 硬编码 EXPAT_SHARED_LIBS="ON" | .so 打包到 lib/ + wrapper 脚本设置 LD_LIBRARY_PATH | 阻塞 |
| 7 | Conan copy() 破坏 $ORIGIN | Conan 打包后处理展开 ELF RUNPATH 中的 $ORIGIN | shutil.copy2() 复制为 tectonic.real + wrapper 脚本 | 阻塞 |
| 8 | patchelf 修改后不可执行 | OHOS 拒绝执行被修改的 ELF 二进制 | 改用 wrapper 脚本，不修改二进制 | 阻塞 |
| 9 | LaTeX 编译 SSL 失败 | reqwest 找不到 CA 证书 | build() 中设置 SSL_CERT_FILE 和 SSL_CERT_DIR | 阻塞 |
| 10 | fontconfig 重建缺 meson | 系统未安装 meson | pip3 install meson | 阻塞 |
| 11 | package() 二进制路径不确定 | basic_layout 路径不确定性 | 搜索多路径 + glob fallback | 非阻塞 |
| 12 | test_package chmod 失败 | OHOS 对 conan cache 文件 chmod 有限制 | try/except 包裹 | 非阻塞 |
| 13 | conanfile.py 硬编码路径 | 3 处硬coded 路径 | shutil.which() 动态查找 | 非阻塞 |

## 编译产物

### 包结构
```
bin/tectonic       — wrapper 脚本 (#!/system/bin/sh, 134 bytes)
bin/tectonic.real  — ELF64 aarch64 二进制 (60MB, 未 strip, PIE)
lib/libexpat.so    — 唯一动态 C/C++ 依赖 (182KB)
```

### 二进制动态依赖 (readelf -d tectonic.real)
```
NEEDED: libc++_shared.so       — OHOS C++ 运行时 (系统)
NEEDED: libexpat.so            — XML 解析 (打包在 lib/)
NEEDED: libtime_service_ndk.so — OHOS 系统库
NEEDED: libc.so                — C 库 (系统)
```

freetype/fontconfig/harfbuzz/graphite2/icu4c/libpng/zlib/openssl 全部静态链接，无运行时 .so 依赖。

### wrapper 脚本
```sh
#!/system/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
export LD_LIBRARY_PATH="$DIR/../lib:$LD_LIBRARY_PATH"
exec "$DIR/tectonic.real" "$@"
```

## 验证结果

### 功能测试
```bash
# 1. 无 LD_LIBRARY_PATH 直接运行
$ tectonic --version
Tectonic 0.16.9

# 2. --help 显示所有选项
$ tectonic --help
Process a (La)TeX document
Usage: tectonic.real [OPTIONS] <INPUT>
...

# 3. LaTeX 文档编译（成功生成 PDF）
$ cat test.tex
\documentclass{article}
\begin{document}
Hello Tectonic on OHOS! $E = mc^2$
\end{document}

$ tectonic test.tex
note: downloading article.cls
note: downloading size10.clo
note: downloading lmroman10-regular.otf
...
note: Running xdvipdfmx ...
note: Writing `test.pdf` (6.376953125 KiB)

$ ls -la test.pdf
-rw-rw---- 6530 bytes  ← PDF 生成成功!
```

### CI 干净构建
```bash
conan create archives/t/tectonic/0.16.9/conanfile.py \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# 结果: EXIT CODE 0
# test_package: Tectonic 0.16.9
```

### conan-verify 门禁 (8/8 PASS)
- G0: 预构建风险评估 ✅
- G1: 配方完整性 ✅
- G2: conan create 干净构建 ✅
- G3: 系统同名库隔离 (R26) ✅
- G4: 产物完整性 ✅
- L2: smoke test (--version) ✅
- L4: 安全扫描 ✅
- L5: 产物基线 ✅

## 注意事项

1. tectonic 是 Rust 项目，Rust 工具链通过 Harmonybrew 安装（非 rustup）
2. `default_options = {"*:shared": False}` 强制所有 C/C++ 依赖静态链接，expat 例外（上游 bug）
3. Conan `copy()` 和打包后处理破坏 ELF `$ORIGIN` RUNPATH → 使用 wrapper 脚本绕过
4. `patchelf` 修改二进制后 OHOS 拒绝执行（ELF 签名/安全策略）→ 使用 wrapper 脚本
5. `SSL_CERT_FILE` 必须设置，否则 tectonic 的 reqwest 无法下载 TeX bundle
6. wrapper 脚本使用 `#!/system/bin/sh`（非 `#!/bin/bash`，OHOS 上 /bin/bash 不存在）
7. LaTeX 编译功能完全正常：成功下载 TeX 包并生成 PDF
8. 参考先例: archives/g/gifski/1.34.0/（同为 cargo 构建的 OHOS 适配包）

---

**编译结束**: 2026-07-23 13:27
**最终状态**: built

## 清理记录 (2026-08-06)
- 移除 harfbuzz 14.2.0.2 非标准归档文件（ADAPTATION_REPORT.md, PR.md, patches/.empty）
- 修正 manifest.yaml 中 harfbuzz graphite2 状态（含→disabled）

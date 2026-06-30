# BibTeXConv

BibTeX 格式转换工具，支持将 BibTeX 文件转换为多种格式（ODT、HTML 等）。

## 功能特性

- BibTeX 到 ODT 转换
- BibTeX 到 HTML 转换
- IETF RFC 到 BibTeX 转换
- 支持 SSL/TLS 加密连接

## 编译指导

在 HarmonyOS/OpenClaw 平台编译时需要：

1. 安装依赖：
   - curl 8.19.0（通过 cmd-pkgs 安装）
   - openssl 1.1.1w（已预装）

2. 配置环境：
   ```bash
   export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
   cmake -DCMAKE_INSTALL_PREFIX=/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DOPENSSL_ROOT_DIR=$HOME/usr/local ..
   ```

3. 编译打包：
   ```bash
   make -j2
   make install DESTDIR=$HOME/test-install-bibtexconv-2.2.2/usr/local
   python3 scripts/ohc-run.py package bibtexconv 2.2.2 \
         --prefix $HOME/test-install-bibtexconv-2.2.2/usr/local
   ```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [2.2.2](./2.2.2/) | published | 2026-06-11 |
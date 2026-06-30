# slowhttptest 1.9.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **下载源码**：从 GitHub 下载 v1.9.0 tarball
2. **解压源码**：解压到 ~/builds/slowhttptest-1.9.0.work
3. **设置环境变量**：
   - `export TMPDIR=$HOME/tmp`
   - `export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig`
   - `export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH`
4. **修改 configure 和 config.status**：修改临时目录创建逻辑（详见下文）
5. **配置编译**：
   ```bash
   ./configure \
       --prefix=$HOME/usr/local \
       --disable-dependency-tracking \
       LDFLAGS="-L$HOME/usr/local/lib" \
       CPPFLAGS="-I$HOME/usr/local/include"
   ```
6. **编译**：`make -j2`
7. **安装到测试目录**：`make install DESTDIR=$HOME/test-install-slowhttptest-1.9.0`
8. **创建预编译包**：`python3 ohc-run.py package slowhttptest 1.9.0`
9. **本地验证**：解压预编译包并测试功能

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 临时目录权限问题 | HMDFS 文件系统不支持在 umask 077 创建的子目录中写入文件 | 修改 configure/config.status，使用 $TMPDIR 替代硬编码 ./confXXXXXX，移除 umask 077 |
| 2 | configure 不识别 OpenSSL | configure 硬编码 macOS OpenSSL 路径 | 通过 LDFLAGS 和 CPPFLAGS 参数指定 OpenSSL 路径 |
| 3 | 运行时缺少 libssl.so.1.1 | 预编译包需要包含依赖库 | package 脚本自动收集 OpenSSL 动态库到 lib/external/ |

### 关键修复：HMDFS 临时目录问题

**问题描述**：
```
./config.status[744]: can't create ./confXXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根本原因**：
- configure/config.status 使用 `(umask 077 && mktemp -d "./confXXXXXX")` 创建临时目录
- umask 077 导致创建的目录权限为 `drwx--S---`，无法在其中创建文件
- HMDFS 文件系统对此类权限的目录有特殊限制

**解决方案**：
1. 修改 configure 第 7291 行：
   ```bash
   # 原代码：
   tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&

   # 修改为：
   tmp=`mktemp -d "$TMPDIR/confXXXXXX" 2>/dev/null` &&
   ```
2. 同样修改 config.status 第 581 行
3. 设置 TMPDIR 环境变量：`export TMPDIR=$HOME/tmp`

## 源码修改

**文件**：configure
**修改内容**：第 7291 行，临时目录创建逻辑

**文件**：config.status（configure 生成的）
**修改内容**：第 581 行，临时目录创建逻辑

## 依赖版本

- OpenSSL 1.1.1w（已预编译并安装到 ~/usr/local）

## 验证结果

```bash
# 预编译包内容验证
tar tzf slowhttptest-1.9.0-ohos-aarch64.tar.gz
bin/slowhttptest
lib/external/libssl.so.1.1
lib/external/libcrypto.so.1.1
share/man/man1/slowhttptest.1

# 功能验证
cd ~/tmp/slowhttptest-verify
export LD_LIBRARY_PATH=$PWD/lib/external:$LD_LIBRARY_PATH
bin/slowhttptest -h
# 输出：slowhttptest, a tool to test for slow HTTP DoS vulnerabilities - version 1.9.0

# RPATH 验证
readelf -d bin/slowhttptest | grep RUNPATH
# Library runpath: [$ORIGIN/../lib:$ORIGIN/../lib/external]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| slowhttptest-1.9.0-ohos-aarch64.tar.gz | 3.4M | 预编译包（含 OpenSSL 依赖） |
| slowhttptest-1.9.0-ohos-aarch64-debug.tar.gz | 1.2M | 调试符号包 |

## 注意事项

1. **临时目录问题**：HMDFS 文件系统有特殊的权限限制，编译 autotools 项目时需要注意 configure/config.status 的临时目录创建逻辑
2. **OpenSSL 依赖**：预编译包包含 OpenSSL 1.1.1w 动态库，部署时会自动安装到 lib/external/
3. **RPATH 设置**：预编译包的二进制已设置正确的 RUNPATH，可以找到 lib/external 中的依赖库

---

**编译结束**: 2026-06-11 12:27
**最终状态**: published
# pkcs11-tools 2.6.0 适配笔记

## 编译环境
- 构建系统: autotools（需要 bootstrap.sh）
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

由于 GitHub tarball 不包含 configure 脚本，需要运行 bootstrap.sh，但 HMDFS 文件系统限制导致 bootstrap.sh 失败。解决方案如下：

1. **手动 bootstrap**：
   - 创建 Python 脚本 `manual-bootstrap.py`，从 .gnulib 目录复制所需的 gnulib 模块文件
   - 复制 config.guess, config.sub, build-aux 文件
   - 复制 m4 宏文件和 lib 源文件
   - 创建简化版 gl/Makefile.am

2. **运行 autoreconf**：
   - `autoreconf -vfi` 成功生成 configure 脚本

3. **解决 config.status 权限问题**：
   - HMDFS 不支持在某些临时目录创建文件
   - 创建 `.config-tmp` 目录，修改 config.status 使用此固定目录
   - 成功运行 config.status 生成 Makefile

4. **克隆缺失的 submodule**：
   - include/oasis-pkcs11 是 git submodule，tarball 中为空
   - 克隆 oasis-pkcs11 submodule 到 include/oasis-pkcs11/
   - 创建 working/3-00-current/ 目录并复制头文件

5. **修复 Makefile LIBCRYPTO 变量**：
   - configure 生成了无效的变量名 `[LIBCRYPTO]_CFLAGS` 和 `[LIBCRYPTO]_LIBS`
   - 手动修改 lib/Makefile 和 src/Makefile，替换为正确的 OpenSSL 路径

6. **添加缺失的定义**：
   - include/config.h：添加 `#define _GL_CONFIG_H_INCLUDED 1`
   - include/target.h：手动创建，定义 TARGET_CPU_TYPE, TARGET_ARCH_TYPE 等宏

7. **编译和安装**：
   - `make -j1` 编译成功（有大量 OpenSSL deprecated warnings，非致命）
   - `make install DESTDIR=$TEST_PREFIX` 安装成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bootstrap.sh 失败 | HMDFS 不支持在临时目录创建文件，且 tarball 没有 .git 目录 | 创建 manual-bootstrap.py 手动复制 gnulib 文件 |
| 2 | config.status 失败 | HMDFS 不支持在 mktemp 创建的临时目录中创建文件 | 创建固定目录 .config-tmp，修改 config.status |
| 3 | oasis-pkcs11 缺失 | git submodule，tarball 中为空 | 克隆 oasis-pkcs11，创建 working/3-00-current 目录 |
| 4 | LIBCRYPTO 变量无效 | configure 生成了包含方括号的无效变量名 | 手动修改 Makefile 替换为正确路径 |
| 5 | target.h 缺失 | AX_CREATE_TARGET_H 宏未正确执行 | 手动创建 target.h 定义目标平台宏 |
| 6 | _GL_CONFIG_H_INCLUDED 缺失 | 简化的 gnulib-m4.m4 不完整 | 在 config.h 中添加此宏定义 |

## 源码修改

### 新增文件
- `manual-bootstrap.py`: 手动 bootstrap 脚本，替代 gnulib-tool
- `include/target.h`: 目标平台定义头文件

### 修改文件
- `include/config.h`: 添加 `_GL_CONFIG_H_INCLUDED 1`
- `lib/Makefile`: 修复 LIBCRYPTO_CFLAGS 和 LIBCRYPTO_LIBS
- `src/Makefile`: 修复 LIBCRYPTO_CFLAGS 和 LIBCRYPTO_LIBS
- `config.status`: 修改临时目录路径为 .config-tmp

## 依赖版本

- OpenSSL: 3.5.6（预编译包）
- libtool: 系统自带
- autoconf: 2.72
- automake: 系统自带
- pkg-config: 系统自带
- flex: 2.6.4
- bison: 3.8.2
- perl: 系统自带

## 验证结果

编译成功，生成 22 个可执行文件：
- p11mkcert, p11rewrap, p11wrap, p11unwrap, p11cp, p11ls, p11cat, p11more, p11od, p11rm, p11mv
- p11slotinfo, p11req, p11importcert, p11importpubk, p11importdata, p11keycomp, p11setattr
- masqreq, p11keygen, p11kcv
- with_beid, with_luna, with_nfast, with_nss, with_softhsm, with_utimaco, with_aws

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pkcs11-tools-2.6.0-ohos-aarch64.tar.gz | 8.8M | 主预编译包（已签名） |
| pkcs11-tools-2.6.0-ohos-aarch64-debug.tar.gz | 1.9M | 调试符号包 |

## 注意事项

1. **HMDFS 限制**：不支持在 mktemp 创建的临时目录中创建文件，需使用固定目录
2. **Git submodule**：oasis-pkcs11 submodule 需手动克隆并设置正确的目录结构
3. **configure 变量问题**：pkg-config 相关变量名包含方括号，需手动修复
4. **OpenSSL deprecated warnings**：编译有大量 deprecated 警告，但不影响编译成功
5. **硬链接限制**：HMDFS 不支持硬链接，libtool 会报错但不影响编译结果
---

**编译结束**: 2026-05-21 20:47
**最终状态**: built

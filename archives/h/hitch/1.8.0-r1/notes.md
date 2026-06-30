# hitch 1.8.0-r1 编译笔记

## 软件信息
- **名称**: hitch
- **版本**: 1.8.0-r1
- **描述**: TLS代理/SSL终止代理
- **下载源**: https://download.savannah.nongnu.org/releases/hitch/hitch-1.8.0-r1.tar.gz

## 依赖
- libev 4.33（已预编译）
- openssl 1.1.1w（已预编译）
- libcrypto 1.1.1w（已预编译）

## 编译过程

### 遇到的问题与解决方案

#### 问题1: configure脚本PKG_CHECK_EXISTS宏未展开
- **现象**: `./configure: line 6011: syntax error: unexpected 'libev,'`
- **原因**: autoreconf时pkg.m4宏文件未正确包含
- **解决**:
  1. 复制pkg.m4到m4目录
  2. 手动修改configure脚本，将PKG_CHECK_EXISTS替换为实际shell代码

#### 问题2: config.status临时目录权限问题
- **现象**: `mktemp -d "./confXXXXXX"`创建的目录无法创建文件
- **原因**: HMDFS文件系统中mktemp创建的目录有setuid属性(S)，导致无法在其中创建文件
- **解决**: 修改config.status脚本，使用mkdir代替mktemp创建临时目录

#### 问题3: configure PKG_CONFIG变量未定义
- **现象**: `$PKG_CONFIG: not found`
- **原因**: configure脚本中PKG_CONFIG变量未初始化
- **解决**: 在configure脚本开头添加`PKG_CONFIG="pkg-config"`

#### 问题4: pkg-config文件prefix路径错误
- **现象**: openssl.pc中的prefix指向test-install目录而非正确路径
- **原因**: 之前编译openssl时DESTDIR模式遗留问题
- **解决**: 手动修正libev.pc、openssl.pc、libcrypto.pc中的prefix路径

#### 问题5: ylwrap脚本LEX/YACC变量为空
- **现象**: ylwrap调用时prog参数为空，导致shift失败
- **原因**: Makefile中LEX和YACC变量未正确设置
- **解决**:
  1. 设置LEX=/data/service/hnp/bin/flex
  2. 设置YACC=/data/service/hnp/bin/bison
  3. 设置LEX_OUTPUT_ROOT=lex.yy（避免空参数问题）

#### 问题6: 缺少编译时头文件路径
- **现象**: `openssl/opensslv.h: No such file or directory`
- **原因**: Makefile中CFLAGS/CPPFLAGS未包含~/usr/local/include
- **解决**: 修改Makefile添加`-I/storage/Users/currentUser/usr/local/include`

#### 问题7: 链接时缺少库
- **现象**: `undefined reference to ENGINE_load_builtin_engines`
- **原因**: Makefile中SSL_LIBS、CRYPTO_LIBS、EV_LIBS变量为空
- **解决**: 添加正确的库链接选项

#### 问题8: bison生成的文件名不匹配
- **现象**: cfg_parser.c不存在，只有cfg_parser.tab.c
- **原因**: ylwrap脚本执行bison后未能正确复制输出文件
- **解决**: 手动复制cfg_parser.tab.c为cfg_parser.c，cfg_parser.tab.h为cfg_parser.h

#### 问题9: manpage生成失败
- **现象**: `hitch.8: No such file or directory`
- **原因**: 发布包缺少.rst文档源文件
- **解决**: 创建空文件绕过（不影响核心功能）

#### 问题10: ELF签名
- **现象**: 编译后的ELF需要重新签名才能在鸿蒙上执行
- **解决**:
  1. llvm-objcopy --remove-section .codesign移除旧签名段
  2. binary-sign-tool sign -selfSign 1重新签名

### 编译参数
```bash
./configure --prefix=/storage/Users/currentUser/usr/local
make -j2
make install DESTDIR=/storage/Users/currentUser/test-install-hitch-1.8.0-r1
```

### 关键修改文件
- `configure`: 手动展开PKG_CHECK_EXISTS宏，添加PKG_CONFIG变量
- `config.status`: 使用mkdir代替mktemp
- `Makefile`: 添加头文件路径和链接库
- `src/Makefile`: 设置LEX、YACC、LEX_OUTPUT_ROOT变量，添加SSL_LIBS等

---

**编译开始**: 2026-05-21 12:00
**编译结束**: 2026-05-21 12:16
**最终状态**: published
**产物**: hitch-1.8.0-r1-ohos-aarch64.tar.gz (509KB)
---

**编译结束**: 2026-05-21 12:16
**最终状态**: built

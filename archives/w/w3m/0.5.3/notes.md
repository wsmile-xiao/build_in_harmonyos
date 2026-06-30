# w3m 0.5.3 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 加载构建上下文：`source .build-context-w3m-0.5.3`
2. 配置环境：`export TMPDIR=$HOME/tmp LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH`
3. 执行 configure：
   ```bash
   TMPDIR=$HOME/tmp CC=clang CXX=clang++ \
   LDFLAGS="-L$HOME/usr/local/lib" \
   CPPFLAGS="-I$HOME/usr/local/include" \
   ./configure --prefix=$HOME/usr/local --with-gc=$HOME/usr/local
   ```
4. 编译：`make -j1`（初次失败）
5. 修复源码后重新编译：`make clean && make -j1`
6. 安装：`make install DESTDIR=$TEST_PREFIX`
7. 本地安装：`make install`
8. 验证：`$HOME/usr/local/bin/w3m -version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | LINES/COLS 符号冲突 | w3m 定义了自己的 LINES/COLS 变量，链接 ncursesw 时符号重复 | 在 terms.c 中添加 __OHOS__ 条件编译，不定义 LINES/COLS（使用 ncursesw 提供的） |
| 2 | RAND_egd 缺失 | OpenSSL 3.0+ 移除了 RAND_egd 函数，但 config.h 定义了 USE_EGD | 手动取消 config.h 中 USE_EGD 定义 |
| 3 | termcap 函数缺失 | w3m 需要 tgetent/tputs 等 termcap 函数，configure 未检测到 ncursesw | 在 Makefile 中手动添加 -lncursesw 链接库 |
| 4 | libgc.so 加载失败 | LD_LIBRARY_PATH 未设置，导致 mktable 无法运行 libgc | 设置 LD_LIBRARY_PATH=$HOME/usr/local/lib |

## 源码修改

### terms.c
```c
#ifdef __OHOS__
/* ncursesw library provides LINES/COLS on OpenHarmony */
#else
int LINES, COLS;
#endif
```
**原因**: 避免与 ncursesw 库中的 LINES/COLS 符号冲突

### config.h
```c
/* #undef USE_EGD */  // 原为 #define USE_EGD
```
**原因**: OpenSSL 3.0+ 不支持 RAND_egd 函数

### Makefile
```makefile
W3M_LIBS = -L./libwc -lwc -lssl -lcrypto -lncursesw  # 手动添加 -lncursesw
```
**原因**: configure 未检测到 ncursesw 库

## 依赖版本

- ncursesw: 6.5.20250216 (静态库 libncursesw.a)
- openssl: 3.5.0
- gc: 8.2.8
- zlib: 1.3.1.zlib-ng

## 验证结果

```bash
$ w3m -version
w3m version w3m/0.5.3, options lang=en,m17n,image,color,ansi-color,mouse,menu,cookie,ssl,ssl-verify,external-uri-loader,w3mmailer,nntp,ipv6,alarm,mark
GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| w3m | 2.6M | ELF 可执行文件 |
| w3mman | 1.1K | Shell 脚本 |

## 注意事项

1. **编译顺序**: w3m 依赖 gc、openssl、ncursesw、zlib，需先编译这些依赖
2. **符号冲突**: w3m 自己定义 LINES/COLS，与 ncursesw 库冲突，需要条件编译
3. **EGD 移除**: OpenSSL 3.0+ 移除了 RAND_egd，需取消 USE_EGD 定义
4. **链接库**: 需手动添加 -lncursesw，configure 未自动检测
5. **make check**: w3m 没有 make check 目标，无测试套件

---

**编译结束**: 2026-05-28 15:44
**预编译包制作**: 2026-05-28 17:16
**最终状态**: published

## 预编译包信息

- **文件名**: w3m-0.5.3-ohos-aarch64.tar.gz
- **大小**: 1.4M
- **路径**: archives/w/w3m/0.5.3/packaging/w3m-0.5.3-ohos-aarch64.tar.gz
- **签名**: self-sign (OpenHarmony ELF signature)
- **RUNPATH**: $ORIGIN/../lib
- **依赖**: libgc.so, libssl.so.3, libcrypto.so.3

## 用户安装指引

```bash
# 1. 安装依赖
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gc 8.2.8
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openssl 3.5.0

# 2. 安装 w3m
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- w3m 0.5.3

# 3. 配置环境
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# 4. 使用
w3m https://example.com
```
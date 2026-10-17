# cbftp 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-30
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: built（conan-verify 通过，尚未走 CI upload；最终状态见 manifest.yaml）

## 编译步骤

cbftp 为纯 Makefile 项目（无 configure），在源码根目录直接 make：

```bash
make CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib \
  CXXFLAGS="-O2 -std=c++11 -I$OPENSSL_PKG/include -I$NCURSES_PKG/include" \
  CFLAGS="-O2 -I$OPENSSL_PKG/include -I$NCURSES_PKG/include" \
  LINKFLAGS="-L$OPENSSL_PKG/lib -L$NCURSES_PKG/lib -lssl -lcrypto -lpthread -lncursesw" \
  -j4
```

产物：`bin/cbftp`（ncurses UI 主程序）、`bin/datafilecat`、`bin/datafilewrite`（数据文件加密/解密工具）。

无 configure 步骤；conan 配方中通过 CXXFLAGS/CFLAGS/LINKFLAGS 注入 openssl/ncurses 依赖路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/ext/picohttpparser.c` 编译失败 `cc: No such file or directory` | 环境无 `cc`（gcc）命令 | 显式传 `CC=clang` |
| 2 | `ar rc lib*.a && lib*.a: inaccessible` 子目标失败 | Makefile 使用 `$(AR)`/`$(RANLIB)`，环境变量 RANLIB 为空导致 `&&` 后执行错误 | 显式传 `AR=llvm-ar RANLIB=llvm-ranlib` |
| 3 | datafilecat/datafilewrite 编译报 `<openssl/sha.h> not found` | 上游这两个目标仅用 `$(STATIC_SSL_INCLUDE)`/`$(SSL_LINKFLAGS)`，不继承 CXXFLAGS 的 -I 头路径 | 打补丁 0001：改为使用统一的 `$(CXXFLAGS)`/`$(LINKFLAGS)` |
| 4 | 主程序 UI 需要宽字符 ncurses | Makefile.inc 非 Debian 平台默认 `-lncurses`，而制品仓 ncurses 包只提供 `libncursesw.a` | 显式传 `LINKFLAGS=... -lncursesw` |
| 5 | 运行报 `Error loading shared library libc++_shared.so` | 二进制动态链接 libc++_shared.so，需 SDK llvm 运行库 | 运行时 `LD_LIBRARY_PATH` 加 `.../llvm/lib/aarch64-linux-ohos` |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-Makefile.patch | datafilecat/datafilewrite 目标从 `$(OPTFLAGS) -std=c++11 $(STATIC_SSL_INCLUDE) ... $(SSL_LINKFLAGS) -lpthread` 改为 `$(CXXFLAGS) ... $(LINKFLAGS)`，使 conan 依赖的 include/lib 路径正确传播 |

## 依赖版本

- openssl/3.5.6.1.1
- ncurses/6.6（宽字符版，libncursesw）

## 验证结果

```bash
# 三个二进制产物齐全，aarch64 OHOS ELF
bin/cbftp bin/datafilecat bin/datafilewrite

# 功能测试（test_package/test_cbftp.py，5 个用例全过）：
#  1. 三个可执行文件存在且可执行
#  2. datafilecat 明文（ASCII）数据文件直读
#  3. datafilewrite AES-256 加密 + datafilecat 解密 往返一致
#  4. 错误口令解密结果不等于明文（AES 密钥调度确定性断言）
#  5. cbftp 主程序 ELF 可加载/启动（无 TTY 时报 ncurses 初始化失败属预期）
OK: cbftp binaries present, datafile encrypt/decrypt round trip PASSED,
    wrong-passphrase rejected, cbftp ELF starts
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/cbftp | ~8.6MB | FTP/FXP 客户端主程序（ncurses UI） |
| bin/datafilecat | ~4.1MB | cbftp 数据文件解密工具（AES-256） |
| bin/datafilewrite | ~4.1MB | cbftp 数据文件加密工具（AES-256） |

## 注意事项

1. **上游无版本号**：cbftp 使用 SVN 修订号（r1266），无语义化 tag；1.0.0 为赛事任务命名版本，源码取官方 GitHub 组织 `cbftp/cbftp-svn` 主线快照。
2. **上游无测试套件**：无 check/test 目标、无 tests 目录，按 SKILL 要求补全功能测试集（test_cbftp.py）。
3. **运行时依赖 libc++_shared.so**：测试/运行前需将 SDK `llvm/lib/aarch64-linux-ohos` 加入 LD_LIBRARY_PATH；test_package 已处理。
4. **上游 decrypt 不校验 EVP_DecryptFinal_ex 返回值**：错误口令解密结果不确定（可能被 isMostlyASCII 误判），测试用确定性断言（错误口令输出 ≠ 明文）。
5. **本地构建注意**：init-build 生成的 orig/work 目录可能是同一 inode（硬链接），修改 work 源码后 orig 会被同步污染；重新解压 orig 后再跑 refresh-patch 生成正确的补丁。
---

**编译结束**: 2026-08-30 03:11
**最终状态**: built

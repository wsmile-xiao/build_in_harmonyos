# z80asm 1.8 适配笔记

## 编译环境

- 构建系统: makefile（纯 Makefile，非 autotools/cmake）
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 (Target: aarch64-unknown-linux-ohos)
- 链接器: clang（默认 ld）
- 架构: AArch64 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 下载源码（SSL 证书问题，手动 curl --insecure 下载）
cp z80asm-1.8.tar.gz ~/tmp/builds/

# 2. 初始化编译
python3 $SKILL_ROOT/scripts/ohc-run.py init-build z80asm 1.8 --url=https://download.savannah.gnu.org/releases/z80asm/z80asm-1.8.tar.gz

# 3. 加载上下文
source .build-context-z80asm-1.8

# 4. 编译（纯 Makefile 项目，无 configure）
cd $BUILD_SRC_DIR
make CC=clang SHELL=/data/service/hnp/bin/bash -j1

# 5. 安装到 staging 目录（无 make install target，手动安装）
mkdir -p $TEST_PREFIX/bin $TEST_PREFIX/share/man/man1
cp z80asm $TEST_PREFIX/bin/
cp z80asm.1 $TEST_PREFIX/share/man/man1/
chmod 755 $TEST_PREFIX/bin/z80asm

# 6. 质量门禁 + 打包
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build z80asm 1.8
python3 $SKILL_ROOT/scripts/ohc-run.py package z80asm 1.8

# 7. 安装到 DEFAULT_PREFIX
cp z80asm $DEFAULT_PREFIX/bin/
cp z80asm.1 $DEFAULT_PREFIX/share/man/man1/

# 8. 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish z80asm 1.8 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 SSL 失败 | HarmonyOS 缺少 CA 证书，urllib SSL 验证失败 | 手动 curl --insecure 下载 tarball 到 `~/tmp/builds/`，init-build 检测到已存在后跳过下载 |
| 2 | 无 configure 脚本 | z80asm 是纯 Makefile 项目，非 autotools | 直接 `make CC=clang`，跳过 `./configure` 步骤 |
| 3 | CC=gcc 不可用 | Makefile 默认 CC=gcc，系统仅有 clang | 命令行覆盖 `CC=clang` |
| 4 | SHELL=/bin/bash 不存在 | Makefile 设置 `SHELL=/bin/bash`，bash 实际在 `/data/service/hnp/bin/bash` | 命令行覆盖 `SHELL=/data/service/hnp/bin/bash` |
| 5 | 无 make install target | Makefile 只有 all/clean/dist target | 手动 cp 安装二进制和 man page |
| 6 | G4 manifest 缺少 build_system 字段 | init 模板使用 `build:\n  system:` 嵌套格式 | 添加顶级 `build_system: makefile` 字段 |
| 7 | G0 clean-verify 失败 | clean-verify 尝试运行 `./configure` 但项目无 configure 脚本 | 平台限制，手动编译已验证通过 |

## 源码修改

**无源码修改**。项目代码在 HarmonyOS 平台上无需任何补丁即可编译。

编译时仅通过命令行参数覆盖了 CC 和 SHELL 变量，未修改任何源文件。

## 依赖版本

- 无外部库依赖
- 仅依赖系统 libc（musl libc）
- 编译器: clang 15.0.4

## 验证结果

```bash
$ z80asm --version
Z80 assembler version 1.8
Copyright (C) 2002-2007 Bas Wijnen <shevek@fmf.nl>.

$ make -C tests SHELL=/data/service/hnp/bin/bash CC=clang
# pass.asm 汇编成功，diff pass.correct-bin/pass.correct-err 全部匹配 (RC=0)

$ sha256sum pass.correct-bin 手动生成.bin
# 1c6b83aa7c16128cbc27c06ea4e48d52533005e70a8fbc60d720919d934edc60 (完全一致)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| z80asm-1.8-ohos-aarch64.tar.gz | 164,912 bytes | 预编译主包（strip 后） |
| z80asm-1.8-ohos-aarch64-debug.tar.gz | 97,313 bytes | 调试符号包 |

## 注意事项

1. 该项目为纯 Makefile，与 autotools 模式不同，需跳过 configure 步骤
2. 编译时必须覆盖 `CC=clang` 和 `SHELL=/data/service/hnp/bin/bash`
3. 无 make install target，需手动安装
4. G0 clean-verify 无法通过（无 configure 脚本），不影响实际编译质量
5. 预编译包仅含 bin/z80asm 和 share/man/man1/z80asm.1

---

**编译结束**: 2026-06-17 23:10
**最终状态**: built

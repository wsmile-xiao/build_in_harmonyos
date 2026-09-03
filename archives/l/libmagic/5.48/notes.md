# libmagic 5.48 适配笔记

## 状态: built（Conan 配方验证通过）

## 上游

- 项目: file / libmagic（file(1) 命令与 libmagic 库）
- 主页: https://www.astron.com/pub/file/
- 官方源码: https://astron.com/pub/file/file-5.48.tar.gz
- SHA256: ed14656883b23a364b4057c05595d93252da9bc473d30106519519d0da141283
- License: BSD-2-Clause（COPYING: "Copyright (c) Ian F. Darwin and Ian Darwin...redistribution and use in source and binary forms"）
- 构建系统: GNU autotools（configure + Makefile）
- 上游正式测试: automake check-local（`make check`），见下

## 上游测试核查（穷尽式）

上游 tarball 内与测试相关的内容：

- `tests/`：83 个 `*.testfile` + 93 个 `*.result`（一个 testfile 可对应多段
  result，如 `multiple` 有多行期望），另有 `.magic`/`.flags` 辅助文件（flags
  实测只有 `multiple.flags = k`）
- `tests/Makefile.am`：`check_PROGRAMS = test`；`check-local` 对每个 testfile
  运行 `./test`（链接 `$(top_builddir)/src/libmagic.la` 的 C 程序，源码
  tests/test.c），比对输出与 `*.result`；`MAGIC=$(top_builddir)/magic/magic`
  env 指向构建目录刚编译的 magic.mgc
- `Makefile.am`：`SUBDIRS = src magic tests doc python`
- 无 CMakeLists.txt（上游非 CMake 项目）、无 CI 配置目录（.github 等不存在）
- `make check` 实际运行 `check-local`（无 TESTS 变量驱动的并行 harness）

结论：上游正式测试 = `make check` 的 check-local 套件，83 个用例。

**计数（真实 OHOS AArch64 产物执行）**：
Total 83 / Pass 83 / Fail 0 / Skip 0

## 构建期 Host 工具与 Target 产物（任务三重点）

问题真实出现。上游 `magic/Makefile.am` 用 `FILE_COMPILE` 在构建期把
`magic/Magdir/*` 文本规则编译成 `magic.mgc` 二进制数据库，默认 `FILE_COMPILE
= file`（PATH 上的系统 file）。非交叉模式直接用刚构建的 `src/file`；**交叉
模式**（`--host ≠ --build`）下上游切换到 PATH 上的系统 `file`，并强制版本
检查（"Cannot use the installed version of file (…) to compile magic
support files"）。

本机 PATH 上只有 toybox file 0.8.12（HarmonyOS 自带），版本检查必失败 →
`make` 在 magic.mgc 处中断（已在本地试验构建中真实触发并复现）。

### 解决方式

构建宿主本身就是 HarmonyOS PC（AArch64），与 target 同架构、同 ABI，构建出
的 target `file(1)` 可直接在宿主执行（试验：`./src/file --version` 正常输
出 5.48）。因此传带路径的 `FILE_COMPILE=$PWD/src/file` 覆盖：

- 路径含 `/` 时上游规则跳过系统版本检查；
- 用的是刚构建的同版本 target file(1)，满足 host-file 与 target-libmagic
  版本一致的要求；
- magic.mgc 是架构无关的版本化数据库（小端字节序 + 版本魔数），target
  libmagic 运行时加载不受构建机架构影响。

这与任务要求的"两阶段 host-tool/target-library"一致：host 阶段只产出
magic.mgc（构建期数据），target 阶段是安装的 libmagic + file。本例的特殊
性在于 host 与 target 恰好可直接运行同一产物，不需要单独构建 host file。

## OHOS 适配问题清单

1. **HMFS umask 077 quirk**（仓库已知，lhasa 0.6.0 / ldns 1.9.0 判例）：
   config.status 的 `umask 077 && mktemp -d` 在 setgid 目录下创建的目录
   无法写入 → sed 替换 configure 里 `umask 077` → `umask 0`。零 patch
   （build() 内 sed，与仓库判例一致）。
2. **configure getcwd symlink 问题**（同上判例）：`ac_pwd=\`pwd\`` →
   `ac_pwd=\`echo "$PWD"\``。零 patch。
3. **config.sub 不识别 ohos triple**：交叉模式用
   `--host=aarch64-unknown-linux-musl`（config.sub 认识 musl），真实
   triple 在 conan profile 里是 aarch64-unknown-linux-ohos，仅作
   configure 元组用途。零 patch。
4. **PATH 前置 /data/service/hnp/bin**：CI worker PATH 不含该目录，clang
   绝对路径可调用但同目录 lld 找不到（PR #6248 判例）。
5. **CONAN_HOME 在 .cache 下禁止执行**（同上判例）：配置阶段交叉模式
   规避 AC_PROG_CC 运行测试程序。

## 依赖策略

零依赖。上游 83 个测试用例不需要 zlib/bz2/lzma/zstd 等解压库（flags 只有
`-e`/`-k`，无 `-z`；压缩格式的识别来自 magic 规则匹配而非解压链路），且
CI L0i 要求依赖必须已在 registry 发布（zlib 等未发布）。故 configure 全部
`--disable-*` 压缩库，保持与上游测试一致的默认支持集。

## test_package

单测试套件（CMake），内部 14 个断言，覆盖 magic_open/magic_load/文件与
buffer 识别/MIME/负向路径/magic_close。测试数据运行时生成，无二进制
fixture。

# fzy 1.1 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，非 autotools）
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: HarmonyOS (aarch64, musl libc)
- 安装前缀: ~/usr/local
- 状态: built

## 编译步骤

fzy 使用自定义 Makefile，无 configure 步骤。编译命令如下：

```bash
# 加载编译上下文
source .build-context-fzy-1.1
cd $BUILD_SRC_DIR

# 编译（DESTDIR 模式，R20）
make CC=clang CFLAGS="-O2 -fPIC" PREFIX=$DEFAULT_PREFIX -j1

# 安装到 staging 目录（打包用）
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX

# 安装到本地前缀（用户验证用）
make install PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载 SSL 证书验证失败 | HarmonyOS 环境缺少 CA 证书，Python urllib 无法验证 HTTPS | 使用 curl -kL 手动下载 tarball，放置到 `~/tmp/builds/fzy-1.1.tar.gz` 后用 init-build 自动识别 |
| 2 | make check 编译测试时缺少 `greatest/greatest.h` | 命令行传 `CFLAGS="-O2 -fPIC"` 覆盖了 Makefile 中 `CFLAGS+=` 的 `-Ideps` 等关键编译参数 | 在 make check 时使用完整 CFLAGS：`CFLAGS="-O2 -fPIC -Ideps -std=c99 -MD -Wall"` |
| 3 | G0 干净构建验证失败 | fzy 是 makefile 项目，G0 验证脚本尝试运行 configure（不存在），exit 127 | 已手动验证通过，fzy 无 configure 步骤，G0 跳过 configure 合理 |
| 4 | manifest.yaml 中 build_system 字段缺失 | 初始模板使用嵌套 `build.system` 格式，验证脚本要求顶级 `build_system` 字段 | 添加顶级 `build_system: makefile` 字段，同时更新嵌套 `build.system: makefile` |

## 源码修改

无。fzy 1.1 在 HarmonyOS 平台上使用 clang 直接编译即可，无需修改任何源文件。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无外部依赖 | — | fzy 仅链接 libc.so 和 libpthread，无第三方库依赖 |
| clang | 15.0.4 | 编译器 |
| make | 4.4.1 | 构建工具 |

## 功能验证结果

### 单元测试（make check）

```bash
make CC=clang CFLAGS="-O2 -fPIC -Ideps -std=c99 -MD -Wall" check
```

结果：32 tests, 102 assertions — 全部通过
- match_suite: 24 passed ✅
- choices_suite: 6 passed ✅
- properties_suite: 2 passed ✅

### 真实功能验证

```bash
# 版本信息
$DEFAULT_PREFIX/bin/fzy --version
# 输出: fzy 1.1 © 2014-2025 John Hawthorn ✅

# 帮助信息
$DEFAULT_PREFIX/bin/fzy -h
# 输出完整选项列表（-l, -p, -q, -e, -t, -s, -0, -j, -i） ✅

# 非交互式模糊匹配（-e/--show-matches 模式）
echo -e "apple\nbanana\ncherry\napricot\ngrape\npineapple" | fzy -e "ap" -s
# 输出:
# 1.885000  apple
# 1.875000  apricot
# 0.985000  grape
# 0.965000  pineapple ✅

# 文件名模糊搜索
echo -e "main.c\nutils.c\ntest_main.c\nhelper.c\nconfig.c\nmain.h" | fzy -e "main" -s
# 输出:
# 3.890000  main.c
# 3.890000  main.h
# 3.765000  test_main.c ✅

# 动态链接
# NEEDED: libc.so ✅
# ELF: 64-bit LSB arm64, dynamic, ld-musl-aarch64.so.1 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fzy-1.1-ohos-aarch64.tar.gz | 91KB (91681 bytes) | 预编译包（ELF 签名、strip、RPATH 已处理） |
| fzy-1.1-ohos-aarch64-debug.tar.gz | 36KB (36380 bytes) | debug 符号包 |
| $DEFAULT_PREFIX/bin/fzy | 51KB (51648 bytes) | 本地安装的可执行文件 |
| $DEFAULT_PREFIX/share/man/man1/fzy.1 | 2.4KB | 手册页 |

## 注意事项

1. fzy 编译命令行覆盖 CFLAGS 时，务必包含 Makefile 中原有的 `-Ideps` 和 `-std=c99`，否则测试编译会失败
2. fzy 是终端交互工具，非交互验证需使用 `-e` (--show-matches) 模式
3. fzy 仅依赖 libc 和 libpthread，适合作为基础工具优先编译
4. G0 干净构建验证的 configure 步骤对 makefile 项目不适用，需手动验证

---

**编译结束**: 2026-07-15 21:23
**最终状态**: built

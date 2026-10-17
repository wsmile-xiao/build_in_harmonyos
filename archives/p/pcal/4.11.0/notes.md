# pcal 4.11.0 适配笔记

## 编译环境

- 构建系统: makefile
- 编译日期: 2026-09-04
- 编译器: clang
- 状态: built

## 编译步骤

1. 通过官方脚本初始化源码和档案目录:

   ```bash
   python3 scripts/ohc-run.py init-build --auto \
     --url "https://downloads.sourceforge.net/project/pcal/pcal/pcal-4.11.0/pcal-4.11.0.tgz" \
     --tar tar.gz pcal 4.11.0
   ```

2. 执行语言预检:

   ```bash
   python3 scripts/ohc-run.py lang-preflight pcal 4.11.0 --src "$BUILD_SRC_DIR" --lang cpp
   ```

   预检结果为 `task=cpp, detected=c`，按官方 C/C++ 同族兼容规则继续适配。

3. 使用 clang 覆盖上游 Makefile 的 `/usr/bin/gcc` 默认值:

   ```bash
   make -j1 CC=clang CFLAGS="-fPIC -O2 -Wall -W" PACK=:
   ```

4. Conan recipe 不执行上游 `make install`，而是在 `package()` 中复制:

   - `exec/pcal` 到 `bin/pcal`
   - `doc/pcal.man` 到 `share/man/man1/pcal.1`
   - `doc/ReadMe.txt` 到 `share/doc/pcal/ReadMe.txt`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 `make` 会调用 `/usr/bin/gcc` | 上游 Makefile 为 Unix 分支硬编码 `CC=/usr/bin/gcc` | recipe 显式传入 `CC=clang` |
| 2 | `make -j2` 报 `jobserver mkfifo ... Operation not permitted` | 当前 OHOS 用户目录不允许 GNU make 在 `$TMPDIR` 中创建 jobserver FIFO | recipe 固定 `make -j1` |
| 3 | `make install` 依赖 `nroff/groff/compress` | 上游安装目标会生成并压缩 man/cat 文档 | recipe 手动打包二进制和已有 man 源文件，避免可选文档链 |

## 源码修改

无源码补丁。

## 依赖版本

无外部 Conan 依赖。

## 验证结果

```bash
$ pcal -v
pcal v4.11.0 - generate PostScript calendars

$ pcal -e 9 2026
%!PS-Adobe-1.0
%%Title: calendar for 09/2026

$ pcal -H -e 9 2026
<html>
...
September 2026

$ pcal -c 9 2026
opt -A
```

## 注意事项

- pcal 是命令行工具，软件级目录必须保留 `commands.json`。
- 该任务在大小写不敏感的 OHOS 用户目录中开发时，需要 sparse checkout 排除仓库中已有的 `libXext/libxext` 顶层大小写冲突文件，否则干净 checkout 会显示无关 diff。
---

**编译结束**: 2026-09-05 12:19
**最终状态**: built

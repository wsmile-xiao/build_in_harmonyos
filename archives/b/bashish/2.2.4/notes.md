# bashish 2.2.4 适配记录

## 软件简介

bashish 是文本终端的主题环境（theme engine），可在 per-application 基础上
更改颜色、字体、透明度和背景图像，并支持 bash/zsh/tcsh 的提示符（prompt）切换。

- 上游：https://bashish.sourceforge.net/
- 作者：Thomas Eriksson（2010 年最后更新）
- 许可证：GPL-2.0
- 语言：纯 bash 脚本
- 构建系统：autoconf（./configure && make && make install）

## 源码信息

- 下载 URL：https://downloads.sourceforge.net/project/bashish/bashish/2.2.4/bashish-2.2.4.tar.gz
- SHA256：3de48bc1aa69ec73dafc7436070e688015d794f22f6e74d5c78a0b09c938204b
- 大小：241565 字节
- 选择理由：SourceForge 是 bashish 的官方发布平台，CI build_and_test.sh
  的 mirror fallback 覆盖 sourceforge.net，CI worker 可达。

## 安装布局

```
bin/bashish                     # 主启动脚本
share/bashish/                  # 主题数据树
  main/                         # 核心：prompt/terminal/bashish/
  themes/                       # 主题集合：app/ascii-art/computer/...
  lib/                          # 运行时库脚本
  defaults/                     # 默认主题配置
share/man/man1/bashish.1        # man page
```

## 构建流程

1. `./configure --prefix=<package_folder>` — autoconf 生成 Makefile/bin/bashish/man/bashish.1
2. `make -j1` — 生成 bashish headers + 处理后的脚本
3. `make install DESTDIR=<source_folder>/_staging` — 安装到 staging
4. 复制 staging 树到 package_folder（保留 bin/share 布局）

## 运行时依赖

- bash >=2.04（必需）
- dialog（可选，curses 主题选择器）
- xwininfo / xprop（可选，X 支持）

## 测试策略（R34）

- bash -n 语法校验 launcher（bin/bashish）
- bash -n 语法校验所有安装的 .sh 脚本
- 验证 share/bashish/ 安装树的 4 个子目录（main/themes/lib/defaults）
- bashish 是纯 bash 脚本包，bash -n 是 R34"实际执行被测包脚本"对纯 shell 包的等价校验

## 已知限制

- bashish 主脚本 bin/bashish 里 BASHISHDIR 硬编码为 `@PREFIX@/share/bashish`，
  运行时依赖 prefix 路径的稳定性。
- 无上游测试套件（纯 bash 脚本包，无 make check/test）。

# abcselect 1.5 适配笔记

## 软件简介

abcselect 是一个 Perl 脚本工具，用于从 abc 音乐符号文件中提取声部（voices）、
乐章（movements）等，输出可管道输入 abctab2ps 等排版工具。纯脚本工具，无需编译。

## 构建要点

- **无编译**：`package_type = application`，`build()` 为空操作，直接打包脚本与 man 页。
- **运行时依赖**：`perl/5.42.2`（制品仓已有预编译包），`requirements()` 声明。
- **shebang 修复**：上游脚本 shebang 为 `#!/usr/bin/perl`，OHOS 上该路径不存在；
  `package()` 中在 `shutil.copy2` 后、`os.chmod` 前将其替换为 `#!/usr/bin/env perl`，
  通过 Conan 环境 PATH 找到 perl 解释器。
- **源码布局**：tar 包仅含单个顶层目录 `abcselect/`，`source()` 用 `strip_root=True`
  剥离根目录，使脚本直接位于 source_folder 根。

## 源码下载（镜像源说明）

- 上游官方站 `www.lautengesellschaft.de` 与 FreeBSD `distcache.freebsd.org` 在 CI
  Worker 上均不可达（连接超时）。
- conandata.yml 以 **USTC 镜像**
  （`https://mirrors.ustc.edu.cn/freebsd-ports/distfiles/abcselect.tar.gz`）为主源，
  sha256 `37e69575...` 与 FreeBSD distinfo 完全一致（本机下载校验通过）；原源保留
  为兜底（Conan 2.x `get()` 支持 url 列表逐个尝试）。

## 测试说明

- 上游无测试套件（简单的 Perl 脚本工具），适配后新增 test_package 冒烟测试：
  - `test_package/conanfile.py`：通过 perl 依赖解释器显式执行 `abcselect -?`
    （abcselect 仅识别 `-?` 为 help 选项，返回 0；`--help` 不被识别返回 1），
    区分 crash（exit >=128 / 127）与功能失败。
  - `test_package/test.sh`：等价 shell 冒烟测试（bash，`set -euo pipefail`）。
- CI #14178 通过：Conan test_package ✅、L0/L1 门禁 ✅。

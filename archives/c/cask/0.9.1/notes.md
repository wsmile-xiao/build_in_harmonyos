# cask 0.9.1 — 适配笔记

## 软件信息

- **名称**: cask
- **版本**: 0.9.1
- **描述**: Emacs dependency management tool
- **许可证**: GPL-3.0-or-later
- **源码**: https://github.com/cask/cask/archive/refs/tags/v0.9.1.tar.gz
- **SHA256**: 755e71b7291678787afd497e34724004459add3e438d367e83891080f6d545a3
- **构建系统**: script (无编译，bash脚本安装)

## 构建特征

cask 是一个 Emacs Lisp 项目管理工具，不是传统的 C/Go 项目。它不需要编译：
- `bin/cask` 是 bash 脚本，作为主入口点
- `cask.el`, `cask-cli.el`, `cask-bootstrap.el` 是 Emacs Lisp 源码
- `package-build/` 目录包含依赖管理工具

安装方式参考 Homebrew formula：
1. `bin.install "bin/cask"` — 安装 bash 脚本到 bin/
2. `prefix.install Dir["*.el"]` — 安装 .el 文件到 prefix 根目录
3. `prefix.install "package-build"` — 安装 package-build 目录
4. `elisp.install_symlink` — 创建 emacs site-lisp 符号链接
5. `touch prefix/.no-upgrade` — 禁止 cask 自升级

## 适配过程

### 下载
- GitHub SSL 证书问题：使用 `curl -k` 手动下载
- SHA256 校验通过：755e71b7291678787afd497e34724004459add3e438d367e83891080f6d545a3

### 安装
- DESTDIR 模式：手动安装文件到 `$TEST_PREFIX/$DEFAULT_PREFIX/`
- 本地安装：手动安装到 `$DEFAULT_PREFIX/`（~/usr/local）
- .el 文件必须放在 prefix 根目录（而非 share/emacs/site-lisp/），因为 `bin/cask` 通过 `readlink -f` 解析 `SRCDIR=$(dirname $(dirname $(readlink -f $0)))` 来定位 .el 文件

### 打包特殊处理
- 标准 package 流程只打包顶层目录（bin/, lib/, share/），不包含根目录下的 .el 文件
- 手动修复：重建 tar.gz 包含所有顶层文件和目录（cask.el, cask-cli.el, cask-bootstrap.el, .no-upgrade, COPYING）

### 依赖
- 运行时依赖：emacs（Emacs 编辑器）、coreutils（GNU readlink/greadlink）
- cask 脚本使用 `readlink -f` / `greadlink -f` 解析路径，系统 `/usr/bin/readlink` 已可用

### 测试
- bash 语法检查通过
- 路径解析验证通过（SRCDIR 正确指向 prefix）
- emacs 不在系统中，cask 运行时命令需要 emacs（预期行为，运行时依赖）

## 无补丁

cask 是纯脚本/Emacs Lisp 项目，无需源码修改，无补丁文件。

---

**编译结束**: 2026-06-01
**最终状态**: published

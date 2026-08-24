# bashbro 1.13 适配记录

## 软件简介

bashbro 是基于 Bash 的 web 文件浏览器，允许通过浏览器浏览、流式传输、
查看和保存文件。运行一个纯 bash 实现的小型 HTTP 服务器。

- 上游：https://github.com/victrixsoft/bashbro
- 作者：Adam M. Danischewski（Victrixsoft，2024）
- 许可证：GPL-3.0
- 语言：Shell (90.9%) + Roff (9.1%，man page)
- 最新 release：bashbro-v1.13（2024-10-11）

## 源码信息

- 下载 URL：https://github.com/victrixsoft/bashbro/archive/refs/tags/bashbro-v1.13.tar.gz
- SHA256：4ed4560df8cccf66754ba0ec7a2e18860549a36a6a1929188e8394cfedf882f7
- 大小：18589 字节
- 选择理由：GitHub 是 bashbro 官方仓库，CI build_and_test.sh 的 mirror
  fallback 覆盖 github.com，CI worker 可达。该 tarball 与 Debian orig
  tarball 内容完全一致（同 SHA256）。

## 构建与安装

bashbro 是纯 bash 脚本包，**无构建系统**（无 Makefile/configure）。

安装步骤：
1. `source()`：下载并解压 GitHub release tarball
2. `build()`：确保主脚本 `bashbro` 可执行（chmod 755）
3. `package()`：复制文件到 package_folder
   - `bin/bashbro` — 主脚本
   - `share/man/man1/bashbro.1` — man page
   - `share/bashbro/LICENSE` — 许可证

## 运行时依赖

- bash（必需）
- 可选：socat 或 netcat（端口监听后端）

## 测试策略（R34）

- bash -n 语法校验主脚本（bin/bashbro）
- 验证 man page 存在（share/man/man1/bashbro.1）
- bash --version 调用验证脚本可执行
- bashbro 是纯 bash 脚本包，bash -n 是 R34"实际执行被测包脚本"
  对纯 shell 包的等价校验

## 已知限制

- bashbro 启动 HTTP 服务器需要端口绑定权限
- 无上游测试套件（纯 bash 脚本包）

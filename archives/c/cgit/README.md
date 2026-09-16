# cgit

Hyperfast web frontend for git repositories written in C. It is a CGI program
that renders git repositories as web pages with built-in caching.

## 功能概述

- 仓库索引、summary、log、tree、commit、diff、patch、snapshot 页面
- 快照下载 (tar.gz/tar.bz2/tar.xz/zip)
- `cgitrc` 运行时配置与仓库列表
- 14 个上游 shell 测试套件 (tests/t*.sh)

## OHOS 适配

- 构建系统为纯 Makefile, 非 autotools/cmake. 必须先把 git 2.51.0 源码放入
  `git/` 子目录, 再执行 `make GIT_VER=2.51.0 NO_LUA=1 -j1`.
- 使用 `NO_LUA=1` 关闭 Lua 过滤器支持, 只保留 exec 过滤器, 避免引入 LuaJIT/Lua 依赖.
- 依赖来自 Conan 制品仓: `openssl/3.5.6.1` 与 `zlib/1.3.1.1`, 通过 CFLAGS/LDFLAGS 注入.
- 编译器从 Conan conf 获取 (`tools.build:compiler_executables`), 不裸用 shell 的 CC 变量 (R33).
- 产物为 CGI 可执行文件 `bin/cgit` 与 `share/cgit/` 下的 css/png/ico/txt 及 filters, 无库文件.
- 上游 `t0010-validate-html.sh` 需要 `tidy`, OHOS 真机缺失时计为跳过并在 PR 补充说明中披露.

## 依赖关系

- 编译依赖: openssl/3.5.6.1, zlib/1.3.1.1
- 构建时源码依赖: git 2.51.0 (cdn.kernel.org, 随配方一起下载到 git/ 子目录, 非 Conan requires)
- 运行依赖: git 二进制 (用于创建/读取仓库), 任意 CGI 兼容的 HTTP 服务器

## 参考资料

- 官网: https://git.zx2c4.com/cgit/about/
- 源码: https://git.zx2c4.com/cgit
- GitHub 镜像: https://github.com/zx2c4/cgit
- Debian 快照版本说明: 1.2.3+git20250818.80.3346409+git2.51.0

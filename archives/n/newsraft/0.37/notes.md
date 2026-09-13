# newsraft 0.37 适配笔记

## 来源与校验

上游使用 Codeberg 的 `newsraft-0.37` tag，官方 tarball 为：
`https://codeberg.org/newsraft/newsraft/archive/newsraft-0.37.tar.gz`

sha256 为 `725fdbf4c14d87eb7e926aebd9b116f540dca812bea02e73078070156d986ad4`，已与 FreeBSD ports distinfo 和 Homebrew formula 双源核对一致。

## 构建

上游是纯 POSIX makefile，核心变量可覆盖：CC、CFLAGS、AUXCFLAGS、LDFLAGS、PREFIX 和 DESTDIR。源码将各 C 文件包含进 `src/newsraft.c`，最终生成 `newsraft`。

配方从 `tools.build:compiler_executables` 获取 OHOS clang，并从 Conan 依赖对象显式拼接 include/lib 路径。上游 makefile 的 pkg-config 探测被 AUXCFLAGS 覆盖；PKG_CONFIG_LIBDIR 和 PKG_CONFIG_PATH 指向空目录，使链接采用上游 fallback 库名并使用 Conan 注入的 -L 路径。

## 依赖与平台判断

0.37 不含 stfl，也不含 ncurses。TUI 由 `src/termbox2.h` 提供，是 header-only POSIX 实现。依赖为 libcurl/8.5.0、expat/2.8.2.1.1、sqlite3/3.53.4 和 gumbo-parser/0.10.1，均已完成制品仓 recipe 预检。

## 补丁

`0001-run-check-sh.patch` 是 per-file portability 补丁：让 `tests/run-check.sh` 的两个内部 make 调用显式传递 AUXCFLAGS/LDFLAGS，确保 `make check` 在 Conan/ OHOS 环境能够找到依赖头文件和库。补丁基于 tar 解压 `.orig` 树生成，并已通过 `git apply --check` 与应用后树差异校验。

## 测试

上游 `make check` 包含 16 个纯函数测试，适合无头执行。消费者 test_package 执行 `newsraft -v`（合并 stderr，断言包含 0.37 且 rc=0）和 `newsraft -h`（rc=0）。运行前设置 `LC_ALL=C.UTF-8` 和 `LANG=C.UTF-8`，因为主程序在解析参数前会验证 locale。

TUI 交互本身不在无头环境测试；版本和帮助路径均在 termbox 初始化前退出，可证明主程序启动、链接和参数退出路径。

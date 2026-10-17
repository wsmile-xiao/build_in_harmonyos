# protomol

ProtoMol 是一个面向分子动力学（MD）的面向对象框架，用于快速原型化新的 MD 算法。
它由 Autoconf 2.57 / Automake 1.6 时代的 autotools 构建，上游发布包为
`protomol-2.0.3-tar.gz`（注意 `tar` 前是连字符而非点）。

`2.0.3` 配方不需要任何 Conan 依赖：FFT 使用内置 ZFFT，GLUT/X11 与 libpng 均关闭。
上游框架库全部是 `noinst_LIBRARIES`，`make install` 只产出 `bin/` 下的 6 个可执行文件，
因此这一包是纯可执行包（`package_type: application`，配软件级 `commands.json`）。

适配要点（详见 `2.0.3/notes.md`）：11 个补丁处理 clang 两阶段名字查找、libc++ 迭代器/流重载
差异、OHOS 用户态 toybox `sed` 丢弃含非法 UTF-8 行导致的 `PACKAGE_CITE` 未定义，
以及 `configure`/`config.status` 临时目录 `umask 077`→`022`（CI worker 的 HMDFS 上
0700 目录不可写，会让 configure 以 exit 2 失败）。

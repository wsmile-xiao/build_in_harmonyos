# sproxy — OpenHarmony 编译档案

## 软件简介
sproxy（[S][proxy]）是 JoeDog 出品、配合 Siege 回归测试器使用的 HTTP 代理：监听
（默认 9001）浏览器的 HTTP 请求并原样转发，同时把请求的 URL（含 GET 参数与 POST
数据）写成 Siege `urls.txt` 格式的文件。上游为一个纯 Perl 脚本加自带的纯 Perl
模块 JoeDog::Config，许可证 GPL-2.0-or-later。

## OHOS 适配要点
- 纯 Perl 包，无 C/C++ 编译；上游 configure/Makefile 仅做 `%_VAR%` 的 sed 替换与
  文件拷贝，配方在 `build()` 以 Python 等价实现，**无需 autoconf/automake/libtool**
- 上游 configure 用 `$PERL utils/modtest` 探测 perl 模块，交叉构建时无法在构建机
  执行目标 perl，因此不走 configure；自带的 JoeDog::Config 直接从上游 tarball 取出
  安装到 `lib/sproxy/JoeDog/Config.pm`（脚本用 `FindBin/../lib/sproxy` 定位）
- shebang 重写为 perl 依赖包的绝对路径（OHOS 无 `/usr/bin/perl`，禁 `env perl`）
- 默认配置 `etc/sproxy.conf`、手册 `share/man/man1/sproxy.1`

## 依赖关系
- 运行时: perl/5.42.2.3（仓库已适配）；perl 不带 libwww-perl 栈，包自包含：上游自带
  libwww-perl 5.76（纯 Perl）+ CPAN URI 5.35 装到 lib/sproxy/；sproxy.in 插入 `parse_head(0)`
  以免依赖 HTML::Parser(XS)
- 被依赖: 无

## 参考资料
- [Sproxy (JoeDog)](https://www.joedog.org/)
- 源码: https://download.joedog.org/sproxy/sproxy-1.02.tar.gz

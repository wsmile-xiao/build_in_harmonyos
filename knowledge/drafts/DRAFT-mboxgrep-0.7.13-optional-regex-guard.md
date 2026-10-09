# mboxgrep 0.7.13：关闭 PCRE2 后的悬空条件语句

状态：路径 B 知识库扩展草稿，是否接纳为独立知识条目由维护者评定。现有 `DRAFT-proxsmtp-1.10-capability-split` 解释不同可选能力的探针边界；本条关注的是关闭可选库后，源码条件语句本身失效，导致基础能力被错误阻断。

## 现象和根因

在 HarmonyOS PC AArch64 上，官方发布包使用 `--without-pcre2 --without-z` 原样编译返回 0，`mboxgrep --version` 也正常。然而 `mboxgrep -E -c foo` 退出 2，提示 `Support for Perl regular expressions not compiled in`。扩展 POSIX 正则 `-E` 不应依赖 PCRE2。

`src/misc.c::set_option_regextype` 在 `#ifndef HAVE_LIBPCRE2` 中写成 `if (regextype == REGEX_PERL);`。末尾分号结束了条件语句，后面的花括号是无条件代码块，任何显式正则模式都会报错。Clang 的 `-Wempty-body` 提示可用于定位，但编译成功并不能证明行为正确。

## 最小修复及验证

仅删除该分号，保留 `REGEX_PERL` 判断和错误文案，不启用缺失的 PCRE2。最终安装包的消费者测试从两封临时 mbox 邮件核对版本、默认 POSIX 匹配计数、`-E` 扩展正则、`-H` 仅头部匹配，并确认 `-P` 仍以退出码 2 拒绝。上游发布包没有自动化测试入口，不能宣称“上游测试通过”；新增 1 项消费者场景含 5 个断言。

源码：官方 0.7.13 发布包 SHA-256 `be2c9d65bbdaa97a860313e394938cf4bdcbca6e5f84d5fb98434ec38b8d65b4`。真机隔离 Conan `create-v2.log` SHA-256 `a10f160ea974a010c1ad1d6bab5b117c2bbe2e52ac128a84d9bfb6e24542f477`，目录 `/data/storage/el2/base/haps/entry/files/mboxgrep-conan-0.7.13-20260929T125256`，消费者输出 `PASS: installed mboxgrep 0.7.13, POSIX patterns and PCRE2 boundary`。该次验证副本仅将源码 URL 改为同哈希本地 `file://` 归档，以绕过目标机 Conan 的 GitHub 连接超时；提交配方仍使用官方 HTTPS，CI 下载与构建须独立核验。

可复用原则：测试可选依赖被禁用后的基础路径和应拒绝路径，不只测试配置与编译；当编译器报告空 `if`、悬空分号时，把它当作潜在运行时控制流错误核实。

# ondir 0.2.4 适配笔记

任务 5735（activity=-依赖）。上游 OnDir（Alec Thomas），进入/离开目录时自动
执行目录专属脚本的 shell 钩子工具，产物为 CLI `ondir`。

## 上游形态

- 发布渠道：作者站点 `https://swapoff.org/files/ondir/ondir-0.2.4.tar.gz`。
  GitHub 镜像 `alecthomas/ondir` **无 tag 且 2014 年后停更**，不可作源码锚点；
  sha256 `52921cdc…0bda343a` 与 Homebrew homebrew-core `Formula/o/ondir.rb`
  声明值逐字符一致（双源交叉核验）。
- 构建系统：**上游手写 Makefile（非 autotools）**，无 configure / config.h /
  codegen；两个编译单元 `conf.c` + `ondir.c`。
- 依赖：仅 POSIX libc —— `regex.h`（musl 提供）、`limits.h` 的 `PATH_MAX`。
- 上游 Makefile 的 `CFLAGS` 连写两行，**后者生效**：
  `-Wall -c -g -DVERSION -DGLOBAL_CONF`。`USE_ONENTERLEAVE` 默认关（上游源码
  注释标注 "not recommended at all"），本配方保持默认。
- 语义注意：`ondir <old> [new]` 只把 enter/leave 规则命中的 shell 命令
  **打印到 stdout**，由 shell 钩子 eval；ondir 自身不执行命令。功能断言因此
  校验 stdout 文本，而非副作用。
- 上游**无测试套件**（无 `tests/`、无 check 目标）。

## OHOS 适配要点

1. 编译器从 `tools.build:compiler_executables` 取（CI 上 `$CC` 为空），`make`
   时**同时覆盖 `CC` 与 `LD`**：上游 `LD` 与 `CC` 分离且默认裸 `cc`，只覆盖
   `CC` 会让链接步在 CI 上 Error 127（CI #44149）。
2. `GLOBAL_CONF` 编译期固化为 `/etc/ondirrc`（上游默认）。HMFS 上 `/etc`
   只读，测试**经 `HOME` 隔离**写 `~/.ondirrc`，不触碰全局配置。
3. `/tmp` 只读：test_package 的 here-doc 需重定向 `TMPDIR`。
4. 层1 上游测试：上游无套件 → `build()` 内 smoke（`./ondir -V` 输出版本号）。
   功能性 enter/leave 正则规则测试在 `test_package` 以断言补齐
   （见 `test_package/MANIFEST.yml`）；另含 2 条鸿蒙特有断言（rule12）。
5. 目录级 `archives/o/ondir/commands.json` 登记 0.2.4（L0k/R38）；该文件在
   main 上已有 0.2.3 条目，本 PR 以追加方式合入，不改动既有条目。

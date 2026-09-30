# regldg 1.0.1 适配笔记

任务：积分赛。上游 regldg（Patrick Cronin），正则表达式字典生成器：
读取正则表达式，输出所有匹配的文本字符串（word list / dictionary 生成）。
产物为单文件 CLI `regldg`（仅依赖 libc/libm，零三方依赖）。

## 上游形态

- 版本锚点：`github.com/PatrickCronin/regldg` release `v1.0.1`
  （2022-06-20，唯一 release）。tarball
  `https://github.com/PatrickCronin/regldg/releases/download/v1.0.1/regldg-1.0.1.tar.gz`
  sha256 `f5f401c6…501335dc99` 与 Homebrew homebrew-core
  `Formula/r/regldg.rb` 声明值逐字符一致（双源交叉核验，另经本机实下验证）。
- 构建形态为**裸 Makefile**（非 autotools / 非 cmake）：仅 `all`
  （编译 17 个 .o 并链接为 `regldg`）与 `clean` 两个目标；无 configure、
  无 install、无 check/test 目标。上游 README 原话："Compile: make /
  Install: Don't; just run from here!"。Homebrew 侧以 `bin.install "regldg"`
  完成安装，本配方 package() 等价处理（`bin/regldg` + `licenses/LICENSE`）。
- 上游编译变量写死：`COMPILE=cc -O3 -Wall -g -c` / `LINK=gcc -O3 -Wall -g -lm`。
- 上游测试：**无**。源码树无 tests/ 或 test/ 目录、无 *test* 测试架文件；
  Makefile 无 check/test/TESTS 目标；Homebrew `test do` 块仅为单条 smoke
  （`regldg test`）。详见 `test_package/MANIFEST.yml` 审计结论
  （`upstream_tests_exist: false`，`upstream_test_total: 0`）。
- CLI 用法：`regldg [options] regex`（`-n/--num-words-output` 限输出词数、
  `-p/--parse-only` 仅解析、`-f/--file` 从文件读正则等）。有限语言直接
  输出全部词（如 `regldg test` 输出单个词 `test`），无限语言需 `-n` 限界。

## OHOS 适配要点

1. R33：编译器从 `tools.build:compiler_executables` 取（CI 上 `$CC` 为空）；
   以 make 命令行变量覆盖上游写死的 `COMPILE`/`LINK`
   （make 命令行变量优先级高于 Makefile 内定义），`-j1`（R9）。
2. patches/0001：新版 Clang 对上游旧式 int 转换写法告警，COMPILE 追加
   `-Wno-int-conversion`。**逐字复用 Homebrew DATA 补丁**（发行版级验证），
   非自研；build() 命令行同样携带该标志，双保险。
3. R26 不适用：单文件 CLI，无 .so 产物，不存在系统同名库污染风险。
4. R38：命令行工具，在软件级目录新建 `commands.json`（type=tool，
   ref 对齐 regldg/1.0.1）。
5. R34：test_package 非空壳——`test_regldg.sh` 6 项真实断言：
   Homebrew 等价 smoke（输出精确匹配单个词）、分支输出（a/b 两行）、
   长选项路径、仅解析路径、反向对照（无参数必须失败退出，证明 harness
   能抓到失败）、鸿蒙形态（输出落盘 HMFS 可写目录非空）。脚本刻意只用
   `set -u` 不用 `set -e`，保证任何单项失败后仍执行并打印 RESULT 尾行
   （真机门禁解析该行计数）。
6. 机器 evidence（`HMBS_TEST_PACKAGE_RESULT` / `HMBS_UPSTREAM_TEST_RESULT`
   双标记）由 test_package/conanfile.py 在真机实测后发出，计数取自脚本
   RESULT 尾行正则解析，无算术修补、无猜测修正分支。

## 待 HMBS 真机预检

- 本轮仅完成未提交工作树；`conan create` 编译 + test_package 6 项断言 +
  双标记 evidence 待 HMBS 后台真机验证后回填 PR 正文通过率。
- 若真机 clang 对某源文件另有告警/错误，下一轮按真机日志修复。

---

**编写日期**: 2026-09-30
**最终状态**: 待真机预检（工作树未提交）

# tintin 2.02.61 适配笔记

## 构建

- 构建系统：GNU Autoconf（configure.in + Makefile.in，tarball 内含 autoconf 2.72 生成的 configure，无需 autoreconf）
- configure/Makefile 位于 `src/` 子目录；产物为单一二进制 `tt++`
- 依赖：zlib（必需，MCCP 压缩）、pcre2（必需，正则）；gnutls（TLS）为可选，configure 缺失时仅 WARN 并优雅降级，本适配不引入
- tarball 自带 config.sub / config.guess（2025-07-10），原生支持 `linux-ohos` 三元组，无需 dnsperf 式三元组补丁

## 补丁说明

`patches/0001-use-tmpdir-for-configure.patch`（portability）：

- autoconf 2.72 在 configure 内创建临时目录的片段为 `umask 077 && mktemp -d "./confXXXXXX"`
- HarmonyOS 设备 HMDFS 上该写法与 E081（HMDFS tmpdir umask）冲突
- 改为 `${TMPDIR:-.}/confXXXXXX` + umask 022（与基线 dnsperf 0002 补丁同一模式）

`patches/0002-class-save-memstream-fallback.patch`（portability，无平台宏）：

- OHOS libc 的 `open_memstream` 已损坏：写入被丢弃、缓冲区从不分配
  （`#class save` 得到长度 0），退出时 free 崩溃（SIGTRAP）；`fopencookie`
  同样段错误；`fmemopen` 在有效缓冲区下工作正常（已用探针程序逐项实测）
- 特性探测：configure.in 的 AC_CHECK_FUNCS 增加 open_memstream 探测
  （configure / config.h.in 同步补丁），生成 `HAVE_OPEN_MEMSTREAM` 宏
- 但"符号存在"不等于"实现可用"（OHOS 正是存在但损坏），因此 class_save
  在 open_memstream 写入后做**运行时校验**（长度非零 + 首字节为命令字符），
  校验失败（或无该宏）时回退到 `mkstemp`（尊重 TMPDIR，HarmonyOS 的
  /tmp 只读）+ `fdopen("w+")` 写入并读回 `node->data`，与 fmemopen
  读取端（class_load，正常）配对
- 修复后上游 validate 第 6/23 组（#class save/load）通过

## HMDFS 适配

- 不使用 Conan Autotools helper：`self.run()`/`env="conanbuild"` 的 shell wrapper 会触发 profile CONFIG_SHELL（bash）在 HMDFS 深路径下的 getcwd 缺陷
- build() 将源码复制到 `tempfile.mkdtemp`（优先 TMPDIR）下的独立构建目录，用 `/bin/sh` 脚本完成 configure + make -j1 + make install DESTDIR
- CC 取自 conan conf `tools.build:compiler_executables`（profile 注入），未设置时抛 ConanException，不硬编码任何路径
- 原生 OHOS 环境无法运行 config.guess（HMDFS 只读 tmp），显式传 `--build=--host=<gnu_triplet>`

## 上游测试

- 上游无正式测试框架；上游仓库（master）与 2.02.61 release 均无 test 目录、
  无 CI workflow，`src/validate` 是唯一测试产物
- validate 含 **113 个 error 断言点**（112 个独立编号），全部实跑：
  输出 `End of validation with 0 errors` = 113/113 通过
- 以 `tt++ -H -G validate` 运行；`-H`（nohup）必需：无 TTY 的 CI 环境下
  终端初始化 tcsetattr 会致命退出，-H 跳过终端初始化
- 通过判据：输出 `End of validation with 0 errors`（脚本错误计数机制，
  退出码恒为 0，故必须 grep 输出）
- `tt++ -V` 按上游行为打印版本后 exit(1)（main.c -V 分支），断言只校验输出内容
- test_package 原样拷贝 validate（未修改上游测试），追加 `-V` 版本断言与
  负向断言（`-l bogus` 必须 exit 1 并输出用法提示），共 6 断言（4 正向 + 2 负向）
- 上游脚本自身分组标记缺陷：`)=-=( ERROR N )=-=(` 标记共 38 处、独立编号 36 个
  （编号 23 无独立标记、19 与 30 各重复一次），仅用于分组注释，
  不影响 113 个 error 断言点的统计
- tt++ 启动时会创建 `$HOME/.tintin`，test 脚本将 HOME 指向 TMPDIR 下临时目录，不污染 CI 家目录

## 编译细节

- Makefile 编译规则只用 `$(CFLAGS)`（`INCS=@MYINCLUDE@` 因 includedir 取默认值而为空），
  依赖 include 路径必须同时进 CFLAGS；CPPFLAGS 仅对 configure 的 conftest 生效
  （首次构建曾因只设 CPPFLAGS 导致 `pcre2.h file not found`）

## 验证命令

```bash
cd /storage/Users/currentUser/build_in_harmonyos
export PATH="$HOME/.local/bin:$PATH"
PROFILE=ci/conan/profiles/ohos-aarch64
conan create archives/t/tintin/2.02.61 -pr:h=$PROFILE -pr:b=$PROFILE --build=missing
```

依赖发布复核（R36）：

```bash
conan download "zlib/1.3.2" --only-recipe
conan download "pcre2/10.45.1" --only-recipe
```

# rancid 3.14 - HarmonyOS 编译记录

## 概述

rancid（Really Awesome New Cisco confIg Differ）是一套网络设备配置版本控制工具，能够
自动登录各类设备抓取配置并以 RCS 版本库统一管理配置快照。核心组件为若干 perl 脚本
（clogin/alogin/jlogin/par 等）+ 少量 C 助手（par、hpuifilter），并附带 lg 等商用参考脚本。

**编译状态**: ✅ 成功（built）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel aarch64 |
| 编译器 | clang/clang++ 15 |
| C 库 | musl libc |
| 解释器 | perl >= 5（Socket.pm >= 2.006） |
| 三元组 | aarch64-unknown-linux-ohos |

## 编译步骤

```bash
# rancid release tarball 自带生成的 configure + Makefile.in，无需 autoreconf
./configure --prefix=/          # AutotoolsToolchain 注入 CC/CONFIG_SHELL；应用 3 个补丁
make -j1
make install DESTDIR=<package_folder>   # → {bin,etc,lib/rancid,share/rancid,share/man,var}
```

## 补丁说明

### 0001 - configure: expect/mktemp/ping 探测非致命化

rancid 的 configure 对三个纯运行时辅助工具（expect/mktemp/ping）做硬性
`AC_PATH_PROG` + `as_fn_error` 探测，任一缺失即整体中止。三者都不是编译所需
（expect 仅给 clogin/*login 登录脚本、mktemp 仅用于生成 etc/rancid.conf 的 PATH、
ping 仅用于 lg 网路状态 CGI）。补丁把三处 "not found" 分支改为 WARNING + 置空，
工具存在时行为与上游完全一致。

### 0002 - configure: HMFS getcwd 回退 $PWD

OHOS/HMFS 部分挂载点不实现 getcwd(3)（报 "getcwd: cannot access parent directories"），
configure 顶部 `ac_pwd=`pwd`` 输出为空直接以 "working directory cannot be determined"
中止。补丁把 ac_pwd 判定改为 `pwd` 失败时回退 `$PWD`（配方预置
`os.environ["PWD"]=source_folder`），仍保留 `test -n` + `ls -di` 一致性校验。

### 0003 - configure: config.status 临时目录 HMFS 修复

configure 末尾 config.status 在 cwd 用 `mktemp -d ./confXXXXXX`(umask 077) 建临时
目录写 subs1.awk；HMFS 对 0700/0770 临时目录不可写（报 Permission denied → could not
setup config files machinery）。补丁把 mktemp 改为 false 恒走 autoconf mkdir 回退，
并把该回退的 umask 077 放宽为 000（0777）。

### 安装包装器（package() 内联脚本）

configure 找到的 INSTALL 程序是 HMBS 运行时 install shim，只支持 GNU 参数面子集，
automake 的多文件 `-m 644 f1..fn dir/`（及 -d/-t）调用以 Error 64 (EX_USAGE) 拒绝。
package() 写一个只依赖 cp/mkdir/chmod 的确定性 POSIX 安装包装器（覆盖 -c/-m/-d/-t/-D、
单/多文件拷贝），经命令行 `INSTALL=<wrapper> -c` + `MKDIR_P=mkdir -p` 传给 make install。

## 已知问题

- rancid 是自包含 prefix 设计：脚本把 `@prefix@`（= `/`）焙进 `@INC`/路径
  （如 `push(@INC, "/lib/rancid")`），conan 安装到自身缓存目录后脚本直接运行会在
  系统根路径找模块。这是上游原生设计，非本次引入缺陷；consumer 测试用
  `PERL5LIB`/`-I` 指向包内 `lib/rancid` 校验模块可加载。
- 实际登录设备功能依赖 expect/async 等外部工具与网络设备，运行时按需安装，与编译无关。

## 验证结果

（本机非 conan 探索性验证；最终以 hmbs 真机 conan create 为准）
- 三补丁（0001/0002/0003）顺序套用后 `sh -n configure` 通过；`./configure --prefix=/tmp/rancid-prefix`
  退出码 0，config.status 全量生成各 Makefile/config.h/bin scripts，无 conf* 临时目录残留。
- 本机 make install 用安装包装器退出码 0，176 个文件全安装且无 0 字节
  （bin/lib/etc/share/man 就绪）。
- 上游 rancid 3.14 无任何自动化测试（no_tests），由 test_package 消费者视角验证
  （C 助手 EX_USAGE 64 + perl -c 语法 + rancid 模块加载）。

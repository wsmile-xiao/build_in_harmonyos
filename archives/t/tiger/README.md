# tiger

## 简介

Tiger 是一套 UNIX/Linux 安全审计与入侵检测工具集，最初由 Texas A&M University
开发（1994），后经 Advanced Research Corporation 与 Javier Fernández-Sanguino
维护。它由三部分组成：

- `tiger`：主程序，按 `tigerrc` 配置依次运行 `scripts/` 与 `systems/<OS>/` 下的
  检查脚本，产出安全报告；
- `tigexp`：把报告里的消息号（如 `init001e`）翻译成 `doc/*.txt` 中的说明正文；
- `tigercron`：面向 cron 的封装，负责去重与邮件通知。

另有一组用 C 写的小工具（`md5`、`snefru`、`getpermit`、`realpath`、`testsuid`），
供检查脚本做文件签名与权限比对。

- **官方网站**：<https://savannah.nongnu.org/projects/tiger/>
- **源码发布**：<https://download.savannah.nongnu.org/releases/tiger/>
- **License**：GPL-2.0-or-later

## 已适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.2.4 | built | 真机（HarmonyOS aarch64）`conan create` + test_package + L0–L5 全绿（L0/L1/L2/L4/L5 = pass，11/11 断言），尚未 `conan upload` |

> 3.2.4 系列上游只发布过 `tiger_3.2.4rc1.tar.gz`（Savannah 发布目录与 git 标签
> 均无最终 3.2.4），本目录的 `3.2.4` 即指向该官方发布物，详见
> `3.2.4/notes.md` 第 2 节。

## 构建方式（OHOS）

上游是 Autotools 变体：预生成的 `configure`（GNU Autoconf 2.69）+ 手写
`Makefile.in`，没有 automake/libtool/CMake/meson，也没有测试套件。
`Makefile` 不支持 VPATH，因此配方采用 in-source 构建。

```bash
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### OHOS 适配要点

1. **shebang（E165）**：`configure`、`Makefile.in` 与全部安装脚本都指向
   `/bin/sh`，OHOS 没有 `/bin`。配方在构建期探测本机可用解释器
   （`/system/bin/sh` 优先），改写 `configure` 首行、用 `SHELL=` 传给 make，
   并在 `package()` 阶段统一改写已安装脚本的解释器（含 `/usr/bin/perl` →
   实际 perl 路径）。
2. **LP64 摘要错误**：`c/md5.c`、`c/snefru.c` 把 32 位字长声明为
   `unsigned long int`，在 aarch64 上是 64 位，会静默算错摘要。
   补丁 `0001-use-32bit-hash-word-types.patch` 固定为 `uint32_t`。
3. **命令查找路径**：`tigexp`、`util/genmsgidx` 的 `findcmd()` 写死传统 FHS
   路径，OHOS 上会导致 `make`（生成 `doc/explain.idx`）与 `tigexp` 双双失败。
   补丁 `0002-find-posix-tools-in-system-bin.patch` 追加 `/system/bin`。
4. **HMDFS umask（E129）**：`configure`/`config.status` 的 `umask 077` 在
   HMDFS 上生成所有者都写不进去的目录，需放宽为 `022`。
5. **SHELL 覆盖**：profile 的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 在 CI
   shell 中不一定可执行，配方改用本机可用 POSIX shell。

## 依赖

- 构建期：无 Conan 依赖，仅需 C 编译器与 make（W0 结论，见 `3.2.4/notes.md` 第 4 节）。
- 运行期：POSIX shell + 常用工具（awk/sed/grep/ls/...）、以及执行检查脚本所需的
  系统数据（`/etc/passwd`、`/var/log` 等）。后者在 OHOS 上不完整，
  因此当前版本只保证命令入口与辅助工具可用，完整检查流程见
  `3.2.4/notes.md` 第 8、9 节。

## 安装产物

```
bin/tiger  bin/tigexp  bin/tigercron           # 命令入口
share/tiger/                                   # tiger home
  config initdefs syslist
  bin/{md5,snefru,getpermit,realpath,testsuid} # C 辅助工具
  scripts/ systems/ util/ doc/explain.idx
etc/tiger/{tigerrc,cronrc}                     # 配置模板
var/tiger/{run,log}                            # 运行 / 日志目录
share/man/man8/{tiger,tigexp,tigercron}.8
```

安装脚本把绝对路径写进了 `config` 与三个命令入口，因此包内使用时要显式指定根目录：

```bash
<pkg>/bin/tiger  -B <pkg>/share/tiger -h
<pkg>/bin/tiger  -B <pkg>/share/tiger -v
TIGERHOMEDIR=<pkg>/share/tiger <pkg>/bin/tigexp init001e
```

## 功能验证

`test_package/test_tiger.sh` 共 11 条断言：安装布局、命令 shebang 解释器、
5 个 C 辅助工具、RFC 1321 MD5 向量、`c/snefru.c` 自带 Snefru 向量、
`realpath`、`getpermit`、`tigexp` 消息解释查询、`tiger -h`、`tiger -v`。

```bash
conan test test_package tiger/3.2.4@ohpcd/stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

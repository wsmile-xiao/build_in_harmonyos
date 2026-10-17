# GNU teseq

**Escape Sequence Illuminator** — 把含有终端控制序列的文件翻译成人类可读的描述，
并可由配套脚本 `reseq` 逆向还原（逐字节往返）。

- 上游主页：<https://www.gnu.org/software/teseq/>
- 手册：<https://www.gnu.org/software/teseq/manual/>
- 许可证：GPL-3.0-or-later

## 提供的能力

| 命令 | 说明 |
| --- | --- |
| `teseq` | 读入含控制序列的流/文件，输出可读的序列描述（`cat -v` 的信息量增强版） |
| `reseq` | 将 `teseq` 的输出还原为原始字节流（支持 `-t` 保留 timing 信息） |

典型用途：调试终端模拟器与重度使用高级终端特性的程序；把 `script` 产生的
typescript 去控制序列变成纯文本；编写/编辑终端动画演示；定位文件里不可见的
控制字符。

## 版本

| 版本 | 状态 | 说明 |
| --- | --- | --- |
| 1.1.1 | built | 首次适配；上游 `make check` 全绿（28 + 28 shell 用例 + exercise-seqs + 2 个 libcheck 单测） |

## 构建

```bash
conan create archives/t/teseq/1.1.1 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing \
  --user=ohpcd --channel=stable
```

产物：`bin/teseq`、`bin/reseq`、`share/info/teseq.info`、`share/man/man1/{teseq,reseq}.1`。

## OHOS 适配要点

- **configure umask 补丁（E129/E112/E136）**：HMDFS 对 `umask 077` 新建目录强制
  setgid，得到 `drwx--S---`，owner 也无法写入；autoconf 生成的 configure/
  config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，
  会以 `could not setup config files machinery` 失败。补丁
  `patches/0002-configure.patch` 把两处 `umask 077` 改为 `umask 022`
  （与已合入的 a52dec/0.7.4 同款）。
- **文档生成禁用（Makefile.in 补丁）**：automake 的 `doc/stamp-vti` 规则依赖
  teseq 自带的 mdate-sh，而它无法解析 HarmonyOS `ls` 的 ISO-8601 日期
  （解析失败时会把环境变量表写进 `doc/version.texi`），OHOS 又没有
  texinfo/makeinfo。补丁 `patches/0001-Makefile.in.patch` 把该规则改为 no-op，
  发行 tarball 自带的 info/man 原样安装；构建采用 in-source 方式（同 a52dec）。
- **完整上游测试**：`check/0.15.2`（ohpcd 制品仓）作为 test_requires +
  PkgConfigDeps 使 `PKG_CHECK_MODULES([libcheck], [check])` 探测成功，
  `make check` 因而额外编译执行两个 libcheck 单测；配合 `LD_LIBRARY_PATH`
  （check 包同时含 .a/.so）与 `TEMP/TMPDIR`（libcheck 的 `P_tmpdir`=/tmp
  只读优先级问题，E547）在真机上全部通过。
- **无需 C 源码修改**：不改 C 源码、不注入 `__OHOS__`。

详细的适配过程与问题清单见 [1.1.1/notes.md](1.1.1/notes.md)。

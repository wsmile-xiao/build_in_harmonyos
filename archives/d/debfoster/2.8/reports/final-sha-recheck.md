# final-sha-recheck — 最终 SHA 上的系统属性与可复算性复核

本文件记录收尾阶段在**最终工作树**上重跑的一遍实测，用于满足两条要求：

1. 「文档里凡出现 mode/权限/umask 类系统属性断言（`2771`/`2751`/`0640`、`chmod` 是否生效、
   文件是否仍存在/可复算），必须在最终 SHA 上重新实测一次并附复现命令与真实输出」——
   止血法是**先跑实验、把原始输出粘进文档，再写解释性文字**；
2. 「文档里声明的取数命令必须当场实跑一次」。

被复核对象就是本文件所在提交的树（`git -C <worktree> rev-parse HEAD`）。**构建输入**
（`conanfile.py` / `conandata.yml` / `patches/` / `generated/` / `test_package/conanfile.py` /
`test_package/test.sh`）自采信轮对应的输入版本起逐字节未变——复核命令：

```sh
git diff --stat 0d05ed199a730df764347e94e34c3662f795522b..HEAD -- \
  archives/d/debfoster/2.8/conanfile.py \
  archives/d/debfoster/2.8/conandata.yml \
  archives/d/debfoster/2.8/patches \
  archives/d/debfoster/2.8/generated \
  archives/d/debfoster/2.8/test_package/conanfile.py \
  archives/d/debfoster/2.8/test_package/test.sh
# （空输出——实测）
```

同区间另有两个**台账类**文件各有纯文本更新，如实登记（二者的改动都只落在证据引用上，
不参与 `conan create`）：

```sh
git diff --numstat 0d05ed19..HEAD -- archives/d/debfoster/2.8/manifest.yaml \
  archives/d/debfoster/2.8/test_package/MANIFEST.yml
2	2	archives/d/debfoster/2.8/manifest.yaml
3	3	archives/d/debfoster/2.8/test_package/MANIFEST.yml
# 内容：把指向本地 reports/conan-create.log 的 evidence 引用改指到已入库的
# reports/evidence-excerpts.md；逐行核对未改动任何命令、计数值或声明值
```

下文所有输出均为设备原始输出逐字粘贴，未做任何加工。

---

## 1. mode / 权限类断言复测

### 1.1 真实 `ac_tmp` 与其中的 `subs1.awk`（`notes.md` §4.1 的核心断言）

`ac_tmp` 默认在 config.status 进程退出时被其自身 trap 清理，因此要取真实文件必须让该
trap 不生效：开关是脚本内的 shell 变量 `debug`（`$debug || { trap … }`），而
`config.status --debug` 会把它置为 `:`。`configure` 自身**没有** `--debug` 选项
（下方 rc=1 为实测）。本次捕获两次独立复现结果一致。

```text
$ umask                                  # 真实构建的 ambient umask
0002
$ ./config.status --debug                # 在 configure 已运行过的 scratch 目录内重跑
rc=0
$ for f in conf??????; do case "$f" in config.*) continue;; esac
>   stat -c '%a %A %n' "$f" "$f"/subs1.awk "$f"/subs.awk "$f"/defines.awk; done
2751 drwxr-s--x conf6ZHlOo
660 -rw-rw---- conf6ZHlOo/subs1.awk
660 -rw-rw---- conf6ZHlOo/subs.awk
660 -rw-rw---- conf6ZHlOo/defines.awk
$ ls -d conf?????? | grep -v 'config\.'   # 另一目录走同一流程但不加 --debug
（无输出：退出 trap 已清理）
$ stat -c '%a %A %n' .../b/build-release/{config.log,Makefile,src/AVLTree.o}
660 -rw-rw---- .../b/build-release/config.log
660 -rw-rw---- .../b/build-release/Makefile
660 -rw-rw---- .../b/build-release/src/AVLTree.o
$ "$B/configure" --debug ; echo "rc=$?"
configure: error: unrecognized option: '--debug'
Try '.../b/configure --help' for more information.
rc=1
```

第二次捕获（另一次独立运行，采用**运行期间实时采样**——该目录在进程退出时即被 trap 清理，
故在其存活窗口内取到；逐字）：

```text
== 捕获 ac_tmp=confLoquhk（第 25 次探测）
2751 drwxr-s--x 20001006/file_manager confLoquhk
660 -rw-rw---- 20001006/file_manager confLoquhk/subs1.awk
660 -rw-rw---- 20001006/file_manager confLoquhk/subs.awk
660 -rw-rw---- 20001006/file_manager confLoquhk/defines.awk
configure rc=0
```

**结论**：目录 `2751 drwxr-s--x`；目录内三个片段 `0660 -rw-rw----`（**同组可读且可写**）。
`0640` 只在**显式 `umask 022`** 下建文件时出现，而补丁里的 `umask 022` 写在 `( … )`
子 shell 内、不改变随后写 `subs1.awk` 的父 shell 的 umask，真实构建的 ambient umask 是
设备默认的 `0002`（同一 build folder 内 configure/make 生成的文件亦全为 `0660`）。
两类 mode 由不同条件决定，不可写在同一处——`notes.md` §4.1 已按本结论改写。

片段内容与「无凭据/密钥」断言复核：

```text
$ F=<捕获的 subs1.awk>; wc -c "$F"; sha256sum "$F"
4659 /…/subs1.awk.captured
4b1b81eb534485d016247abd7000afae218147f83ba3f64f35d481dc2716af4a
$ head -3 "$F"
BEGIN {
S["am__EXEEXT_FALSE"]=""
S["am__EXEEXT_TRUE"]="#"
$ grep -c '^S\[' "$F"                                   # 变量赋值行数
126
$ grep -Eic 'password|passwd|token|secret|credential|api[_-]?key' "$F"
0
```

### 1.2 目录 mode 随 umask（`notes.md` §4.1 表格）

```text
$ for u in 077 022 002; do (umask $u; mkdir "mkdir$u"); t=$( (umask $u; mktemp -d "./mktemp$u.XXXXXX") ); done
$ stat -c '%a %A %U/%G %n' mkdir077 mkdir022 mkdir002 mktemp077.* mktemp022.* mktemp002.*
2700 drwx--S--- 20001006/file_manager mkdir077
2751 drwxr-s--x 20001006/file_manager mkdir022
2771 drwxrws--x 20001006/file_manager mkdir002
2700 drwx--S--- 20001006/file_manager mktemp077.DgDhVm
2751 drwxr-s--x 20001006/file_manager mktemp022.Zqs1JW
2771 drwxrws--x 20001006/file_manager mktemp002.cFolsO
$ ( echo x > mkdir077/f ); echo "rc=$?"
mkdir077/f: Permission denied
rc=1
```

表中三个数据点（`077→2700`、`022→2751`、`002→2771`）与 `mkdir`/`mktemp -d` 等价性全部复现。

### 1.3 文件 mode 随 ambient umask（`notes.md` §4.1 新增代码块）

```text
$ for u in 077 022 002; do (umask $u; echo x > "f_echo_$u"; touch "f_touch_$u"); done
$ stat -c '%a %A %n' f_echo_077 f_echo_022 f_echo_002 f_touch_077 f_touch_022 f_touch_002
600 -rw------- f_echo_077
640 -rw-r----- f_echo_022
660 -rw-rw---- f_echo_002
600 -rw------- f_touch_077
640 -rw-r----- f_touch_022
660 -rw-rw---- f_touch_002
```

### 1.4 `chmod` 对目录的双向 no-op（`notes.md` §4.1）

```text
$ mkdir base2771; (umask 077; mkdir base2700)
$ for d in base2771 base2700; do for m in 700 2771; do
>   echo "$d before=$(stat -c %a $d)"; chmod $m $d; echo "  chmod $m rc=$? after=$(stat -c %a $d)"; done; done
base2771 before=2771  chmod 700 rc=0 after=2771
base2771 before=2771  chmod 2771 rc=0 after=2771
base2700 before=2700  chmod 700 rc=0 after=2700
base2700 before=2700  chmod 2771 rc=0 after=2700
```

### 1.5 构建路径整链与上层目录（`notes.md` §4.1）

```text
$ stat -c '%a %A %U/%G %n' /storage /storage/Users /storage/Users/currentUser \
>   ~/.conan2 ~/.conan2/p ~/.conan2/p/b
711 drwx--x--x root/root /storage
711 drwx--x--x root/root /storage/Users
2771 drwxrws--x 20001006/file_manager /storage/Users/currentUser
2751 drwxr-s--x 20001006/file_manager /storage/Users/currentUser/.conan2
2751 drwxr-s--x 20001006/file_manager /storage/Users/currentUser/.conan2/p
2751 drwxr-s--x 20001006/file_manager /storage/Users/currentUser/.conan2/p/b
$ stat -c '%a %A %n' ~/.conan2/p/b/debfo567d371d4110f{,/b,/b/build-release}
2771 drwxrws--x /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f
2771 drwxrws--x /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b
2771 drwxrws--x /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/b/build-release
$ id -u; id
20020084
uid=20020084 gid=20020084 groups=20020084,1006(file_manager),1007(log),1097(netsys_socket),3009(readproc),3099(shader_cache)
```

进程 uid `20020084` 与目录属主 `20001006` 不同（`notes.md` §4 的机制前提）复现。

### 1.6 入库 mode：`generated/` 五份脚本 `100755`

```text
$ git ls-files -s archives/d/debfoster/2.8/generated/
100644 74dc5b627f5d20a3194ce1f5c85a371f329e8f2f 0	archives/d/debfoster/2.8/generated/PROVENANCE.md
100644 2092d06b3197712a6526519ce93714a1a26310ad 0	archives/d/debfoster/2.8/generated/aclocal.m4
100755 c8bd8fe63fa218660fdb0be9e66f068b69ac70dc 0	archives/d/debfoster/2.8/generated/config.guess
100755 4aaae46f6f74428949f32922308f48bd1316e7c1 0	archives/d/debfoster/2.8/generated/config.sub
100755 9f6725b9e0f5d699b10591f32af4bdf2b8516ff6 0	archives/d/debfoster/2.8/generated/depcomp
100755 1d8d96696466c7db04a23ee3f3b2562e1c16f9c6 0	archives/d/debfoster/2.8/generated/install-sh
100755 5e450bab3cdf4808973786e8f51d0a820b5afafe 0	archives/d/debfoster/2.8/generated/missing
```

五份辅助脚本 `100755`、`aclocal.m4` 与 `PROVENANCE.md` 为 `100644`，与申报一致。

### 1.7 包内产物 mode 与目录

```text
$ stat -c '%a %A %n' ~/.conan2/p/b/debfo567d371d4110f/p
2771 drwxrws--x /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p
$ ls -l ~/.conan2/p/b/debfo567d371d4110f/p/bin/debfoster
-rwxrwx--- 1 20001006 file_manager 244224 2026-09-11 10:01 /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p/bin/debfoster
$ stat -c '%a %A %n' ~/.conan2/p/b/debfo567d371d4110f/p/etc/debfoster.conf
660 -rw-rw---- /storage/Users/currentUser/.conan2/p/b/debfo567d371d4110f/p/etc/debfoster.conf
```

（文档中**没有**对包内产物 mode 的断言；此处仅记录现场取值 `bin/debfoster` `0770`、
其余普通文件 `0660`、包目录 `2771`，供后续比对。）

---

## 2. 由本节实测导出的文档修正

`notes.md` §4.1 有三处按本复核改写（均为文字，不改配方/补丁/测试）：

| 原表述 | 实测后的表述 |
| --- | --- |
| 「目录内生成的 `subs1.awk` 等配置片段落盘 **0640**，即同组用户可读」 | 「落盘 **0660**（`-rw-rw----`），即同组用户可读**且可写**」，并新增「取值条件必须连带声明」块（目录 mode 由建目录时 umask 决定；文件 mode 由建文件时进程 umask 决定；`0640` 是显式 `umask 022` 实验的值，不是本构建路径的值） |
| 「并在 `configure` 退出前由 `config.status` 的退出 trap … 清理（仅 `configure --debug` 时不挂该 trap）」 | 改为「在该次 config.status 进程退出时由**其自身**的退出 trap 清理；trap 开关是脚本内变量 `debug`，`config.status --debug` 会不挂该 trap（`configure` 无 `--debug`，实测 rc=1），故该例外只在直接运行 config.status 时出现」 |
| 「同组可读」「可读者是同组」 | 「同组可读写」（目录 `2751` 同组可读可遍历 + 片段 `0660` 同组可读可写） |

---

## 3. 其他「仍存在 / 仍可复算」断言复核

### 3.1 七件打包产物 sha256（两个包目录各自复算，逐字节一致）

```text
$ for pd in ~/.conan2/p/b/debfo*/p; do for rel in bin/debfoster etc/debfoster.conf \
>   licenses/COPYING licenses/LICENSE.AVLTree licenses/LICENSE.debfoster licenses/LICENSE.symbol \
>   share/man/man8/debfoster.8; do printf '%s  %s\n' "$(sha256sum "$pd/$rel" | cut -d' ' -f1)" "$rel"; done; done
17c66a113ca9d80dfb485b6ed46da9eb96ce81d39d25fcf5ee4862daebd2b5ce  bin/debfoster
7ca9db900d969dc9efdd8b7cbf1953dfccb16c4426b1a0a9585bed2135d8eaf7  etc/debfoster.conf
876406815e3912e17d794fb16c3d0bbbe3317ba8aa3263cc5802b73b6c3e1a35  licenses/COPYING
7a4436f9ec37603356791c87de3bc444989befd2682d29efb3d97604e04c1852  licenses/LICENSE.AVLTree
32b1062f7da84967e7019d01ab805935caa7ab7321a7ced0e30ebe75e5df1670  licenses/LICENSE.debfoster
5bbcbb737e60fe9deba08ecbd00920cfcc3403ba2e534c64fdeea49d6bb87509  licenses/LICENSE.symbol
fc63e0c9236adea0127612a3c62bc6f62b4217ae0941132371eb5c8b915cea18  share/man/man8/debfoster.8
（两个包目录 debfo567d371d4110f 与 debfoa67fa32ac0e26 输出逐行相同）
```

与 `reports/conan-verify-supplement.md` 的两轮对照表逐值一致。

### 3.2 `generated/` 六份 sha256 与 `PROVENANCE.md` 对照

```text
$ sha256sum archives/d/debfoster/2.8/generated/*
cb602d841844af4eda822780944e88e5f1173bdeb0102fc30f91beee861a884d  config.guess
11c54f55c3ac99e5d2c3dc2bb0bcccbf69f8223cc68f6b2438daa806cf0d16d8  config.sub
776876b3909b096439109a4c7642eb0f9100f6ba3fb42fa93d05351e50a0a7ef  install-sh
4f17c4a66ec5b8000d44573a576f6b5d9c0c84848e8fd1286f84a52f439db4e9  missing
ac3ae010382a83144ff6ec1a4c368a3f16a14ea2b12751aa73ddfb548d931574  depcomp
b107acdf6138b9ec0b46511913febd9fdcc73b74364fda1f9f43c0abbb72dd12  aclocal.m4
$ sh <generated/config.guess>
aarch64-unknown-linux-ohos
$ sh <generated/config.sub> aarch64-unknown-linux-ohos
aarch64-unknown-linux-ohos
$ grep -m1 '^timestamp=' archives/d/debfoster/2.8/generated/config.guess
timestamp='2024-07-27'
$ grep -m1 '^timestamp=' archives/d/debfoster/2.8/generated/config.sub
timestamp='2024-05-27'
```

### 3.3 三份 `-log.md` 与原始日志的逐字 round-trip

```text
$ python3 - <<'PY'   # 抽出 ``` 围栏内正文与本地原始 .log 逐字节比较
conan-create-log.md: fenced=46472B/623行  逐字节相同=True
conan-create-l5-round2-log.md: fenced=46472B/623行  逐字节相同=True
w3-local-ci-log.md: fenced=49803B/733行  逐字节相同=True
$ wc -l <reports>/{conan-create-log.md,conan-create-l5-round2-log.md,w3-local-ci-log.md,conan-create.log,conan-create-l5-round2.log,w3-local-ci.log}
   643 /…/reports/conan-create-log.md
   643 /…/reports/conan-create-l5-round2-log.md
   753 /…/reports/w3-local-ci-log.md
   623 /…/reports/conan-create.log
   623 /…/reports/conan-create-l5-round2.log
   733 /…/reports/w3-local-ci.log
  4018 total
$ sha256sum <reports>/*.log
ef35ef54f139228d7a36ae7da3f84be931dd4bc26e0fa75004c452233dbfbb7a  /…/reports/conan-create.log
f731d5e86525bdf5aac6dadcc8d9955352b9ca71d996c240ef16d49c9424e9be  /…/reports/conan-create-l5-round2.log
dcdaa830ec9bcc3c8aaa6d1b541fc39f784faf70684893b68d973162b8c31f99  /…/reports/w3-local-ci.log
```

三份 `.md` 头部声明的字节数/行数/sha256（46472/623、46472/623、49803/733）与本地原始日志
逐一相同；`.md` 自身行数为 643/643/753，即比原始正文多 20 行（头部表格 + 围栏），
**不是** 623/623/733。

### 3.4 计数类断言（原始 `.log` 与入库 `-log.md` 双面各跑一次）

```text
$ for f in conan-create.log conan-create-log.md conan-create-l5-round2.log conan-create-l5-round2-log.md; do
>   printf '%-28s check=%s check-am=%s ApplyPatch=%s bashRUN=%s HMBS=%s\n' "$(basename $f)" \
>     "$(grep -c "Nothing to be done for 'check'" $f)" "$(grep -c 'check-am' $f)" \
>     "$(grep -c 'Apply patch (portability)' $f)" "$(grep -c 'RUN: /data/service/hnp/bin/bash' $f)" \
>     "$(grep -c 'HMBS_TEST_SUMMARY discovered=36 passed=36 failed=0 skipped=0' $f)"; done
conan-create.log             check=3  check-am=1  ApplyPatch=3  bashRUN=1  HMBS=1
conan-create-log.md          check=3  check-am=1  ApplyPatch=3  bashRUN=1  HMBS=1
conan-create-l5-round2.log   check=3  check-am=1  ApplyPatch=3  bashRUN=1  HMBS=1
conan-create-l5-round2-log.md check=3  check-am=1  ApplyPatch=3  bashRUN=1  HMBS=1
```

### 3.5 源码 tarball 重新下载后复算

```text
$ curl -sSL --max-time 120 https://deb.debian.org/debian/pool/main/d/debfoster/debfoster_2.8.orig.tar.xz -o t.tar.xz
rc=0  size=142780
$ sha256sum t.tar.xz
c5d044a89642603987e216d406d8f9aa74c60240be4b4992f45bd9b743a9a522  t.tar.xz
$ grep -n 'sha256' archives/d/debfoster/2.8/conandata.yml
3:  sha256: "c5d044a89642603987e216d406d8f9aa74c60240be4b4992f45bd9b743a9a522"
```

（采信轮期间的 tarball 缓存已被清缓存轮清除，本值是收尾时按 `conandata.yml` 的官方 URL
重新下载后复算的；与申报值及 W4 审计时的实测值一致。）

### 3.6 三个补丁在 pristine 上游树上的 dry-run

```text
$ tar -xf debfoster_2.8.orig.tar.xz -C pristine && cd pristine/debfoster-2.8
$ for p in <patches>/*.patch; do echo "--- $(basename "$p")"; patch -p1 --dry-run < "$p" 2>&1; echo "rc=$?"; done
--- 0001-configure-umask-hmdfs.patch
patching configure
rc=0
--- 0002-keepers-include-fcntl.patch
patching src/keepers.c
rc=0
--- 0003-etc-makefile-install-d.patch
patching etc/Makefile.am
patching etc/Makefile.in
rc=0
```

（三个补丁各自 rc=0；`0003` 同时改 `Makefile.am` 与 `Makefile.in` 两个文件。）

### 3.7 上游测试入口 N=0 的四口径候选数法（同一 pristine 树）

```text
$ grep -c 'TESTS\|check_PROGRAMS' Makefile.am src/Makefile.am etc/Makefile.am doc/Makefile.am
Makefile.am:0
src/Makefile.am:0
etc/Makefile.am:0
doc/Makefile.am:0
$ ls -1 test_*.c *_test.c 2>/dev/null | wc -l
0
$ ls -d tests test check spec 2>/dev/null | wc -l
0
$ python3 -m tarfile -l debfoster_2.8.orig.tar.xz | grep -Eic '(^|/)(tests?|checks?|specs?)(/|$)'
0
```

四口径一致为 0，与 PR 正文的上游用例数申报及 `test_package/MANIFEST.yml` 台账一致。

---

## 4. 覆盖范围与局限

- 本节复测覆盖「系统属性（mode/权限/umask/chmod）、文件存在性与可复算性、声明式计数、
  补丁可应用性、上游用例数取数口径」五类断言，全部在最终工作树上现跑。
- **未**在收尾阶段重跑 `conan create` / `conan-verify` / W3：构建输入自
  `0d05ed199a730df764347e94e34c3662f795522b` 起逐字节未变（命令与实测输出见文件头），
  本轮 delta 只含 `reports/**` 与 `notes.md`，不改变任何产物字节；产物侧以
  §3.1 的两轮包目录 sha256 复算为准。台账类文件 `manifest.yaml` /
  `test_package/MANIFEST.yml` 在更早的区间有纯证据引用文本更新（文件头已登记行数与内容），
  同样不改变产物字节。
- 采信轮与 L5 复现轮各自的清缓存过程未重跑，因此「两轮产物逐字节一致」这一结论沿用
  既有两轮日志与存活包目录（两份包目录均在设备上，§3.1 已对两份分别复算）。

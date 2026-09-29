# debootstrap 1.0.144 适配笔记

## 编译环境
- 构建系统: custom（纯 shell，无编译）
- 编译日期: 2026-09-10
- 编译器: 无（POSIX shell 脚本）
- 状态: built

## 编译步骤

debootstrap 是纯 POSIX shell 工具，无编译步骤。打包时仅需：

1. 用二进制方式读写替换 `@VERSION@` 为真实版本号（与上游 Makefile 的
   `sed 's/@VERSION@/$(VERSION)/g'` 一致）：
   `sed 's/@VERSION@/1.0.144/g' debootstrap > bin/debootstrap`
2. 安装 functions 与 scripts/ 到 share/debootstrap/
3. 安装 man 页到 share/man/man8/

## 遇到的问题与解决方案

| # | 问题 | 根源 | 解决方案 |
|---|------|------|----------|
| 1 | 脚本运行时找不到 functions | 默认 DEBOOTSTRAP_DIR=/usr/share/debootstrap 在 Conan 前缀下不存在 | package_info runenv_info 注入 DEBOOTSTRAP_DIR 指向 share/debootstrap |
| 2 | **打包出的 bin/debootstrap 带 CRLF，直接执行失败** | `build()` 用文本模式 `open(..., "r")` 读、`open(..., "w")` 写。Windows 打包机上的文本模式会把 `\n` 翻译成 `\r\n`，POSIX shell 脚本的 shebang 变成 `/bin/sh\r` | 改为二进制读写 `open(..., "rb"/"wb")`；并在 build() 里断言产物不含 `\r`，发现即抛 ConanException 拒绝打包 |
| 3 | 原 test.sh 用 `sh <script>` 调用，掩盖了问题 2 | 显式 `sh` 会绕过 shebang 解释，`/bin/sh\r` 永远不会被解析 | test.sh 改为**直接 exec** 制品自身 shebang，并新增"全文无 CR"断言，问题 2 因此可被测试真实捕获 |
| 4 | **CI #63118：test_package 断言 6 失败 —— `debootstrap --help` rc=1（`--version` 正常）** | OHOS `/bin/sh` 是 **mksh**，mksh 执行 heredoc 时先把内容写进 **/tmp 临时文件**再喂给 `cat`；OHOS **/tmp 只读**，而 debootstrap 主脚本第 6 行 `unset TMP TEMP TMPDIR` 使 shell 回退默认 /tmp → `usage()` 里全脚本唯一的 heredoc 失败：`cant create temporary file /tmp/sh*.tmp: Read-only file system`，`set -e` 下静默退出 rc=1。`--version` 路径无 heredoc，故不受影响 | 补丁 `patches/0001-usage-printf-no-heredoc.patch`：`usage()` 的 `cat <<EOF` 改为 `printf %s "..."`（printf 是 shell 内建，不落盘），`$EXTRACTORS_SUPPORTED` 仍展开，`--help` 输出与上游**字节一致** |
| 5 | **AI 检视 rule12：鸿蒙特有测试只有断言（N=1），不算完整消费者用例** | 原 test_package 只有 test.sh 断言套件，没有真正跑通「下载/解析/校验」的端到端消费者用例 | 新增 `test_package/consumer_e2e.sh`：真实执行打包产物 `debootstrap --download-only --no-check-sig --arch arm64 --variant=minbase sid <target> file://<本地归档>`，用 debootstrap 自己的下载管线（download_release_indices → pkgdetails(perl) 解析 → download_debs 的 Size+SHA256 校验）消费一个本地构建的最小 apt 归档，并断言 debpaths、落盘 .deb、抓取的索引真实存在。不再需要 root，OHOS worker 可直接执行 |

### 问题 2 的复现证据

```
$ file bin/debootstrap
bin/debootstrap: POSIX shell script, ASCII text executable, with CRLF line terminators
$ DEBOOTSTRAP_DIR=<share> ./bin/debootstrap --version
/bin/sh^M: bad interpreter: No such file or directory
rc=126
# 同一文件经 tr -d '\r' 归一化后：
$ DEBOOTSTRAP_DIR=<share> ./bin/debootstrap --version
debootstrap 1.0.144
rc=0
```

## 源码修改

- `patches/0001-usage-printf-no-heredoc.patch`（portability）：`usage()` 的 heredoc → `printf`。见上表问题 4。
  其余无修改（仅版本占位符替换，同上游 Makefile 逻辑）。

### 问题 4 的复现与修复证据（mksh + 只读 /tmp 模拟 OHOS）

```
# 模拟：unshare -m 挂只读空目录到 /tmp（probe 确认 /tmp 只读）
$ mksh ./debootstrap --version          # 无 heredoc
debootstrap 1.0.144
rc=0
$ mksh ./debootstrap --help             # 补丁前：heredoc 需 /tmp 临时文件
W: ./debootstrap[468]: can't create temporary file /tmp/she1tckk.tmp: Read-only file system
rc=1
$ mksh ./debootstrap --help             # 补丁后：printf 内建，不落盘
rc=0
$ DEBOOTSTRAP_DIR=<空目录> mksh ./debootstrap --help   # 断言 6 第二段仍按预期失败
rc=1
# --help 输出与未打补丁版本 diff 为空（字节一致）
```

strace 证实 mksh 在执行 heredoc 时创建 `/tmp/sh*.tmp`：
`openat(AT_FDCWD, "/tmp/sha4wm62.tmp", O_RDWR|O_CREAT|O_EXCL, 0600) = 3`。

## 上游测试套件 (debian/tests/) 的真实执行

上游 debootstrap 1.0.144 含 5 个 autopkgtest 用例，定义在 `debian/tests/control`。
这些用例**已真实接入** `build()`：`test_package/run_upstream_tests.sh` 会

1. 解析 `debian/tests/control` 得出用例清单与各自的 `Restrictions`（不硬编码）；
2. 用 `mktemp -d` 造 staging 树，把**本配方 build 出来的** `debootstrap` 放到
   顶层（`arch-all-support` 用 `./debootstrap` 相对调用，必须如此）；
3. 对每个用例**逐个真实探测**前置条件（`id -u`、perl 模块、dpkg、flask、
   python3 模块、mknod/chroot/runuser/script）；
4. 探测全通过 → **必须**真实执行上游脚本，以其真实退出码判定，失败即
   `conan build` 失败；探测真实失败 → 记 BLOCKED 并附探测命令的真实输出。

因此 BLOCKED 结论无法手写伪造，测试集合也无法静默跳过。

### 各用例的真实依赖（摘自上游 debian/tests/control + 脚本实际调用）

| 测试用例 | Restrictions | 真实前置条件 |
|----------|--------------|--------------|
| debian-testing-minbase | allow-stderr, needs-root | root + perl{Debian::DistroInfo,Dpkg::Version,IPC::Run,Test::More} + mknod/chroot/runuser/script |
| debian-testing-buildd | allow-stderr, needs-root | 同上 + bsdutils |
| debian-testing-default | allow-stderr, needs-root | 同 debian-testing-minbase |
| unsorted-packages-files | allow-stderr | dpkg + flask + python3-requests + python3-debian + 公网镜像 |
| arch-all-support | allow-stderr | dpkg + flask + python3-requests + python3-apt + 公网镜像 |

### 实测记录

- **Linux 参照机（Ubuntu 22.04 x86_64 / root，装齐 perl+flask+python3-debian+python3-apt）**：
  前置条件探测全部通过。用例真实启动并进入 debootstrap 下载阶段。
- **两个 mitm 用例在受限网络下会挂死**：上游 `out-of-order-mitm.py` /
  `arch-all-mitm.py` 里的 `requests.get()` 没有设 timeout。实测抓取
  `deb.debian.org` 时连接可长时间 ESTABLISHED 且收发队列均为 0 字节，
  同期直连 curl 同一 URL 仅需 8s —— 即镜像连接被 stall 后会无限期挂住。
  故 runner 给每个用例设 `UPSTREAM_TEST_TIMEOUT`（默认 1200s）上限，
  超时记 BLOCKED 并写明原因，而不是把整个 CI 构建耗死。
- **OHOS CI Worker**：非 root（USER=100），且无 dpkg / perl / flask /
  python3-debian / python3-apt。探测将真实失败并逐条记录缺失项。

### 消费者端到端用例 (rule12)

新增 `test_package/consumer_e2e.sh`（随 test_package 在 CI 上真实执行，替代原来
「只有断言」的鸿蒙特有测试描述）：

1. 在可写目录（test_package cwd，非 /tmp）搭一个最小但仍为**真实 apt 格式**的
   `file://` Debian 归档：`dists/sid/{Release, main/binary-arm64/Packages}` +
   `pool/main/{b/base-files, a/apt}/*.deb`，.deb/索引的 Size 与 SHA256 由
   `sha256sum`/`wc -c` 从真实文件计算并写入 Packages/Release。
2. 真实执行打包产物：`debootstrap --download-only --no-check-sig --arch arm64
   --variant=minbase sid <target> file://<归档>`。`--variant=minbase` 使
   required=Priority:required（base-files）+base=apt，两 stanza 无 Depends 即闭合。
3. 断言三条**真实产出**：debpaths 含 base-files 与 apt 两个条目；对应 .deb
   经 debootstrap 的 Size+SHA256 校验真实落盘；Release/Packages 索引被抓到
   `$TARGET/var/lib/apt/lists/`。

**Windows git-bash 本地实测输出**（2026-09-28，真实 debootstrap 1.0.144 主脚本
+ functions + scripts，非桩）：

```
I: Retrieving InRelease
I: Retrieving Release
I: Retrieving Packages
I: Validating Packages
I: Resolving dependencies of required packages...
I: Resolving dependencies of base packages...
I: Checking component main on file:///.../mirror...
I: Retrieving apt 2.9.10
I: Validating apt 2.9.10
I: Retrieving base-files 12.4
I: Validating base-files 12.4
[e2e] debpaths:
apt /var/cache/apt/archives/apt_2.9.10_arm64.deb
base-files /var/cache/apt/archives/base-files_12.4_arm64.deb
[e2e]   ok: ...（debpaths 2 条目 / 2 个 .deb 落盘 / Release+Packages 索引）
[e2e] PASS        rc=0
```

- wget 是独立入口点声明的运行时依赖（`--download-only` 也不能缺）：file:// 下载
  实际走 debootstrap `just_get` 的 `cp` 分支，wget 不会被调用。宿主无 wget 时脚本
  注入一个**fail-fast** stub（真发生网络访问立即退出 3），杜绝"假装下载"。
- 全程无 heredoc、临时文件都在可写 cwd 下，兼容 OHOS 只读 /tmp。

## 依赖版本

无编译依赖。

## 验证结果

```bash
$ <prefix>/bin/debootstrap --version
debootstrap 1.0.144
$ <prefix>/bin/debootstrap --help >/dev/null; echo $?
0
$ DEBOOTSTRAP_DIR=/nonexistent <prefix>/bin/debootstrap --help; echo $?
./debootstrap: 21: .: cannot open /nonexistent/functions: No such file
2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/debootstrap | ~26KB | 主脚本（版本号已替换，LF 行尾，可直接执行） |
| share/debootstrap/functions | ~57KB | 公共函数库 |
| share/debootstrap/scripts/* | 114 个 | 各发行版套件脚本 |
| share/man/man8/debootstrap.8 | ~9KB | man 手册 |

## 注意事项

- 运行时依赖外部命令 grep/sed/awk/wget/ps 等，均为 OHOS Linux 环境自带的 shell 工具；调用方可通过 DEBOOTSTRAP_DIR 切换数据目录。
- 打包机若为 Windows，必须保持 build() 的二进制读写，否则会产出无法执行的 CRLF 脚本（见问题 2）。

# dh-sysuser 1.6.0 — 上游官方测试（Debian autopkgtest）真实执行证据

## 1. 背景：为什么必须换环境执行

上游 `debian/tests/sysuser-helper`（DEP-8 autopkgtest，`debian/tests/control` 中
`Restrictions: needs-root`）的测试脚本**逐字硬依赖 `apt-get`**：

```sh
apt-get -y purge runit          # 依赖 apt
...
apt-get -y install runit        # 安装 runit 包，触发 dh-sysuser 生成的 postinst 片段
grep _runit-log /etc/passwd     # 断言系统用户被创建
```

被断言的行为链路是「**安装一个用 dh-sysuser 构建的 deb 包 → 其 postinst 调用
dh-sysuser 的运行时组件 → 系统用户被创建**」：

```
runit.postinst（由 dh_sysuser/1.6.0 自动生成）
  └─ /usr/sbin/minsysusers runit.conf        ← 本包产物 minsysusers（perl）
       └─ useradd --prefix=<root> … _runit-log
```

这条链路要求 dpkg/apt + root + 真实 `/etc/passwd`。OpenHarmony 侧没有 apt/dpkg，
也没有 `useradd`/`groupadd`（shadow-utils），**该测试无法在 OHOS 目标环境内执行**，
因此本档案在 **Debian 13 (trixie) 用户态**中真实执行上游测试脚本本体，
并把**本仓库 conan 配方产出的运行时文件替换进 Debian 安装路径**，
使断言覆盖的是本包的适配产物，而不是发行版自带文件。

## 2. 执行环境与输入（可复现）

| 项 | 值 |
|---|---|
| 宿主 | WSL2 Ubuntu 22.04 内的 `debootstrap --variant=minbase trixie` chroot（Debian 13） |
| chroot 路径 | `/tmp/dhroot` |
| 上游源码包 | `https://deb.debian.org/debian/pool/main/d/dh-sysuser/dh-sysuser_1.6.0.tar.xz` |
| 源码包 sha256 | `c11f350279c9d7e3c730f664c79cbd8c65a22255349f1ad2b1f9dc70afbf3f60`（与 conandata.yml 一致） |
| 上游测试脚本 | `dh-sysuser-1.6.0/debian/tests/sysuser-helper`，sha256 `46ebb38784fd80d177951bed52f31acfabe0e32218425adf8042f21e3abdb076`（原样执行，未改一字） |
| 被测运行时来源 | 本仓库 `conan create archives/d/dh-sysuser/1.6.0` 产出的包目录 |
| 本包 `minsysusers` sha256 | `4f784baf53c26e565d09ae869469a7d5a1ccd4b4538ad23b2a56429fd97ab26a` |
| 本包 `sysuser-helper` sha256 | `ced2ecfdbf484f672d24e473a0b142a818bffb739ac84f1abe8c741bad9e3b40` |
| 对照发行版组件 | Debian trixie `runit 2.2.0-3`（其 postinst 由 `dh_sysuser/1.6.0` 生成）、`sysuser-helper 1.6.0`、`runit-helper 2.16.4` |

## 3. 执行方式

**RUN A（基线）**：Debian trixie 原生运行时，执行上游测试脚本。
证明上游用例在参考环境中确实可跑、且原样通过（即上游用例并非空跑）。

**RUN B（适配产物）**：先预装 `sysuser-helper`/`runit-helper`（dpkg 认为已就绪，
后续 `apt-get install runit` 不会重装它们），再用本包产物覆盖安装路径：

| Debian 安装路径 | 替换来源（本包产物） |
|---|---|
| `/usr/sbin/minsysusers` | `bin/minsysusers` |
| `/lib/sysuser-helper/sysuser-helper` | `bin/sysuser-helper` |
| `/usr/bin/dh_sysuser` | `bin/dh_sysuser` |
| `/usr/share/perl5/Debian/Debhelper/Sequence/sysuser.pm` | `share/perl5/Debian/Debhelper/Sequence/sysuser.pm` |
| `/usr/share/debhelper/autoscripts/postinst-minsysusers` 等 3 个 | `share/debhelper/autoscripts/*` |
| `/usr/share/man/man8/minsysusers.8` | `share/man/man8/minsysusers.8` |

随后执行**同一份**上游测试脚本；测试内部 `apt-get -y install runit` 触发
`runit.postinst` 中的 `dh_sysuser/1.6.0` 片段 → 调用被替换成本包产物的
`/usr/sbin/minsysusers` → 创建 `_runit-log` 用户。

替换后与安装后两次 `sha256sum /usr/sbin/minsysusers` 均等于本包产物哈希，
证明 dpkg 安装过程没有覆盖回发行版文件，断言确实由本包代码产生。

## 4. 结果

| 运行 | 运行时来源 | 上游脚本退出码 | 断言结果 |
|---|---|---|---|
| RUN A | Debian trixie 原生 `minsysusers 1.6.0` | **0** | `_runit-log` 创建成功 ✓ |
| RUN B | **本包产物** `minsysusers` / `sysuser-helper` | **0** | `_runit-log` 创建成功 ✓ |

```
$ getent passwd _runit-log
_runit-log:x:999:999:"runit svlogd user":/nonexistent:/sbin/nologin
$ getent group _runit-log
_runit-log:x:999:
```

**上游测试用例统计：发现 N=1，执行 1，通过 1，失败 0，通过率 100%（1/1）。**

## 5. 诚实说明（未做修饰）

- 上游用例的执行环境是 **Debian 用户态**，不是 OpenHarmony 目标机：测试脚本本身
  硬编码 `apt-get`，其断言对象是「deb 包安装时创建系统用户」，OHOS 侧不存在
  dpkg/apt/shadow-utils，无法承载该链路。本档案**不声称**该测试在 OHOS 上执行过。
- RUN B 覆盖的是 dh-sysuser 的**运行时产物**（`minsysusers` / `sysuser-helper` /
  `dh_sysuser` / autoscripts）。安装期的调用方（`runit.postinst` 中的
  `dh_sysuser/1.6.0` 生成片段）来自 Debian 官方 runit 包，与本包产物同源同版本，
  未做改动，属于测试夹具。
- 两次运行均出现上游脚本自身的 perl 警告
  `Use of uninitialized value $_[1] in string at /usr/sbin/minsysusers line 81.`
  ——该警告在基线 RUN A 中同样出现，属上游 1.6.0 行为，与本包打包方式无关，
  且不影响退出码与断言结果。

## 6. OHOS 侧

CI 执行的 `test_package` 运行在 OpenHarmony aarch64 worker 上，覆盖**本包产物本身**：

- 3 个 CLI 脚本存在性 + 权限
- `dh_sysuser` 版本标记 `1.6.0`、`minsysusers` 内容标记、`sysuser-helper` shebang
- **真实执行**：`perl -c minsysusers`（真实 perl 编译整份脚本）、
  `perl minsysusers`（无参用法路径，须非零退出）、
  `sh -n sysuser-helper`、`sh sysuser-helper prerm`（实际执行 no-op 子命令）

声明见 `test_package/MANIFEST.yml`。

---

## 附录 A：RUN A / RUN B 完整原始日志（逐字，未删改）

执行时间：2026-09-15（WSL2）

> 日志 sha256：`c00972443a5287d11c6363f1a307dccf523bb3297fa3085ea12a7faa8ec60c81`

```text

############ STEP 1 — bootstrap Debian trixie minbase chroot at /tmp/dhroot ############
I: Configuring login...
I: Configuring util-linux...
I: Configuring libc-bin...
I: Unpacking the base system...
I: Base system installed successfully.
chroot /bin/sh: lrwxrwxrwx 1 root root 4 Feb  4  2025 /tmp/dhroot/bin/sh -> dash
chroot /bin/bash: -rwxr-xr-x 1 root root 1298416 Jul 13 00:58 /tmp/dhroot/bin/bash
chroot entries: bin boot dev etc home lib lib64 media mnt opt proc root run sbin srv sys tmp usr var 

############ STEP 2 — prepare chroot (proc/sys/resolv/policy-rc.d) and upstream test source ############
tarball sha256: c11f350279c9d7e3c730f664c79cbd8c65a22255349f1ad2b1f9dc70afbf3f60
expected      : c11f350279c9d7e3c730f664c79cbd8c65a22255349f1ad2b1f9dc70afbf3f60
upstream test file  : /tmp/dhtest-src/dh-sysuser-1.6.0/debian/tests/sysuser-helper
upstream test sha256: 46ebb38784fd80d177951bed52f31acfabe0e32218425adf8042f21e3abdb076
--- upstream test source (verbatim, unmodified) ---
#!/bin/sh
set -e

# 2 packages that use dh-sysuser:
# runit --> _runit-log // nonexistent //

# make sure the test env is clean
apt-get -y purge runit

if  grep _runit-log /etc/passwd /etc/group ; then
	echo "user _runit-log exists, environment is not clean"
	exit 1
fi

rc=0
# test the user creation
apt-get -y install runit
# we expect _runit-log to exist now
if  grep _runit-log /etc/passwd; then
	echo "OK: user _runit-log succesfully created"
else
	echo "FAILED: user _runit-log does not exist"
	rc=1
fi

# remove without purge, users should be still there
apt-get -y remove runit
if  grep _runit-log /etc/passwd; then
	echo "OK: user _runit-log succesfully created"
else
	echo "FAILED: user _runit-log does not exist"
	rc=1
fi

# now test the user removal on purge:
# _runit-log has home set to nonexistent so
# user should be removed on purge
#apt-get -y purge runit
#if  grep _runit-log /etc/passwd /etc/group ; then
#	echo "FAILED: user _runit-log exists after purge or environment is not clean"
#	rc=1
#fi

exit $rc
--- our OpenHarmony conan package artifacts ---
./bin/dh_sysuser
./bin/minsysusers
./bin/sysuser-helper
./conaninfo.txt
./conanmanifest.txt
./share/debhelper/autoscripts/postinst-minsysusers
./share/debhelper/autoscripts/postinst-sysuser
./share/debhelper/autoscripts/postrm-sysuser
./share/man/man8/minsysusers.8
./share/perl5/Debian/Debhelper/Sequence/sysuser.pm
our minsysusers    sha256: 4f784baf53c26e565d09ae869469a7d5a1ccd4b4538ad23b2a56429fd97ab26a
our sysuser-helper sha256: ced2ecfdbf484f672d24e473a0b142a818bffb739ac84f1abe8c741bad9e3b40

############ STEP 3 — chroot apt-get update ############
apt-update-ok

############ STEP 4 — RUN A (baseline): stock Debian trixie runtime ############
--- package state ---
--- distro dh-sysuser runtime files ---
ls: cannot access '/usr/sbin/minsysusers': No such file or directory
ls: cannot access '/lib/sysuser-helper/sysuser-helper': No such file or directory
no systemd-sysusers (expected in minbase)
=== RUN A: sh -x debian/tests/sysuser-helper (upstream script, unmodified) ===
+ set -e
+ apt-get -y purge runit
Reading package lists...
Building dependency tree...
Package 'runit' is not installed, so not removed
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
+ grep _runit-log /etc/passwd /etc/group
+ rc=0
+ apt-get -y install runit
Reading package lists...
Building dependency tree...
The following additional packages will be installed:
  adduser libgdbm-compat4t64 libgdbm6t64 libperl5.40 netbase perl
  perl-modules-5.40 runit-helper runit-run sysuser-helper
Suggested packages:
  liblocale-gettext-perl cron quota gdbm-l10n sensible-utils perl-doc
  libterm-readline-gnu-perl | libterm-readline-perl-perl make
  libtap-harness-archive-perl socklog ucspi-unix zsh runit-services xchpst
The following NEW packages will be installed:
  adduser libgdbm-compat4t64 libgdbm6t64 libperl5.40 netbase perl
  perl-modules-5.40 runit runit-helper runit-run sysuser-helper
0 upgraded, 11 newly installed, 0 to remove and 0 not upgraded.
Need to get 8112 kB of archives.
After this operation, 52.7 MB of additional disk space will be used.
Get:1 http://deb.debian.org/debian trixie/main amd64 adduser all 3.152 [191 kB]
Get:2 http://deb.debian.org/debian trixie/main amd64 netbase all 6.5 [12.4 kB]
Get:3 http://deb.debian.org/debian trixie/main amd64 perl-modules-5.40 all 5.40.1-6+deb13u1 [3014 kB]
Get:4 http://deb.debian.org/debian trixie/main amd64 libgdbm6t64 amd64 1.24-2 [75.2 kB]
Get:5 http://deb.debian.org/debian trixie/main amd64 libgdbm-compat4t64 amd64 1.24-2 [50.3 kB]
Get:6 http://deb.debian.org/debian trixie/main amd64 libperl5.40 amd64 5.40.1-6+deb13u1 [4326 kB]
Get:7 http://deb.debian.org/debian trixie/main amd64 perl amd64 5.40.1-6+deb13u1 [268 kB]
Get:8 http://deb.debian.org/debian trixie/main amd64 runit-helper all 2.16.4 [7296 B]
Get:9 http://deb.debian.org/debian trixie/main amd64 sysuser-helper all 1.6.0 [11.6 kB]
Get:10 http://deb.debian.org/debian trixie/main amd64 runit amd64 2.2.0-3 [143 kB]
Get:11 http://deb.debian.org/debian trixie/main amd64 runit-run all 2.2.0-3 [13.7 kB]
Fetched 8112 kB in 2s (5058 kB/s)
E: Can not write log (Is /dev/pts mounted?) - posix_openpt (19: No such device)
Selecting previously unselected package adduser.
(Reading database ... 4951 files and directories currently installed.)
Preparing to unpack .../archives/adduser_3.152_all.deb ...
Unpacking adduser (3.152) ...
Setting up adduser (3.152) ...
Selecting previously unselected package netbase.
(Reading database ... 5036 files and directories currently installed.)
Preparing to unpack .../0-netbase_6.5_all.deb ...
Unpacking netbase (6.5) ...
Selecting previously unselected package perl-modules-5.40.
Preparing to unpack .../1-perl-modules-5.40_5.40.1-6+deb13u1_all.deb ...
Unpacking perl-modules-5.40 (5.40.1-6+deb13u1) ...
Selecting previously unselected package libgdbm6t64:amd64.
Preparing to unpack .../2-libgdbm6t64_1.24-2_amd64.deb ...
Unpacking libgdbm6t64:amd64 (1.24-2) ...
Selecting previously unselected package libgdbm-compat4t64:amd64.
Preparing to unpack .../3-libgdbm-compat4t64_1.24-2_amd64.deb ...
Unpacking libgdbm-compat4t64:amd64 (1.24-2) ...
Selecting previously unselected package libperl5.40:amd64.
Preparing to unpack .../4-libperl5.40_5.40.1-6+deb13u1_amd64.deb ...
Unpacking libperl5.40:amd64 (5.40.1-6+deb13u1) ...
Selecting previously unselected package perl.
Preparing to unpack .../5-perl_5.40.1-6+deb13u1_amd64.deb ...
Unpacking perl (5.40.1-6+deb13u1) ...
Selecting previously unselected package runit-helper.
Preparing to unpack .../6-runit-helper_2.16.4_all.deb ...
Unpacking runit-helper (2.16.4) ...
Selecting previously unselected package sysuser-helper.
Preparing to unpack .../7-sysuser-helper_1.6.0_all.deb ...
Unpacking sysuser-helper (1.6.0) ...
Selecting previously unselected package runit.
Preparing to unpack .../8-runit_2.2.0-3_amd64.deb ...
runit: setting up for runsvchdir
runit: current symlink succesfully created
Unpacking runit (2.2.0-3) ...
Selecting previously unselected package runit-run.
Preparing to unpack .../9-runit-run_2.2.0-3_all.deb ...
Unpacking runit-run (2.2.0-3) ...
Setting up runit-helper (2.16.4) ...
Setting up libgdbm6t64:amd64 (1.24-2) ...
Setting up libgdbm-compat4t64:amd64 (1.24-2) ...
Setting up perl-modules-5.40 (5.40.1-6+deb13u1) ...
Setting up netbase (6.5) ...
Setting up libperl5.40:amd64 (5.40.1-6+deb13u1) ...
Setting up perl (5.40.1-6+deb13u1) ...
Setting up sysuser-helper (1.6.0) ...
Setting up runit (2.2.0-3) ...
trigger action denied by policy-rc.d
trigger action denied by policy-rc.d
Use of uninitialized value $_[1] in string at /usr/sbin/minsysusers line 81.
runit: default-syslog: start action denied by policy-rc.d
Setting up runit-run (2.2.0-3) ...
Processing triggers for libc-bin (2.41-12+deb13u4) ...
+ grep _runit-log /etc/passwd
_runit-log:x:999:999:"runit svlogd user":/nonexistent:/sbin/nologin
+ echo OK: user _runit-log succesfully created
OK: user _runit-log succesfully created
+ apt-get -y remove runit
Reading package lists...
Building dependency tree...
Reading state information...
The following packages were automatically installed and are no longer required:
  runit-helper sysuser-helper
Use 'apt autoremove' to remove them.
The following packages will be REMOVED:
  runit runit-run
0 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.
After this operation, 617 kB disk space will be freed.
E: Can not write log (Is /dev/pts mounted?) - posix_openpt (19: No such device)
(Reading database ... 7336 files and directories currently installed.)
Removing runit-run (2.2.0-3) ...
Removing runit (2.2.0-3) ...
+ grep _runit-log /etc/passwd
_runit-log:x:999:999:"runit svlogd user":/nonexistent:/sbin/nologin
+ echo OK: user _runit-log succesfully created
OK: user _runit-log succesfully created
+ exit 0
=== RUN A exit code: 0 ===
--- post-run: user/group lookup ---
_runit-log:x:999:999:"runit svlogd user":/nonexistent:/sbin/nologin
_runit-log:x:999:
--- runit sysusers conf ---
--- dh_sysuser block inside runit postinst (generated by dh-sysuser 1.6.0) ---

############ STEP 5 — reset to a clean state before RUN B ############
remaining _runit-log refs:
none (clean)
runit 
runit-helper 2.16.4
sysuser-helper 1.6.0

############ STEP 6 — RUN B: substitute this repository's package artifacts into the Debian install path ############
--- substituted files (sha256 in chroot) ---
4f784baf53c26e565d09ae869469a7d5a1ccd4b4538ad23b2a56429fd97ab26a  /usr/sbin/minsysusers
ced2ecfdbf484f672d24e473a0b142a818bffb739ac84f1abe8c741bad9e3b40  /lib/sysuser-helper/sysuser-helper
6c0be2637e5b60ecdfe1f86c1416570f12321e05cc1e393c7739820fb6d4c0f2  /usr/bin/dh_sysuser
--- head of substituted /usr/sbin/minsysusers (ours) ---
#!/usr/bin/perl -w

# Copyright: 2024-2025 Lorenzo Puliti <plorenzo@disroot.org>
# License: BSD-3-clause

# minsysusers version: 0.2
=== RUN B: sh -x debian/tests/sysuser-helper (same upstream script, OHOS package runtime) ===
+ set -e
+ apt-get -y purge runit
Reading package lists...
Building dependency tree...
Reading state information...
Package 'runit' is not installed, so not removed
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
+ grep _runit-log /etc/passwd /etc/group
+ rc=0
+ apt-get -y install runit
Reading package lists...
Building dependency tree...
Reading state information...
The following additional packages will be installed:
  runit-run
Suggested packages:
  socklog ucspi-unix zsh runit-services xchpst
The following NEW packages will be installed:
  runit runit-run
0 upgraded, 2 newly installed, 0 to remove and 0 not upgraded.
Need to get 0 B/157 kB of archives.
After this operation, 617 kB of additional disk space will be used.
E: Can not write log (Is /dev/pts mounted?) - posix_openpt (19: No such device)
Selecting previously unselected package runit.
(Reading database ... 7221 files and directories currently installed.)
Preparing to unpack .../runit_2.2.0-3_amd64.deb ...
runit: setting up for runsvchdir
runit: current symlink succesfully created
Unpacking runit (2.2.0-3) ...
Selecting previously unselected package runit-run.
Preparing to unpack .../runit-run_2.2.0-3_all.deb ...
Unpacking runit-run (2.2.0-3) ...
Setting up runit (2.2.0-3) ...
trigger action denied by policy-rc.d
trigger action denied by policy-rc.d
Use of uninitialized value $_[1] in string at /usr/sbin/minsysusers line 81.
runit: default-syslog: start action denied by policy-rc.d
Setting up runit-run (2.2.0-3) ...
+ grep _runit-log /etc/passwd
_runit-log:x:999:999:"runit svlogd user":/nonexistent:/sbin/nologin
+ echo OK: user _runit-log succesfully created
OK: user _runit-log succesfully created
+ apt-get -y remove runit
Reading package lists...
Building dependency tree...
Reading state information...
The following packages will be REMOVED:
  runit runit-run
0 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.
After this operation, 617 kB disk space will be freed.
E: Can not write log (Is /dev/pts mounted?) - posix_openpt (19: No such device)
(Reading database ... 7336 files and directories currently installed.)
Removing runit-run (2.2.0-3) ...
Removing runit (2.2.0-3) ...
+ grep _runit-log /etc/passwd
_runit-log:x:999:999:"runit svlogd user":/nonexistent:/sbin/nologin
+ echo OK: user _runit-log succesfully created
OK: user _runit-log succesfully created
+ exit 0
=== RUN B exit code: 0 ===

############ STEP 7 — post-run verification for RUN B ############
--- substituted runtime files unchanged after dpkg install (must equal our package) ---
4f784baf53c26e565d09ae869469a7d5a1ccd4b4538ad23b2a56429fd97ab26a  /usr/sbin/minsysusers
ced2ecfdbf484f672d24e473a0b142a818bffb739ac84f1abe8c741bad9e3b40  /lib/sysuser-helper/sysuser-helper
--- user created? ---
_runit-log:x:999:999:"runit svlogd user":/nonexistent:/sbin/nologin

############ STEP 8 — SUMMARY ############
upstream test script : debian/tests/sysuser-helper (sha256 46ebb38784fd80d177951bed52f31acfabe0e32218425adf8042f21e3abdb076)
RUN A (stock Debian trixie runtime)      exit=0
RUN B (OpenHarmony package runtime)      exit=0
RESULT: upstream autopkgtest executed for real; 1 discovered / 1 executed / 1 passed (100%)
```

## 附录 B：runit 包中 `dh_sysuser` 生成片段 + 替换后校验

> 日志 sha256：`b3403d693612e9fdab9256c4a81a840ab5b5cc0b3b1d7e498d14f6ad0536b656`

```text
############ A. runit 2.2.0-3 (Debian trixie) postinst 中的 dh_sysuser 生成片段 ############
runit deb sha256: 12f60cd5e149cf89b0bf21960c7a73014b2ae34d7ee443bd31b23fbd94b985fd
--- /var/lib/dpkg/info/runit.postinst (control archive) ---
#!/bin/sh
set -e

case "$1" in
    configure|triggered)
	# what happens to this trigger when runit pkg is removed? maybe this
	# can be moved into runit-init and runit-run pkgs??
	if [ -z "${DPKG_ROOT:-}" ] ; then
		/lib/runit/trigger_sv setup
		/lib/runit/trigger_sv upgrade
	fi
    ;;
esac

# Automatically added by dh_sysuser/1.6.0
if [ "$1" = "configure" ] || [ "$1" = "abort-upgrade" ] || [ "$1" = "abort-deconfigure" ] || [ "$1" = "abort-remove" ] ; then
   if [ -x /usr/bin/systemd-sysusers ] && [ ! -e /etc/minsysusers.force ]; then
      systemd-sysusers ${DPKG_ROOT:+--root="$DPKG_ROOT"} runit.conf
   else
      /usr/sbin/minsysusers ${DPKG_ROOT:+--root="$DPKG_ROOT"} runit.conf
   fi
fi
# End automatically added section
# Automatically added by dh_runit/2.16.4
# Unlike postrm, I can be sure, that runit-helper is present on
# postinst.
#start: remove after trixie
if  [ ! -e /usr/lib/runit-helper/runit-helper ]; then
    #should not happen
    echo "warning: can't find runit-helper, postinst action skipped!"
    echo "warning: runit-helper: please report this bug"
fi
#end: remove after trixie
if [ -z "${DPKG_ROOT:-}" ] && [ -x /usr/lib/runit-helper/runit-helper ]; then
    NAME='default-syslog' ENABLE='yes' ONUPGRADE='nostop' /usr/lib/runit-helper/runit-helper postinst "$@"
fi
# End automatically added section
# Automatically added by dh_installdeb/13.24.2
dpkg-maintscript-helper rm_conffile /etc/sv/default-syslog/finish 2.1.2-60\~ -- "$@"
dpkg-maintscript-helper rm_conffile /etc/default/runit 2.1.2-60\~ -- "$@"
# End automatically added section


--- package dependencies ---
Package: runit
Version: 2.2.0-3
Depends: runit-helper (>= 2.14.0~), sysuser-helper (>= 1.6), libc6 (>= 2.34)

--- /usr/lib/sysusers.d/runit.conf in runit deb ---
u  _runit-log  -  "runit svlogd user"  /nonexistent

############ B. RUN B 之后 chroot 内的实际状态 ############
--- dpkg 安装的 sysuser-helper 版本（被本包产物替换） ---
runit-helper 2.16.4
sysuser-helper 1.6.0
--- 当前 /usr/sbin/minsysusers 是否为本包产物 ---
4f784baf53c26e565d09ae869469a7d5a1ccd4b4538ad23b2a56429fd97ab26a  /usr/sbin/minsysusers
本包 conan 产物 minsysusers sha256: 4f784baf53c26e565d09ae869469a7d5a1ccd4b4538ad23b2a56429fd97ab26a
--- /etc/passwd 中的 _runit-log ---
_runit-log:x:999:999:"runit svlogd user":/nonexistent:/sbin/nologin
--- /etc/group 中的 _runit-log ---
_runit-log:x:999:
```

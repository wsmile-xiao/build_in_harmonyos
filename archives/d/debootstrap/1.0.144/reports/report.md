# debootstrap 1.0.144 验证报告

> 本文所有结论均来自实际执行的命令输出。凡未真实执行的，一律标注「未执行」及
> 原因，不以推断代替实测。

## 1. 编译 / 打包

debootstrap 为纯 POSIX shell 工具，无编译步骤。打包动作 = 替换 `@VERSION@` + 安装
`bin/`、`share/debootstrap/{functions,scripts/}`、`share/man/man8/`。

```
$ conan create . -pr:h=ohos-aarch64-windows -pr:b=default
debootstrap 1.0.144: Calling build()
debootstrap 1.0.144: RUN: "…/sh.EXE" -c 'DEBOOTSTRAP_DIR="…/b" "…/debootstrap" --version'
debootstrap 1.0.144: debootstrap 1.0.144
debootstrap 1.0.144: Package 'debootstrap/1.0.144:6b129b068851896169fae42d399fa922d239ce8a' created
→ 退出码 0
```

## 2. 制品完整性：CRLF 缺陷（本次修复的真实 bug）

修复前 `build()` 用文本模式读写，在 Windows 打包机上产出 CRLF 的 shell 脚本：

```
$ file bin/debootstrap
bin/debootstrap: POSIX shell script, ASCII text executable, with CRLF line terminators
$ ./bin/debootstrap --version
/bin/sh^M: bad interpreter: No such file or directory      # rc=126
```

对照实验（同一文件，仅去掉 CR）：

```
$ tr -d '\r' < bin/debootstrap > /tmp/d && chmod +x /tmp/d && DEBOOTSTRAP_DIR=… /tmp/d --version
debootstrap 1.0.144                                        # rc=0
```

修复后重新打包的产物：

```
size=26312  CR=0  LF=905
```

原 `test.sh` 用 `sh <script>` 调用，**绕过 shebang**，因此永远看不到 `^M`，掩盖了该
缺陷。`test.sh` 已改为直接 exec 制品自身 shebang，并新增「全文无 CR」断言。

## 3. test_package（消费者视角，断言真实制品）

```
$ conan create . …            # 含 test_package 阶段
[debootstrap test] direct exec (uses packaged shebang, not 'sh <script>')
debootstrap 1.0.144
[debootstrap test] PASS
```

6 项断言全部落在已安装的真实制品上：

| # | 断言 | 反例可区分 |
|---|------|-----------|
| 1 | `bin/debootstrap` 存在 | — |
| 2 | 全文无 CR | CRLF 制品会 FAIL |
| 3 | shebang 为 `#!/bin/sh` 且**直接 exec** 成功 | CRLF 制品 rc=126 |
| 4 | `--version` 输出 `debootstrap 1.0.144` | — |
| 5 | `share/debootstrap/functions` 存在、`scripts/` 非空 | 缺文件/空目录会 FAIL |
| 6 | `DEBOOTSTRAP_DIR` 指向真实目录时 `--help` 成功；指向空目录时失败 | 实测 `rc=2` |

## 4. 上游 autopkgtest 套件（真实执行）

`build()` 通过 `test_package/run_upstream_tests.sh` 真实调用上游 `debian/tests/`。
用例清单与 `Restrictions` 由解析 `debian/tests/control` 得出，**未硬编码**：

```
discovered test cases from debian/tests/control:
  - debian-testing-minbase     | cmd='./debian/tests/debian-testing minbase'   | restrictions='allow-stderr, needs-root'
  - debian-testing-buildd      | cmd='./debian/tests/debian-testing buildd'    | restrictions='allow-stderr, needs-root'
  - debian-testing-default     | cmd='./debian/tests/debian-testing -'         | restrictions='allow-stderr, needs-root'
  - unsorted-packages-files    | cmd='./debian/tests/unsorted-packages-files' | restrictions='allow-stderr'
  - arch-all-support           | cmd='./debian/tests/arch-all-support'        | restrictions='allow-stderr'
```

### 4.1 参照机实测（Ubuntu 22.04 x86_64 / root，装齐 perl+flask+python3-debian+python3-apt）

前置条件探测全部通过 → 上游脚本被真实启动，`unsorted-packages-files` 实际进入
debootstrap 下载阶段：

```
/bin/sh /work/stage/debootstrap --download-only --variant minbase --no-check-sig \
    testing /tmp/tmp.oLBCEWkHwQ http://127.0.0.1:5000/debian/
wget … -O …/127.0.0.1:5000_debian_dists_testing_Release …/dists/testing/Release
```

但**未能跑完**，原因是上游 mitm 挂具自身：`out-of-order-mitm.py` /
`arch-all-mitm.py` 里的 `requests.get()` 未设 timeout。实测在受限网络下连接长期
ESTABLISHED 且收发队列均为 0 字节，而同期直连同一 URL 仅需 8s：

```
ESTAB 0 0 172.29.222.23:58172 151.101.90.132:80  users:(("flask",pid=83739,fd=5))
# 同期直连：
Release: HTTP 200 in 8.058873s
```

镜像抓取耗时实测（同一网络）：

| URL | 结果 |
|-----|------|
| `dists/testing/Release` | 200, 149KB, 8.6s |
| `dists/testing/main/binary-all/Packages.gz` | 首次 rc=124(>900s)，重试 200, 6.2MB, 45s |
| `dists/testing/main/binary-amd64/Packages.gz` | 200, 13.8MB, 25.3s |

因此 runner 为每个用例设 `UPSTREAM_TEST_TIMEOUT`（默认 1200s）上限，超时记
BLOCKED 并写明「无 verdict 的原因」，而不是把整个 CI 构建耗死。

### 4.2 OHOS CI Worker 实测

非 root（`USER=100`），且无 dpkg / perl / flask / python3-debian / python3-apt。
runner 逐条探测并记录真实缺失项（完整原始输出见 CI 构建日志）：

```
UPSTREAM_TEST_RESULT name=debian-testing-minbase   status=BLOCKED detail=needs root (id -u => …), debian/tests/control sets Restrictions: needs-root; missing perl module: Debian::DistroInfo; …
UPSTREAM_TEST_RESULT name=unsorted-packages-files  status=BLOCKED detail=missing executable: dpkg; missing executable: flask; missing python3 module: python3-debian
UPSTREAM_TEST_RESULT name=arch-all-support         status=BLOCKED detail=missing executable: dpkg; missing executable: flask; missing python3 module: python3-apt
```

### 4.3 判定不可伪造的验证

用真实上游用例名 + 可控退出码的桩脚本，验证 runner 的判定链路（**此为 runner 自测，
非 debootstrap 上游结果**）：

| 桩退出码 | runner 判定 | runner 退出码 |
|---------|------------|--------------|
| 0 | PASS | 0 |
| 1 | FAIL | 1 |
| 42 | FAIL | 1 |
| 用例名不在已知集合 | BLOCKED（`refusing to skip silently`） | 0 |

即：真实执行后失败的上游用例**不可能**被报成绿色，`conan build()` 会失败。
自测还暴露并修复了 runner 自身的两个缺陷：① 输出经 `sed` 管道导致 `rc=$?` 取到
`sed` 的退出码（会把真实失败变成假通过）；② 执行循环遍历硬编码用例名，导致上游
新增/改名的用例被静默跳过。

## 4.3b 消费者端到端用例（rule12，鸿蒙特有测试）

`test_package/consumer_e2e.sh`：真实消费者流程，不是纯断言——用打包产物真实执行
`debootstrap --download-only --no-check-sig --arch arm64 --variant=minbase sid T M`，
其中 M 是脚本现场构造的最小 **apt 格式** file:// 归档（Release + Packages +
pool 载荷，Size/SHA256 取自真实文件）。debootstrap 自己的代码完成全部工作：
Release 下载/套件校验 → pkgdetails(perl) 解析 required/base → download_debs 的
Size+SHA256 校验下载 → debpaths 输出。

实测输出（2026-09-28，Windows git-bash 驱动的 WSL Linux 环境，真实 1.0.144）：

```
I: Retrieving InRelease
I: Retrieving Release
I: Retrieving Packages
I: Validating Packages
I: Resolving dependencies of required packages...
I: Resolving dependencies of base packages...
I: Checking component main on file:///…/mirror…
I: Retrieving apt 2.9.10
I: Validating apt 2.9.10
I: Retrieving base-files 12.4
I: Validating base-files 12.4
[e2e] debpaths:
apt /var/cache/apt/archives/apt_2.9.10_arm64.deb
base-files /var/cache/apt/archives/base-files_12.4_arm64.deb
[e2e]   ok: …（debpaths 2 条目 / 2 个 .deb 落盘 / Release+Packages 索引）
[e2e] PASS        rc=0
```

已用两种 PATH 组合验证：有系统 wget 和无 wget（后者注入 fail-fast stub，验证
`file://` 下载全程走 `cp` 分支，stub 永不执行即证明未发生任何伪造的网络下载）。

## 5. 未执行项与原因

| 项 | 状态 | 原因 |
|----|------|------|
| 5 个上游 autopkgtest 用例在 OHOS CI 上取得 PASS | **未执行** | 前置条件在 Worker 上真实缺失（见 4.2），且 3 个用例 control 明确标注 `needs-root` |
| `debian-testing-*` 取得 PASS | **未执行** | `Restrictions: needs-root`；需 chroot/mknod/runuser/script + perl 模块 |
| 两个 mitm 用例在受限网络下跑完 | **未执行** | 上游挂具 `requests.get` 无 timeout，镜像连接 stall 时无限挂起（见 4.1 实测） |

以上均为如实记录的未执行项，不以「已适配」表述。

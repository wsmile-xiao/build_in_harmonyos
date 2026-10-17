# 上游测试用例证据 — jool-modules-lts 6.18.39（上游 Jool v4.1.14）

## 1. 计数口径

```console
$ find test -name '*.sh' | wc -l
36
```

上游无 `make check` / `ctest` / `pytest` 目标；`test/` 下 36 个 shell 脚本即全部
用例入口（与管理员实测 N=36 一致，无少报）。

## 2. 为什么 36/36 全部为内核态/root 前置（上游用例形态）

上游 Jool 的被测主体是 **Linux 内核模块**（`src/mod/{nat64,siit}/Makefile`：
`obj-m += jool.o` / `obj-m += jool_siit.o`，`src/mod/common/Kbuild`：
`obj-m += jool_common.o`，DKMS 打包见 `dkms.conf`）。全部 36 个脚本的执行
路径都要先让内核模块存在于运行中内核：

| 类别 | 数量 | 脚本 | 阻塞机制（源码可稽核） |
|---|---|---|---|
| 内核态单元测试 | 2 | `test/unit/test.sh`、`test/unit/pool4-iterations/full-test.sh` | 17 个测试工程编译为 `.ko` 后 `sudo insmod` + `sudo dmesg -C`（`test/unit/Makefile`：`obj-m += ...`） |
| graybox netns 报文注入 | 21 | `test/graybox/test-suite/**`（不含 autogen.sh） | `insmod .../graybox.ko`、`modprobe jool[_siit]`、`ip netns add/exec`、`sysctl -w`、`ip addr/link/route`（均需 root + 可加载模块的内核） |
| 多内核回归脚手架 | 6 | `test/jool-regression/*.sh` | `sudo make install`（装 `.ko` 到 `/lib/modules`）、`sudo sed` 改 `/etc/default/grub`、`. config` 脚手架依赖、`uname -r` 运行内核绑定 |
| netlink 分片 | 2 | `test/nl-fragmentation/{kern2usr,usr2kern}.sh` | `sudo modprobe [\-r] jool[_siit]` + 交互式 `read -p` 确认 + `dmesg` |
| 内核树编译检查 | 2 | `test/compilation_test/*.sh` | 需预编译 Linux 内核树（`prepare-kernels.sh` 自己构建 Linux 内核） |
| CLI 交互冒烟 | 1 | `test/client-test.sh` | 首语句 `if [[ $UID != 0 ]]` root 门禁；过门后 `modprobe` + 交互 `pause` |
| 非测试自举脚本 | 1 | `test/graybox/autogen.sh` | `autoreconf --install`（graybox 构建自举，无测试判定） |
| **合计** | **35+1=36** | | |

OHOS PC 侧适配框架为**非特权用户空间沙箱**（`USER=100`），无内核构建树
（`/lib/modules/$(uname -r)/build` 不存在）、无 root、无 `insmod`/`modprobe` 可用
内核。36 个脚本的前置条件在该平台**原理上不可满足**——这是**上游用例形态**
（被测对象为内核态组件），而非"缺依赖可补"或"环境配置问题"：不存在任何用户态
依赖补齐方式能让 `sudo insmod` 在 OHOS 沙箱内成立。

## 3. 真实执行证据（CI 中实际运行，非纸面推断）

两个脚本的首语句是非 root 门禁，可安全真实执行（不会产生任何副作用），
并以**预期方式**阻塞：

```console
$ bash test/client-test.sh
Please start the script as root or sudo.
$ echo $?
1

$ cd test/graybox/test-suite && bash run.sh
Please start the script as root or sudo.
$ echo $?
1
```

该执行由 `test_package/test_upstream_block_preconditions.sh` 的 B 部分在每次
CI 中强制复跑并断言（退出码 1 + 门禁提示文案）；若脚本行为变化（例如不再
门禁），断言立即失败。

OHOS worker 环境注记（CI #56279 实证）：worker 运行账户为超界 uid
（2002010133），系统 toybox `id -u` 对其报 `bad uid` 且无数值输出——而
`run.sh` 的门禁恰是未加引号的 `[ $(id -u) != 0 ]`，坏 `id` 下退化为
`[ != 0 ]`（unary operator expected）导致门禁失效、脚本跑到缺文件退出 127。
这是平台工具缺陷而非上游形态变化，故 B 部分在执行 `run.sh` 时于 PATH 前列
放置仅实现 `id -u` 的 shim（bash 内建 `EUID` = `geteuid(2)` 直读，任意 uid
下恒为真值）：门禁决策仍是 `run.sh` 自身做出的真实判断（非 root → 门禁照常
触发），断言语义不变；若上游删除门禁，脚本将继续执行并以 127 失败，审计
依然 fail-closed。本脚本自身的 root 自检同样改用 `EUID`。

## 4. 逐脚本 fail-closed 前置审计（CI 中实际运行）

其余 34 个脚本由同脚本 A 部分逐脚本校验：**每个脚本必须仍命中其阻塞模式串**
（固定字符串 grep，模式串清单见 `test_package/upstream-block-map.tsv`，全部
逐文件实测核对）。审计是 fail-closed 的：

- 模式串未命中 → 说明上游脚本形态可能已变为用户态可执行 → **审计失败**，
  强制重新评估该脚本是否应转为真实执行，而不是沿用「阻塞」旧结论；
- 快照中脚本缺失 → 审计失败（防止悄悄丢脚本）；
- 覆盖数 ≠ 36 → 审计失败。

因此「34 个未执行用例的阻塞原因」不是静态描述，而是每次 CI 都重新验证的
机器断言。

## 5. 结论（如实分层）

- **编译状态**：通过（用户态三件套 `jool`/`jool_siit`/`joold` 真实构建为
  aarch64 OHOS ELF；CI L0/L1 门禁实证）。
- **上游测试用例通过率**：**0/36**（36 个用例 0 个通过：2 个真实执行并以
  root 门禁阻塞、34 个经 fail-closed 前置审计确认内核态/root 阻塞；逐条
  技术原因见 `test_package/MANIFEST.yml` 与本文第 2 节）。
- **等价覆盖**：上游交付物中可在 OHOS 用户态真实运行的部分（三个 CLI/守护
  入口）由新增 118 个断言全覆盖（CLI 行为契约 + OHOS 交付契约 + 内核模块
  源码契约 + 阻塞前置审计），全部通过。
- **未声明通过**：内核模块构建/加载、NAT64/SIIT 转发功能、graybox 报文注入、
  17 个内核态单元测试——上述均为内核态能力，OHOS 侧不可验证，不在本包
  交付边界内（边界论证见 PR 描述与 notes.md）。

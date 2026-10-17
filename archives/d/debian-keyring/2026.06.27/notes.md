# debian-keyring 2026.06.27 适配笔记

## 概述

把 `debian-keyring`（Debian 维护者 / PGP 公钥环）适配为 HarmonyOS PC 的 Conan 纯数据包。
上游是 **jetring 形态**：每个密钥环一个目录（`<name>-pgp/`），**一个公钥一个文件**
（`0x<keyid>`，文件名即 keyid），由 `Makefile` 的 `cat <name>-pgp/0x* > output/keyrings/<name>.pgp`
拼接成可直接使用的密钥环。

## 上游形态

```
debian-keyring-2026.06.27/
├── debian-keyring-pgp/       947 个 0x* 公钥文件
├── debian-maintainers-pgp/   205
├── debian-nonupload-pgp/      44
├── debian-role-keys-pgp/       6
├── emeritus-keyring-pgp/     117（上游 debian/install 不安装）
├── keyids                    2992 行 0x<keyid> <name> 清单
├── scripts/ (19)  cheatsheets/ (14)  t/ (6)  runtests  Makefile  README  LICENSE
└── debian/ (含 install / rules / copyright)
```

## 安装内容（与上游 `debian/install` 完全一致）

```
share/keyrings/debian-keyring.pgp        947 个公钥包（32.3 MB）
share/keyrings/debian-nonupload.pgp       44
share/keyrings/debian-maintainers.pgp    205
share/keyrings/debian-role-keys.pgp        6
share/keyrings/sha512sums.txt            本包按其真实产物重算
share/doc/debian-keyring/{README,LICENSE}
licenses/copyright
```

## 为什么本包不需要 gpg（关键取舍）

上游 `Makefile` 的拼接规则是**纯字节拼接**：

```make
output/keyrings/%.pgp: %-pgp %-pgp/0x*
	cat $*-pgp/0x* > $@
```

配方直接复刻这条规则（按文件名排序拼接 `0x*`），**不需要 `gpg` 也不需要 `jetring`**；
需要 gpg 的只是"重新签发 / 校验"这类维护动作。这条取舍必须写清楚，
否则会被误认为"漏了构建步骤"。

## 上游测试情况（**N=6，全部不可执行**）

`t/` 下有 6 个用例：`at-least-2048.t`、`dm-vs-dd.t`、`keyids-complete.t`、`no-dupes.t`、
`no-expired.t`、`no-revoked.t`，由 `./runtests` 驱动（`Makefile` 的 `test` 目标）。
**6 个全部依赖宿主 `gpg`**（`gpg --no-default-keyring --keyring … --list-keys --with-colons`），
OpenHarmony 上没有 gpg，属"环境不具备"，不是"没有测试"，也不是静默跳过。
→ PR 正文按 `N=6` 声明，并给出上述具体技术原因。

## 新增自检（test_package/test_keyring.py，22 条断言）

| 断言组 | 条数 | 内容 |
|--------|------|------|
| 文件齐备 | 5 | 4 个密钥环 + `sha512sums.txt` 存在 |
| 包结构（每个密钥环 3 条 ×4） | 12 | 按 RFC 4880 逐个 packet 走完整个数据流（老格式头 1/2/4 字节或到末尾、新格式头 1/2/5 字节）；**公钥包（tag 6）个数 == jetring 源目录 `0x*` 文件数**（947/205/44/6）；首个包是公钥包且含 UID/签名包 |
| sha512 复核 | 2 | `sha512sums.txt` 恰好列出 4 个密钥环；每条摘要与真实产物一致 |
| 文档/许可/纯净性 | 3 | `share/doc/debian-keyring` 存在；`licenses/copyright` 已发布；未混入 `scripts/`、`cheatsheets/`、`t/`、`runtests` 等维护脚本 |

> "公钥包数 == 源文件数"这条最强：它把上游 `no-dupes`/`keyids-complete` 想守的
> "清单与内容一致"变成了可执行断言，而且不需要 gpg。

## 本地验证

```
$ python3 scripts/ohc-run.py conan-verify debian-keyring 2026.06.27
G0 PASS / G1 PASS / G2 PASS（干净 conan create + test_package 22/22）/ G3 PASS / G4 PASS
✅ 配方验证通过: debian-keyring 2026.06.27
$ python3 scripts/ohc/preflight.py . main HEAD
✓ preflight PF1-PF9+R52 全部通过
```

知识草稿：`knowledge/drafts/DRAFT-debian-keyring-2026.06.27-upstream-tests-need-gpg.{kv,md}`
（主题：上游测试依赖外部二进制时如实声明 N + 自解析做等价校验）。

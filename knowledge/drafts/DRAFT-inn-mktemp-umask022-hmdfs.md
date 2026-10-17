# DRAFT-inn-mktemp-umask022-hmdfs — HMDFS 上 configure 的 umask 077 + mktemp -d 修正

## 可复现症状与稳定错误签名

- `./config.status[1052]: can't create ./confXXXXXX/subs1.awk: Permission denied`
- `config.status: error: could not setup config files machinery`
- 稳定签名：`config\.status.*could not setup config files machinery`（与 E011 同族）；
  伴随出现的 `confXXXXXX` 目录已建出、但对其写入被拒。

## 根因与最小复现

HMDFS 是 **setgid 卷**，且磁盘属主（uid 20001006）与构建进程 uid（20020085）不一致。
autoconf 生成的 `config.status` 用 `umask 077 && mktemp -d "./confXXXXXX"` 建临时目录，
`umask 077` 下该目录实测为 `drwx--S---`（组/其他无任何权限），在此卷的跨 uid 语义下
**连创建者自己也写不进**。

最小复现（同一 hmdfs 目录、同一进程，唯一变量是 umask）：

| umask | mktemp -d 结果权限 | 写入 `$d/f` |
|---|---|---|
| `077` | `drwx--S---` | **FAILED**（Permission denied） |
| `022` | `drwxr-s--x` | OK |
| `002` | `drwxrws--x` | OK |

`mktemp` 的最终权限 = `0777 & ~umask`，因此**放宽 umask 确实生效**。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 原样 `umask 077 && mktemp -d` | Permission denied → config.status 退出（复现） |
| 删掉 umask（直接 `mktemp -d`，用环境 umask 002） | 通过 |
| 改 `umask 022` | 通过（adopted；与 a52dec 的 `0002-configure-umask-022.patch` 同款） |
| 以 root 运行 | 不适用：CI/conan 沙箱无 root/sudo |

## 与既有条目的关系（**重要**）

- `E011`（edit-umask-in-configure）已覆盖 umask 077 家族，本条是其 **mktemp -d 变体**的实测澄清。
- `DRAFT-6507-cln-mktemp-0700-hmdfs` 断言「mktemp -d 强制 0700，**umask 放宽无效**，须改 `mkdir -m 0777`」。
  本次在同卷上做了对照实验，结论相反：`umask 022 && mktemp -d` 得 `drwxr-s--x` 且**可写**。
  两者差异可能来自 mktemp 实现或当时的 SELinux 策略；本条以可复现的对照表为准，
  建议 promote 时与 DRAFT-6507 合并，把「先试 umask 022，仍失败再退 mkdir -m 0777」写成决策树。

## 最终方案、输入输出与真实验证

- **补丁**：`patches/0001-configure-umask-022.patch`（同时改主分支与 fallback 两处 `umask 077`）。
- **验证**：inn2/2.7.4 应用该补丁后，`conan-verify` G0/G1/G2/G3/G4 全 PASS，
  W3 本地 CI 模拟 PASS，`.staging-verified` 判 verified>0；
  消费者 test_package 34/34 断言通过。

## 注意事项

1. **两处都要改**：主分支 `tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` 与
   fallback `(umask 077 && mkdir "$tmp")`；只改一处，在 mktemp 不可用时仍会复现。
2. 先试 umask 放宽即可；**不要**一上来就重写为 `mkdir -m 0777`（除非对照实验证明
   本环境 umask 路径确实无效）。
3. 该问题与"源码是否被改动"无关，纯环境权限语义，故补丁应 `patch_type: portability`。

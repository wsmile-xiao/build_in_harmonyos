# DRAFT-transfuse-0.7.6-golden-file-nul-breaks-ci-pr-diff

## 一句话

把「工具原始输出」当期望文件提交进本仓库时，若内容含 NUL 字节，Git 判为二进制，
PR diff 变成 `GIT binary patch`，CI 的 `checkout-pr` 阶段三条 apply 路径全败，
整个构建在下载源码前就挂 —— 而机器人会按 URL 关键词把它**误判**成
「网络问题 / 源码下载超时」。

## 症状（build #66179，PR #14148）

机器人报的失败诊断：

```
**类别**: 网络问题
**问题**: 源码下载超时 (https://gitcode.com/.../pull/14148.diff)
```

真实日志（同一构建，被归错类）：

```
--- checkout-pr ---
... curl ... pr.diff ... && git apply --whitespace=nowarn pr.diff || git apply --3way ... || patch -p1 --fuzz=3 < pr.diff ...
eerror: missing binary patch data for 'archives/t/transfuse/0.7.6/test_package/data/test-ohos.expect'
eerror: binary patch does not apply to '.../test-ohos.expect'
epatch: Unknown option 'fuzz=3' (see "patch --help")
o[ERROR] PR 14148 diff 无法应用——PR 与 main 分支存在冲突
hprogram finished with exit code 1
```

注意 `checkout-pr ❌`，而 `git-clone ✅` —— 跟网络、跟源码都无关。

## 根因

CI 不直接 fetch PR 分支，而是 **curl 下载 `.diff` 再本地 apply**。Git 见到 NUL
就把文件判为二进制，`.diff` 里相应位置变成：

```
GIT binary patch
literal <N>
...
```

worker 取到的那份 diff 缺这段二进制载荷，于是：

| 兜底路径 | 结果 |
|---|---|
| `git apply --whitespace=nowarn pr.diff` | ✗ missing binary patch data |
| `git apply --3way --whitespace=nowarn pr.diff` | ✗ 同上 |
| `patch -p1 --fuzz=3 < pr.diff` | ✗ `Unknown option 'fuzz=3'` |

三条全败 ⇒ 报成「PR 与 main 存在冲突」，与真实原因（文件含 NUL）毫无关系。

## 为什么上游没暴露这个问题

transfuse 用 NUL 作块分隔符，上游 14 个 `.expect` 里 NUL 很多
（`extract-docx-apertium.expect` 89 个、`extract-html-apertium.expect` 76 个），
但它们**随源码 tarball 发布、不进 git**，所以从没触发。
本包第一次需要把一份期望输出当 fixture 提交进仓库，问题才暴露。

## 检测（提交前 30 秒自检）

```bash
python3 -c "d=open('<file>','rb').read(); print('NUL:', d.count(b'\x00'))"
git diff --cached --numstat <file>     # "- -" = 二进制(危险)，"17 0" = 文本(安全)
```

## 方案

期望文件入库前去掉 NUL，测试侧对实际输出做**同样的**归一化后再比对：

```bash
grep -aEv '^\[transfuse:' out.tmp \
  | grep -aEv '^<STREAMCMD:TRANSFUSE:' \
  | tr -d '\000' > out.txt
diff -u data/test-ohos.expect out.txt
```

归一化只影响块分隔符；被断言的内容（`[tf-block:N-<hash>]` 标识、`[[t:b:...]]`
内联标记、UTF-8 正文）逐字节保留 ⇒ 断言强度不变。修复后实测
`numstat` 由 `-  -` 变 `17 0`，本地 11/11 断言仍全过。

不便归一化时的替代方案：改用结构化断言（只 grep 关键标记），不提交全量期望文件。

## 边界

- 只影响**进 git 的**期望文件；留在 tarball 里的上游 `.expect` 不受影响；
- 任何含 NUL 的入库文件都会命中，不限于 `.expect`；
- 本条讲的是「PR diff 不可应用」，与 `L0o`（配方里禁止 curl/wget）是两回事。

## 证据

- PR #14148 / build #66179，worker `OpenHarmonyPCDeveloper-CI-033`
- 修复前：`python3 -c ... count(b"\x00")` = 5；`git diff --cached --numstat` = `-  -`
- 修复后：NUL = 0；`numstat` = `17 0`；`test.sh` 11/11 通过；L1e 反向验证仍失败
- 配方：`archives/t/transfuse/0.7.6/`，notes.md §3.3

## 判重说明

- E087 / E018 = HMDFS 权限与软链层，CI 另一层 ⇒ 不判重；
- 知识库无「golden 文件二进制导致 PR diff 不可应用」条目 ⇒ 申报。
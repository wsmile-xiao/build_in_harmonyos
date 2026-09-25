# btest-diff 硬编码 /tmp → 只读 /tmp 设备上整套 btest 恒判失败（E706 草稿）

> 状态：草稿（DRAFT，待人工审核）｜来源：paraglob 0.6.0 OHOS aarch64 适配（2026-09-24）｜severity: 2

## 问题

paraglob 0.6.0 的上游测试面是 Zeek btest 套件（`testing/driver/*` +
`testing/Baseline/*`，被测程序是本包安装的 `bin/paraglob-test`）。
在鸿蒙 PC 设备上首跑结果是**全红**：

```
driver.basic_matches ... failed
  % 'btest-diff out' failed unexpectedly (exit code 1)
  % cat .stderr
  .../bin/btest-diff: line 195: /tmp/test-diff.26381.out.tmp: Read-only file system
  .../bin/btest-diff: line 209: /tmp/test-diff.26381.out.baseline.tmp: Read-only file system
  .../bin/btest-diff: line 214: /tmp/test-diff.26381.out.baseline.tmp: Read-only file system
4 of 4 tests failed
```

看起来像「上游回归」，其实**比对一次都没执行**。

## 根因

`/tmp` 在本设备只读（`notes/device-facts.md` §一.1 同族）。`btest-diff`
把两处规范化输出硬编码到 `/tmp`：

| 行 | 原文 |
|---|---|
| 189 | `canon_output=/tmp/test-diff.$$.$canon.tmp` |
| 204 | `canon_baseline=/tmp/test-diff.$$.$canon.baseline.tmp` |

重定向失败 → `eval "$TEST_DIFF_CANONIFIER" ... >"$canon_output"` 返回非零 →
脚本打印 `TEST_DIFF_CANONIFIER failed` 并置 `result=1` → 用例判 failed。

这是「假红」：与 §一.1 描述的「假绿」互为镜像，共同点是**测量装置没工作**，
读数不可采信。判据：凡测试工具把中间产物写进硬编码临时目录，必须先拿到
「比对真实执行」的正面证据（`.diag` 里出现 `== Diff ==` 段）才能采信结果。

## 方案（先修测量装置，再读数）

任务私有副本，**不碰共享 conan 缓存、不碰上游源码与 Baseline**：

```sh
PRIV="$HOME/tmp/paraglob-0.6.0/btest-bin"; mkdir -p "$PRIV"
cp -f "$HOME/.conan2/p/btestc0d28dc74b727/p/bin/"* "$PRIV"/
# 只改两处硬编码 /tmp/ → ${TMPDIR:-/tmp}/
grep -n 'test-diff\$\$\.' "$PRIV/btest-diff"      # 改前 2 处
PATH="$PRIV:$PATH" btest -c testing/btest.cfg -d   # 私有副本置于 PATH 首位
```

实测：原 conan 缓存文件 sha256 保持
`7a9dd830b9a2ba571f185656081c0e2a944875432902a7f30c1b4c5320e9c61c` 未动；
私有副本改后 `7c89b988d6d555601b56cd3541ed35cd019eb5558e34103d352f0cc26e7d16f3`。
重跑后 3/4 通过，`.diag` 出现 `== Diff ==` 段（正面证据），
唯一失败转为真实归因（性能阈值，另见 E708）。

## 禁止的做法

1. **`btest -U` / `btest -u` 回填基线**：把设备读数固化成上游基线 = 篡改上游
   预期，真实回归会被一并抹平。
2. **直接改共享 conan 缓存里的 `btest-diff`**：污染同设备其他任务与后续轮次，
   也让「原文件未动」这条证据失效。改用任务私有副本。
3. **把 4/4 红直接写进测试结论**：装置未修时的读数不进四分项统计的 PASS/FAIL
   判定；装置修好后才按 TOTAL=PASS+FAIL+SKIP+NOT_RUN 逐项闭合。

## 复现命令（设备可直接执行）

```sh
. "$HOME/tmp/paraglob-0.6.0/env.sh"
PATH="$HOME/tmp/paraglob-0.6.0/btest-bin:$PATH" \
  btest -c "$HOME/ws/tmp/builds/paraglob-0.6.0.work/testing/btest.cfg" -d
```

证据：`$HOME/tmp/paraglob-0.6.0/w0/btest-run.log`。

## 关联

- 同族：`notes/device-facts.md` §一.1（runner 硬编码临时目录）、§一.27（HMDFS 可执行位）。
- 同包第二面：E708（`driver.time` 墙钟性能阈值骑设备边界）。

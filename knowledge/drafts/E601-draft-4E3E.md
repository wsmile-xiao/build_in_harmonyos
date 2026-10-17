# E601（草稿）— OHOS toybox diff 不支持 `-c`，上游测试脚本整组 FAIL

> 状态：草稿（`knowledge/drafts/E601-draft-4E3E.kv`），来源：pngmeta 1.11 的 CI 第 1 轮
> （PR #11609，构建 #57964）。

## 现象

配方在 `build()` 里执行上游 `make check`，CI（aarch64 原生构建机）上每个用例都立刻失败：

```
Testing uncompressed text chunk - tEXT (plain format)
diff: Unknown option 'c' (see "diff --help")
FAIL: test1
...
===================
4 of 4 tests failed
===================
make: *** [Makefile:331: check-am] Error 2
```

失败的是**比对工具**，不是被测程序——同一轮构建里，被测二进制已经在原生机上跑出了与期望文件一致的输出。

本地在 x86 交叉 runner 上验证时用的是 GNU diffutils，这个问题完全暴露不出来，只会在 CI 第一轮出现。

## 根因

鸿蒙 PC 的 `diff` 由 toybox 提供，只实现 unified 格式（`-u` / `-U N`），不认识 POSIX 的 context
格式选项 `-c` / `-C N`。老式 automake 项目的测试脚本常写成：

```sh
cd $dir && $here/prog -quiet $INPUT | diff -c $OUTPUT -
```

## 推荐做法

把测试脚本里的 `diff -c` 改为 `diff -u`（`-C N` 改为 `-U N`）：

- toybox 与 GNU diffutils 都支持，读 stdin 的 `-` 照常可用；
- 比对语义不变（相同退出 0、不同退出 1），只是失败时差异的展示格式从 context 变为 unified；
- 期望输出文件本身不用动。

用补丁固化（每个脚本一行），并在 PR 的「上游测试用例修改说明」里逐条登记。

仓库内可参考的同类写法：`archives/g/giflib/5.2.2/patches/0001-tests-makefile.patch` 的回归测试目标
使用 `... | diff -u giffixed.ico -`（该补丁针对的是 toybox `head` 不支持负数 `--bytes`，
`diff -u … -` 为上游原有写法）。

## 回退做法

只有当脚本依赖 context 格式的具体文本（极少见，例如把 diff 结果再交给别的工具解析）时，才考虑
`tool_requires` 已发布的 GNU diffutils，并让它在测试时先于 `/usr/bin` 出现在 PATH——做法同
`DRAFT-toybox-diff-e-ed-script`。

## 禁止做法

- **吞掉 `make check` 的失败**（`|| true`、`make -k check`、忽略退出码）：原因是比对工具不兼容，不是程序
  有 bug；吞掉等于整组上游用例空跑，PR 申报的上游通过率失实（R51）。
- **删除期望输出或清空 `TESTS`** 来让 `make check`「通过」：同上，属于把 skip 写成通过。

## 查重

- 正式条目中与 toybox 相关的是 E254（`patch --dry-run`）与 E402（`gzip` 长选项），都不是 `diff`。
- 草稿 `DRAFT-toybox-diff-e-ed-script` 讨论的是 `-e`（ed 脚本），处方是调整 PATH；它称 toybox diff
  "implements -u/-c style output"，本次 CI 日志表明 toybox diff **不接受** `-c`，该表述需以本条证据更正。
- 建议主编 promote 时考虑与该草稿合并为「toybox diff 选项覆盖」一条：`-u`/`-U` 可用，`-c`/`-C`、`-e` 不可用。

## 验证

```bash
# 找出命中的脚本
grep -rnE '\bdiff\s+-[a-zA-Z]*[cC]\b' <src>/test* <src>/tests <src>/Makefile.am
```

pngmeta 1.11 改为 `diff -u` 后，上游 4 项测试在本地 qemu-aarch64（静态链接）下 4/4 通过。

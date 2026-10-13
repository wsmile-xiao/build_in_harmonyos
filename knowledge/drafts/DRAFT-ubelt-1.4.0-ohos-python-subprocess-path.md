# DRAFT-ubelt-1.4.0-ohos-python-subprocess-path：OHOS CPython subprocess 裸命令名不可 spawn（`posix_spawnp` 无 PATH 查找）

> Contributor: lyl_ling | Status: Draft | Updated: 2026-10-04
> Source: ubelt 1.4.0 适配 HarmonyOS PC（上游 pytest 548 passed / 17 failed / 43 skipped）
> 对应：`knowledge/drafts/DRAFT-ubelt-1.4.0-ohos-python-subprocess-path.kv`

## 现象

在本平台（HarmonyOS PC，CPython 3.12.9）运行 Python 包上游测试时，凡是通过
`subprocess` 以**裸命令名**调用外部程序的用例成批失败：

```console
FAILED tests/test_cmd.py::test_cmd_stdout - FileNotFoundError: [Errno 2] No such file or directory: 'echo'
FAILED tests/test_cmd.py::test_cmd_with_list_of_pathlib - FileNotFoundError: [Errno 2] No such file or directory: 'ls'
FAILED ubelt/util_hash.py::hash_file:2 - FileNotFoundError: [Errno 2] No such file or directory: 'sha1sum'
```

关键线索：`echo`、`ls` 明明存在于 `/usr/bin`（`ls -la /usr/bin/ls` 可见），
`shutil.which('ls')` 也能解析到路径，但 `subprocess.run(['ls'])` 仍报 ENOENT。

## 根因

本平台的 `posix_spawnp`（`subprocess` 在 POSIX 上的默认实现路径）**不执行 PATH
目录查找**，只接受可解析为文件的路径。实测：

| 调用 | 结果 |
|------|------|
| `subprocess.run(['echo','hi'])` | ❌ `FileNotFoundError: [Errno 2] ... 'echo'` |
| `subprocess.run(['echo','hi'], env={PATH:'/usr/bin',...})` | ❌ 同样失败（PATH 无关） |
| `subprocess.run(['/usr/bin/echo','hi'])` | ✅ rc=0 |
| `subprocess.run(['/bin/toybox','echo','hi'])` | ✅ rc=0 |
| `subprocess.run('echo hi', shell=True)` | ✅ rc=0（由 shell 解析） |

即：问题不在 PATH 内容，而在 PATH 查找本身不可用。

## 影响

所有依赖 shell 命令 spawn 的 Python 包上游测试/doctest，在本平台都会出现
"环境性"失败。ubelt 1.4.0 的 17 项失败中 15 项属此类：

- `tests/test_cmd.py`（8 项）
- `ubelt/util_cmd.py` doctest（6 项：`__doc__:0`、`cmd:0/1/2/5/6`）
- `ubelt/util_hash.py::hash_file:2`（1 项，内部走 `ub.cmd(['sha1sum', ...])`）

这与被测库逻辑无关，属平台环境限制。

## 方案

1. **结论层面**：如实归类为平台环境限制，附可复现判定命令（见 `.kv` 的
   `verification_cmd`），不计入库缺陷。
2. **修复层面**：需要真实执行 shell 命令的场景，改用绝对路径
   （`shutil.which()` 取路径后传绝对路径）或 `shell=True`。
3. **禁止**：用 monkeypatch / 屏蔽 PATH / 伪造返回值把失败伪造成 PASS。

# 真实文件缓冲写入：传播提交失败并限定新建残件清理

配套 [KV 草稿](./DRAFT-xmlcatmgr-2.2-buffered-file-error-propagation.kv)。这是已合入 xmlcatmgr 2.2 适配的知识补交；草稿待维护者审核，不占用正式 E 编号。KV 的 `source_pr`、`source_commit` 指向原适配来源。

## 症状与条件

缓冲 stdio 的业务写函数返回值，不一定覆盖随后将缓冲内容提交到真实文件时的失败。输出目录可创建文件，也不能证明文件仍能增长。本例在独立子进程忽略 `SIGXFSZ`，设置 `RLIMIT_FSIZE=(0,0)`，使进程能够返回错误而非被信号终止。

原 HarmonyOS aarch64 消费者日志记录：

```text
xmlcatmgr: failed to flush `<catalog path>': File too large
```

`<catalog path>` 仅表示各命令实际使用的临时文件路径，不是原日志中的占位值。四条命令实际 stdout 为空、退出码为 1，均记录 `file_limit_zero=true`。

| 模式/操作 | 原始 argv（省略相同绝对 binary；路径用目录内文件名展示） | summary commands 下标 |
|---|---|---:|
| XML create | `-c "new catalog.cat" create` | 28 |
| XML add | `-c "existing catalog.cat" add public "write failure id" file.dtd` | 30 |
| SGML create | `-s -c "new catalog.cat" create` | 57 |
| SGML add | `-s -c "existing catalog.cat" add PUBLIC "write failure id" file.dtd` | 59 |

XML 临时目录尾名为 `xmlcatmgr-test-cmp62q18`，SGML 为 `xmlcatmgr-test-347v4btk`；原 argv 中 catalog 均为绝对路径。实际 binary 是 `/data/storage/el2/base/files/ohpc-xmlcatmgr-conan-006-jaEkjO/conan-home/p/b/xmlcabb19d47950608/p/bin/xmlcatmgr`。这些命令在已有两个 `write_failures` 场景内，不另加四个场景。

## 根因与修法

固定原版 `src/generic.c` 依据业务函数的 bool 判断成功，忽略部分关闭结果。stdio 缓冲完成点未纳入该判断，存在漏报的可能；这是固定源码推导，没有原版在相同目标故障输入下的 A/B 对照。

原适配补丁在解除锁之前显式检查 `fflush`，让失败保持在 `res` 中，后续释放资源不能把它改回成功。下列是既有 `FILE *f`、`catname` 和 `bool res` 上下文中的真实补丁片段，完整控制流见来源补丁：

```c
if (fflush(f) == EOF) {
    warn("failed to flush `%s'", catname);
    res = false;
}
```

关闭和解锁仍需按库的实际契约处理；本轮限额实验只直接覆盖 flush 错误传播，没有触发 `failed to close/lock/unlock` 分支。`main.c` 将最终 bool 映射为成功/失败退出码。日志未追踪每次业务写返回值、数字 errno 或内部缓冲状态，因此不将这些更细过程写成实测。

`generic_create` 用 `O_CREAT|O_EXCL` 排他创建，失败后调用 `generic_destroy`。消费者在故障 create 后实际断言 `not fresh.exists()`，XML/SGML 两场景均 PASS。这只覆盖本轮排他新建文件的残件清理，不证明外部进程并发替换路径时仍能安全清理。其他库须核自己的文件归属和并发契约。

`add` 的 `write_catalog` 先 truncate 再重写。补丁准确报告失败，未实现回滚；本次 add 未比较失败前后内容 hash。不能删除用户已有文件，也不能声称旧内容被保全。

## 使用示例与输入输出

输入：已适配的 xmlcatmgr 2.2 binary 的绝对路径；已具备 Python `resource`/`signal` 的目标 POSIX 环境。以下示例沿原消费者方法，仅操作自己创建的临时目录，不接受用户现有 catalog。它是复用方法说明，本次知识补交未执行新软件实验。

```python
import resource
import signal
import subprocess
import tempfile
from pathlib import Path

binary = Path("/absolute/path/to/xmlcatmgr")  # 替换为受测包 binary
assert binary.is_absolute() and binary.is_file()

def deny_file_growth():
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))

def call(mode, catalog, *action, limited=False):
    argv = [str(binary)] + (["-s"] if mode == "sgml" else [])
    argv += ["-c", str(catalog), *action]
    return subprocess.run(
        argv, capture_output=True, text=True, check=False, timeout=8,
        preexec_fn=deny_file_growth if limited else None,
    )

def require_flush_failure(result):
    assert result.returncode == 1  # 不接受负数的信号退出码
    assert result.stdout == ""
    assert "failed to flush" in result.stderr
    assert "File too large" in result.stderr

for mode in ("xml", "sgml"):
    with tempfile.TemporaryDirectory(prefix="xmlcatmgr-test-") as directory:
        fresh = Path(directory) / "new catalog.cat"
        require_flush_failure(call(mode, fresh, "create", limited=True))
        assert not fresh.exists()
        existing = Path(directory) / "existing catalog.cat"
        normal = call(mode, existing, "create")
        assert normal.returncode == 0 and normal.stderr == ""
        token = "public" if mode == "xml" else "PUBLIC"
        require_flush_failure(call(
            mode, existing, "add", token, "write failure id", "file.dtd",
            limited=True,
        ))
```

该方法用于单线程 POSIX 测试进程；`preexec_fn` 不作为多线程宿主的通用启动器。它只改变对应子进程的信号与限额，不改变父进程或系统配置。诊断字符串绑定原受测环境，其他版本或本地化环境须核对应诊断，不静默跳过。

预期输出契约为四次 rc=1/flush 诊断、两次正常 setup create rc=0/空 stderr，以及故障新建文件不存在。原 H1 summary 的 commands[29]/[58] 是同场景正常 create 反例，`file_limit_zero=false`、rc=0、stderr 为空；正常 XML/SGML add 也 rc=0/空 stderr。不能把 `RLIMIT_FSIZE`、正常配置文本或场景计数当错误签名。

## 已有验证与可追溯来源

- 原适配 [PR #12590](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12590) 已合入；原提交 `f05f94d2dcdcf87eab836f0ea79106e6b39110a0`、任务 #12149 已完成。本知识稿不改原适配代码或重报原积分。
- [固定来源包](https://distfiles.macports.org/xmlcatmgr/xmlcatmgr-2.2.tar.gz) SHA256 `ea1142b6aef40fbd624fc3e2130cf10cf081b5fa88e5229c92b8f515779d6fdc`；归档内原 `src/generic.c` SHA256 `60b07a9f9e81e356a35e7afbadc25ca14935760f1b21399fd2a445a3afe94025`。
- [修复补丁](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/f05f94d2dcdcf87eab836f0ea79106e6b39110a0/archives/x/xmlcatmgr/2.2/patches/0001-validate-errors-and-locking.patch) SHA256 `b04dc332c81cf688782df363904cdc2c37b1e570843788fb1aa67b197bce81f4`。
- [原消费者脚本](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/f05f94d2dcdcf87eab836f0ea79106e6b39110a0/archives/x/xmlcatmgr/2.2/test_package/functional.py) SHA256 `5cfdab2b995df9b01bf30e2612e2ff98ba52faf439d5a05fa2f6a0c22f707ee9`；`deny_file_growth`、`Runner.call`、`write_failures` 固定了注入、退出码和清理断言。
- 原 H1-006 `conan-functional/summary.json` SHA256 `1a94158c498d0f29ffc4fb59f421a1d22133e5866b62da47014ecc2cb06c78ff`：11/11 场景、failed=0、63 条命令。四条故障 stderr 都包含上述两个诊断；32 条 rc=0 成功命令中的这两个诊断出现 0 次。清理结论由实际消费者断言与场景 PASS 推得，summary 没有单独文件状态快照，原临时目录现已不可复查。
- 原 H1-006 运行日志 `conan-create.stderr` SHA256 `fcdc5f7b2c724736b8667870aff639bf5e8864754a4e9f6d1e84f6fae103e8f0`，记录执行上述脚本及 `11/11 scenarios passed; 63 commands recorded`。环境原件为 HarmonyOS aarch64、Clang target `aarch64-unknown-linux-ohos`，二进制为 AArch64。
- 原 A 当前提交官方 [CI #63805](https://ohpcd.atomgit.com/ci?id=73499) 实际 Conan/test_package 通过，11/11 场景、63 命令、1/1 包；原步骤日志 SHA256 `e5c84961ec91ed9391da1e7e7d94ea94649654c0e78f9a11c8634dafbfd742e1`。这属于原 A，不代替新知识 PR 的当前提交 CI 或检视。

原包无真实上游测试套件，空 `make check` 不计成功用例。上述 11 个场景是原适配补全消费者，本次新增软件测试为 0；知识解析/匹配校验另记，不与它们混加。原 H1-001 runner RC18（错误要求 baseline configure 必须非零）、历史 W3/finish RC1 保留为失败边界，均不由后续成功倒改为 PASS。

## 与当前近邻的差异

按主线 `1262b4ac24a3244f254c3e8163fa35d04b48f7fb` 的原文比较：

| 最近条目 | 已覆盖机制 | 本稿增量 |
|---|---|---|
| E244 | 有效 handle 生命周期内保存操作错误，open out-param 陈旧状态 | 将真实文件 stdio 完成点失败纳入 CLI 退出状态，并用独立子进程限额核报告路径 |
| E302 | `open_memstream` cookie 流 close/flush 能力探测或禁用 | 真实文件须完成输出或报告失败，不采用内存流能力开关 |
| E999-draft-C1N1 / [Issue #2873](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2873) | 内存流 close EBADF/丢缓冲，前置 fflush 后忽略 cookie close 错误 | 不忽略真实文件提交错误；区分信号终止与业务失败，并仅覆盖排他新建失败残件清理 |

不是以库名重复申报一般“提前 fflush”；新增点是确定性真实文件增长失败、CLI 错误传播和有限清理的证据链。近邻及定向 Issue/PR 已核，标题搜索不能证明全站无重复，最终纳入仍由维护者决定。

## 适用边界

可复用于具有同类缓冲输出与完成点判据遗漏的文件型 CLI，须先核目标库源码、文件归属、诊断和退出契约。本例实际配置为 `HAVE_LOCKF=1`；兼容锁及 warn/warnx fallback 仅源码存在，不称已测。

不支持 add 回滚、旧内容保全、原子提交、fsync/掉电持久化、所有写失败的安全清理或未触发 close/lock 错误路径的结论。不能由本例推定 OHOS libc 缺陷，也不能对现有 catalog 无条件 unlink。两个草稿尚未进入正式索引；解析和代表性匹配通过不等于知识已纳入或获分。

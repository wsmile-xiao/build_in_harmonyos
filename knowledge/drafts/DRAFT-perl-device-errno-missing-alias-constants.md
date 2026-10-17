# DRAFT-perl-device-errno-missing-alias-constants — OHOS 设备 perl 的 Errno 去重了同值别名常量（EWOULDBLOCK/ENOTSUP），依赖它们的上游测试会编译期失败——应 pin 预装 hnp perl

## 错误特征

```
"EWOULDBLOCK" is not exported by the Errno module
Can't continue after import errors at t/11adapter-file.t line 9.
BEGIN failed--compilation aborted at t/11adapter-file.t line 9.
```

在 `prove` 下的表现更具误导性（测试 0 个断言就死）：

```
t/11adapter-file.t        (Wstat: 65280 (exited 255) Tests: 0 Failed: 0)
  Non-zero exit status: 255
  Parse errors: No plan found in TAP output
Result: FAIL
```

## 触发条件

- 测试/脚本里有 `use Errno qw( EAGAIN EWOULDBLOCK )`（或 `ENOTSUP` 等别名）
- 解释器是 **OHOS 设备 perl**（`/storage/Users/currentUser/usr/local/bin/perl`，5.42.2）
- 阶段：testing —— **编译期**就失败，测试体一行都没跑

## 根因分析

OHOS 上并存两套 perl：

| 解释器 | 版本 | Errno 别名导出 |
|---|---|---|
| `/storage/Users/currentUser/usr/local/bin/perl`（设备 perl，随安装器部署） | 5.42.2 | ❌ 缺 `EWOULDBLOCK` / `ENOTSUP` |
| `/data/service/hnp/bin/perl`（系统预装） | 5.42.0 | ✅ 完整 |

设备 perl 的 `Errno.pm` 只保留 `EAGAIN => 11` 与 `EOPNOTSUPP`，把与它们
**同值**的 POSIX 别名 `EWOULDBLOCK`（同 11）、`ENOTSUP`（同 `EOPNOTSUPP`）
从 `%err` 里去掉了。而该模块的导出表是派生的：

```perl
our @EXPORT_OK = keys %err;      # → 别名不在导出表里
```

于是 `use Errno qw(EWOULDBLOCK)` 在 **BEGIN 阶段**报
`"EWOULDBLOCK" is not exported`，脚本直接编译失败。

**危害是「假失败」**：同一套上游测试在 hnp perl 下全过 —— Metrics-Any 0.10 实测：

| 解释器 | 结果 |
|---|---|
| 设备 perl 5.42.2 | `Files=14, Tests=73, Result: FAIL`（t/11adapter-file.t 编译失败） |
| hnp perl 5.42.0 | `Files=14, Tests=83, Result: PASS` |

复现命令：

```bash
/storage/Users/currentUser/usr/local/bin/perl -e 'use Errno qw(EWOULDBLOCK); print "ok\n"'
# → "EWOULDBLOCK" is not exported by the Errno module

/data/service/hnp/bin/perl      -e 'use Errno qw(EWOULDBLOCK); print "ok\n"'
# → ok
```

## Recommended Solution

### 主方案（priority 1）— `pin-interpreter`

配方与 test_package **统一 pin `/data/service/hnp/bin/perl`**（写绝对路径，
回退 PATH 上的 perl）：

```python
def _perl(self):
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    found = shutil.which("perl")
    if not found:
        raise ConanException("perl interpreter not found")
    return found
```

test_package 侧同样以该绝对路径 perl 驱动 `-I<site>`（绝对路径也顺带规避
conanrun 的 PATH 注入不覆盖子进程的问题）。

仓内先例：`perl-uri` 5.35、`perl-io-multiplex` 1.16 均写死 hnp perl 路径。

### 回退方案（priority 2）— `tool-requires-perl`

ohpcd 已发布 `perl/5.42.2.x` 制品，可改为 `tool_requires` 并 pin 其解释器路径，
摆脱对宿主预装 perl 的依赖。**但必须先验证该制品的 Errno 是否完整导出别名常量**
（设备 perl 正是不完整的那一套，若制品与其同源则问题依旧）。

### 禁止做法

- ❌ 修改/删除上游测试来迁就解释器缺陷（`sed -i` 改 `t/*.t`、删测试）—— 以掩盖换通过，违反 R51
- ❌ `use Errno ()` 空 import 或关警告把编译期失败按下去 —— 等于假装测试跑了
- ❌ 只把失败记成「平台限制」就放过 —— 这是**解释器选择**问题，换 hnp perl 即可真跑

## 单库实证（2026-09-18）

| 库 | 处理 | 结果 |
|---|---|---|
| metrics-any 0.10 | 配方与 test_package pin hnp perl 5.42.0 | `Files=14, Tests=83, Result: PASS`（t/11adapter-file.t 正常通过）；消费者 24/24 |

## 测试覆盖边界

- 本条只解释「设备 perl 与 hnp perl 在 Errno 别名导出上的能力差异」导致的**编译期假失败**。
- 若某包的上游测试**在 hnp perl 下也失败**，那才是真实的平台适配问题，不属本条。
- 更一般地，本条提示：**选解释器前先核对两套 perl 的能力差异**，不要默认
  PATH 上的 perl 与 CI 用的是同一个。

## 关联条目

- 相似：`E137`（OHOS perl ldflags 含 `-fstack-protector-strong` → XS 的 CBuilder 探测失败）、`E155`（纯 Perl + MakeMaker 需 `PERL5LIB` 补路径）
- 相关：`DRAFT-perl-module-build-makemaker-substitution`（同属「OHOS 上适配 CPAN 发行版」这一类）

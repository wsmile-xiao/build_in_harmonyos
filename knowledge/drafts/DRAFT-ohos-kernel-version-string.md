# DRAFT — OHOS `uname -r` 为 `HongMeng Kernel 1.12.0`：**无数字前缀**，按"首个数字段"解析版本号的代码会抛异常

> 触发事件：psutil 7.2.2 HarmonyOS PC 适配（PR #11263，2026-09-19 真机实测）
> 主从明确：**E036**（平台字符串含空格导致构建路径错误）为同族条目；本条是其**另一
> 触发面**——不是"空格进路径"，而是"**无数字前缀导致版本号解析失败**"。

## 现象

psutil 上游套件的版本解析工具函数直接抛错，导致依赖它的用例成片失败：

```text
ValueError: can't parse 'HongMeng Kernel 1.12.0'
  File ".../tests/__init__.py", line 645
```

上游代码（`tests/__init__.py:637-645`）按"**从字符串开头连续取数字与点**"的方式解析
内核版本：

```python
s = ""
uname = os.uname()[2]                 # = "HongMeng Kernel 1.12.0"
for c in uname:
    if c.isdigit() or c == '.':
        s += c
    else:
        break                          # ← 首字符 'H' 即 break，s 仍为空串
if not s:
    raise ValueError(f"can't parse {uname!r}")
```

## 根因（实测）

OHOS 的 `uname -r` 返回 **`HongMeng Kernel 1.12.0`** —— 版本数字（`1.12.0`）**不在
字符串开头**，前面有 `HongMeng Kernel ` 这段文字。Linux 上 `uname -r` 形如
`6.6.0-generic`（**以数字开头**），故上游"从头取数字"的解析法在 Linux 成立、在 OHOS
必然抛 `ValueError`。

```text
$ uname -r
HongMeng Kernel 1.12.0
$ python3 -c "import platform; print(platform.release())"
HongMeng Kernel 1.12.0
```

**与 E036 的区别（同族差异化）**：

| 条目 | 触发面 | 后果 |
|---|---|---|
| **E036** | `uname -r` **含空格**，Python `get_platform()` 把整串拼进路径 | 模块路径解析失败（`No module named '_sysconfigdata...'` 等） |
| **本条** | `uname -r` **不以数字开头**，解析方"从头取数字"得到空串 | `ValueError`，版本相关用例/分支全部失败 |

两者根因同源（`uname -r` 的非标准内容），但**失败机制与修法不同**：E036 修的是路径
拼接（跳过 release 字段 / 用 `ohos-aarch64` 标识），本条修的是**版本号提取**。

## 适用面

所有**解析内核版本号**的代码，在 OHOS 上都会踩到：

- 从 `os.uname()[2]` / `platform.release()` **按位置取数字**的解析器；
- 用 `split('.')` 后直接 `int()` 首段的代码（首段为 `HongMeng Kernel 1`，非纯数字）；
- 依赖版本比较决定分支的测试（本例 psutil 的 `test_boot_time` /
  `test_create_time` 等）。

## 推荐方案

1. **解析方健壮化**：不要假设版本号在开头——用**正则提取第一个数字段**，或从
   `platform.release()` 中 `re.search(r'\d+(\.\d+)+', s)`；
2. **测试侧如实归因**：受影响的版本分支类用例列入允许失败清单，并写明本条根因
   （本例即如此：psutil 的 `test_boot_time` / `test_create_time` /
   `test_create_time_monotonic` / `test_issue_687` /
   `test_meminfo_against_sysinfo` 均归入此类）；
3. 若必须拿到"Linux 式"版本串，可用 `platform.uname()` 的其它字段或读
   `/proc/version` 交叉判断（注意 `/proc` 受限面见 E031）。

## 禁止做法

- ❌ 不要为通过用例而**放宽上游断言**（如把 `assertAlmostEqual(diff, 3600)` 改松）——
  那是掩盖平台差异，且偏离上游。
- ❌ 不要假设"版本号总在开头"来写新的解析代码——OHOS 上不成立。
- ❌ 不要把本条与 E036 混为一条：同一根因、**不同失败机制**，合并会丢失可检索性
  （按 `ValueError: can't parse` 检索时应命中本条，按 `get_platform` 检索命中 E036）。

## 验证证据

- **主证据**：psutil 7.2.2（PR #11263）真机实测 —— `ValueError: can't parse
  'HongMeng Kernel 1.12.0'`，命中 `tests/__init__.py:645`；
  `uname -r` 实读 `HongMeng Kernel 1.12.0`。
- **交叉佐证（同族根因）**：`knowledge/doc/E236.md` 记录同一内核串
  （`HongMeng Kernel 1.12.0 aarch64`）导致的 ACPI 接口缺失；`E160.md` 的
  config.guess 因 `HongMeng Kernel` 报 `unable to guess system type` —— 均为同一
  "非标准 `uname -r`"根因的不同后果面。
- **环境**：HarmonyOS PC / aarch64 / CPython 3.12。

## 查重结论

- 对 `HongMeng Kernel` 检索：命中 `E036`（含空格→路径）、`E160`（config.guess 无法
  识别系统类型）、`E236`/`E237`（内核串伴随的 ACPI 接口缺失），另有 2 份
  draft/`.kv` 出现在 config 探测语境。**均未覆盖"从字符串开头取数字解析版本号 →
  空串 → ValueError"这一失败机制**（对 `can't parse` / `uname.*isdigit` 检索亦 0 命中）。
- 本条为 E036 同族**差异化**条目，E036 保持为根条目。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证外部无人提交过
  同主题草稿。

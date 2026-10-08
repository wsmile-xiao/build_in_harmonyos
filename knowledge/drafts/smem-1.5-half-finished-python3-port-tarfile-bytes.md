# 上游 tag 自称"已切 Python 3"但移植只做了一半：`tarfile` 的 `bytes` 泄漏给 `str` 逻辑
> Draft: `DRAFT-SMEM-15-HALF-FINISHED-PYTHON3-PORT`
> Stem: `smem-1.5-half-finished-python3-port-tarfile-bytes` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-SMEM-15-HALF-FINISHED-PYTHON3-PORT
- **严重性**: 2
- **类别**: portability|python|build-system|testing
- **触发工具**: python|python3|conan|test|runtime
- **阶段**: runtime|testing

## 错误特征

发行版把某个版本标记为"已切 Python 3"（Debian `Switch to python3`、Gentoo
`PYTHON_COMPAT` 收敛到 python3、OpenEmbedded 直接改 shebang），但源码只改了 shebang。
`--help` 全绿、`import` 成功，第一次真正解析数据时才炸：

```
$ python3 smem -S capture.tar -c 'pid pss'
  File "smem", line 118, in totalmem
    _totalmem = memory()['memtotal']
  File "smem", line 193, in memory
    m = f.match(l)
TypeError: cannot use a string pattern on a bytes-like object
```

同一根因还有两个**被裸 `except` 吞掉**的兄弟（实测于 python3.10）：

| 调用点 | 表达式 | 实测结果 | 可见症状 |
|---|---|---|---|
| `memory()` (smem:193) | `re.compile(r'(\S+):\s+(\d+) kB')` 匹配 `bytes` | `TypeError: cannot use a string pattern on a bytes-like object` | **唯一会冒泡成 traceback 的**（`showtable → totalmem → memory()`） |
| `pidmaps()` (smem:147) | `'-' in f[0]`，`f = l.split()` 产出 `bytes` | `TypeError: a bytes-like object is required, not 'str'` | 被 `processtotals()` 的裸 `except:` 吞掉 → **进程表整表为空**（只剩表头，不报错） |
| `pidcmd()` (smem:50) | `c.replace('\0', ' ')`，`c` 是 `bytes` | `TypeError: a bytes-like object is required, not 'str'` | 被同函数内的裸 `except:` 吞掉 → 进程名/命令行退化成 `'?'` |

即：**一个抛栈、两个静默**。静默那两个更危险——表格照常打印，只是内容全空或全是 `?`。
另外 `f[-1] == 'kB'` 对 `bytes` 恒为 `False`，所以即使不抛异常，PSS/RSS 列也永远填不上。

## 根因

`tarfile.extractfile().read()` / `.readlines()` 在 python3 返回 `bytes`，而消费方全按 `str` 写
（`str` 正则、`bytes` 与 `str` 字面量比较、`bytes.replace(str, str)`）。发行版的通行修法是
`sed` 换 shebang + 只给 `--source` 补一条补丁，于是"看似支持 python3"，实际数据通路全坏。

## 影响范围

- 所有"主体是单文件 Python 脚本、C 部分极小"的命令行工具（2008–2020 年的运维/诊断类工具尤甚）
- 判断口径：`conanfile.py` 的 `build()` 只编译一两个 `.c`、`package()` 把 `.py`/`.pl` 当脚本原样安装
- 一般化：**任何"上游只改了入口声明（shebang/元数据）、没改 I/O 边界语义"的移植**

## 推荐方案

**方法**: `decode-at-the-single-io-boundary-then-py3-audit`

1. 先 grep 出全部 I/O 边界：`tarfile` / `zipfile` / `os.popen` / `subprocess` / `open(..., 'rb')`。
   凡是把 `bytes` 直接交给上层解析的地方，在**边界处**统一 `decode('utf-8', 'replace')`；
   并让 `_readlines()` 从 `_read()` 派生，避免两个入口行为不一致（一处修好三个调用点）。
2. py3 语义普查：`xrange`/`map`/`has_key`/`iteritems`/`<>`、`print` 语句、`dict.keys()` 索引、
   整除、`sort(cmp)`、`except X, e`。逐项改成 py3 写法（smem 1.5 只剩一个 `xrange`）。
3. shebang 显式写 `python3`，与"只支持 python3"的版本定位对齐。
4. **验收不能停在 `--help`**：造一份能触发完整数据通路的输入（这里是按工具自有的归档格式
   合成一份采集归档），断言真实数值。否则 bytes 泄漏型缺陷会被 `--help` 全绿掩盖——
   三个兄弟里只有一个会抛栈，另两个是静默的。

## 验证命令

```bash
# 三个兄弟各自的实测症状
python3 -c "
import re
f = b'1000-2000 rw-p 0'.split()
for expr in ['memory', 'pidmaps', 'pidcmd']:
    try:
        if expr == 'memory': re.compile(r'(\S+):\s+(\d+) kB').match(b'MemTotal: 1 kB')
        elif expr == 'pidmaps': '-' in f[0]
        else: b'a\0b'.replace('\0', ' ')
        print(expr, 'no error')
    except TypeError as e: print(expr, '->', e)
"
# 完整通路：pristine 必崩，打补丁后同一归档必须 rc=0
python3 smem -S capture.tar -c 'pid pss'
```

## 取证记录

- 包：smem 1.5（`archives/s/smem/1.5`），上游 changeset `98273ce331bb`
- 补丁：`patches/0001-smem-python3-portability.patch`（3 个 hunk：shebang、`tardata` 解码、`xrange→range`）
- 实测环境：python 3.10.12；pristine rc=1（`smem:193` TypeError），打补丁后 rc=0 并正确输出 `1000 18 / 1001 8`
- 逐字证据：`archives/s/smem/1.5/notes.md`（问题 #1–#3，含 pristine/patched 两次实测输出）
  （`reports/` 被仓库 `.gitignore` 排除，审计报告只落本地工作树，不随 PR 提交）
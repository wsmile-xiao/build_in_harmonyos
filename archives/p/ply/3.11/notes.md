# ply 3.11 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译）
- **编译日期**: 2026-09-29
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 版本选择说明（重要）
- 本包**只适配 3.11**。上游另有 `2.4`/`2.5` 等历史版本，但：
  - **2.4 已被上游撤回**。上游 CHANGES 明确记载：
    > "The PLY-2.4 release was withdrawn due to a critical error."
  - **2.4/2.5 在 PyPI 无任何可下载文件**（实测 PyPI releases 为空列表），
    且 PyPI 上没有 `2.4.0` 这个版本号（只有 `2.4`）。
  - `www.dabeaz.com/ply/ply-2.4.tar.gz` 实测 **404**。
- 故 2.4 不具适配条件（无可获取的 https 官方源），经确认不纳入适配。
  若未来需要历史版本，上游指向
  `https://github.com/dabeaz/archive/tree/main/ply`（非 https 官方 sdist）。

## 包结构
sdist `ply-3.11.tar.gz`（159,130 bytes）解包后含：
`ply/`（包本体：lex.py、yacc.py、cpp.py 等）、`doc/`、`example/`、
`test/`（122 个 test*.py）、`setup.py`、`setup.cfg`、`MANIFEST.in`。

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/ply/3.11 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载 PyPI sdist，`tar -xzf --no-same-owner` 解包后
`cp -a` 把内容提到 source_folder 根。

**关键**：必须带 `--no-same-owner`。hmdfs 上归档记录的属主与构建 UID
不一致，不带该参数会因无法还原属主而报错（同 packaging/inn2 教训）。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `ply/` 到
`lib/python3.12/site-packages/ply`；`env_info.PYTHONPATH` 暴露导入路径。

### 3. 上游测试（build() 集成——R51 实测回填）
ply 的 `test/` **不是 pytest 风格**：`testlex.py` / `testyacc.py` / `testcpp.py`
是 **unittest 脚本**，文件名不匹配 pytest 默认 `test_*.py` 模式
（实测 `pytest test` → `no tests ran in 0.35s`）。故按上游方式直接执行脚本。

#### 最终实测：**88/88 = 100%**（2026-09-29，OHOS Python 3.12.9）

| 脚本 | 用例数 | 结果 | 通过 |
|---|---|---|---|
| `test/testlex.py` | 43 | `OK` | 43 |
| `test/testyacc.py` | 42 | `OK` | 42 |
| `test/testcpp.py` | 3 | `OK` | 3 |
| **合计** | **88** | — | **88（100%）** |

#### 提升过程：2/88 → 88/88（三处全是「运行方式」问题，**未改任何上游测试文件**）

初版配方按「从源码根直接跑脚本」的方式执行，得到 2/88。逐项定位后确认
**三处都不是 ply 的缺陷，而是运行方式/环境默认值问题**：

**(1) `assert_` 别名在 Python 3.12 被移除**（影响最大，86 项）
```
AttributeError: 'LexBuildOptionTests' object has no attribute 'assert_'
```
`assert_` 是 `unittest.TestCase.assertTrue` 的历史别名，
**Python 3.12 已将其移除**（本机实测 `hasattr(unittest.TestCase, 'assert_')`
为 `False`）。套件停留在旧 API（`self.assert_(` 出现 66 次于 testlex、
36 次于 testyacc）。
→ runner 内恢复该别名（`assert_ = assertTrue`，**语义等价、不放宽任何断言**）。

**(2) cwd 必须是 `test/`**（此前是**我方的调用错误**）
上游脚本假定自己在 `test/` 目录内运行：
- `test/lex_optimize.py` 做 `sys.path.insert(0, "..")`；
- 生成的 `lextab.py` / `parsetab.py` 相对**当前目录**写入。

从源码根运行时，`testlex` 的 optimize 系列用例因找不到生成的表文件而失败
（`assert os.path.exists("lextab.py")`）。
实测：从根运行 → `testlex errors=42`；从 `test/` 运行 + 别名 →
**`testlex 43 OK`、`testyacc 42 OK`**。

**(3) `multiprocessing` 起始方式**（testcpp 3 项）
`test/testcpp.py` 用 `multiprocessing.Process` 驱动检查，
**没有 `__main__` 守卫**（实测 `grep -c '__main__' testcpp.py` == 0），
依赖 **fork** 语义；而本平台 CPython 默认是 **spawn**
（实测 `multiprocessing.get_start_method()` == `'spawn'`），
spawn 下子进程会重新 import 模块 → 3 项报
`RuntimeError: Time limit exceeded!`。
→ runner 内 `set_start_method("fork")`（恢复 Linux 标准语义）后 **3 OK**。

#### 处置：runner 级兼容 shim（照 `cffi 2.1.1` / `pillow` 的 `sitecustomize` 先例）

配方在 `build()` 中写出 `ohc_ply_runner.py`（常量 `RUNNER_SHIM`），
以 `cwd=test/` 启动：
```bash
_cwd = <src>/test
python3 <src>/ohc_ply_runner.py testlex.py     # runner 施加 (1)(3)
python3 <src>/ohc_ply_runner.py testyacc.py
python3 <src>/ohc_ply_runner.py testcpp.py
```
**上游测试文件零改动**——既没有改断言、没有删用例、也没有放宽校验；
三处调整都在 runner 层面，恢复的是**该套件原本假定的运行环境**。

> 与「改测试让它变绿」的区别：改测试 = 动断言/删用例/加 skip；
> 本处 = 恢复 `assert_` 这个等价别名、用正确的 cwd、恢复 fork 语义
> ——断言强度与被测行为均未改变，故不构成 R51 意义上的「掩盖」。

另以**独立的 R34 消费者测试**（`test_package/test_ply.py`）作为第二证据链：
真实构建 lexer + LALR(1) parser 并求值 `2+3*4 == 14`，实跑通过。

### 4. test_package（消费者视角，R34）
`test_package/test_ply.py` 实跑通过：
```
ply 3.11
OK: ply lexer+parser evaluated 2 + 3 * 4 == 14
OK: ply module + real lexer/parser works
```
**踩坑（已修）**：该脚本最初用 `python -c "<code>"` 执行内层冒烟代码，
报 `TypeError: <module '__main__' ...> is a built-in module`。
根因：ply 的 `lex.lex()` / `yacc.yacc()` 通过 `inspect.getfile()` 定位
**调用者模块**来反射收集 `t_*` / `p_*` 规则；`-c` 下 `__main__` 是内建模块，
inspect 无法取文件。**改为写入临时脚本文件再执行**后通过。

## 注意事项
1. `ply` 上游已**不再以 pip 可安装包形式发布**（2018-12-22 起），
   故 PyPI 上最高只有 3.11；其 README 建议直接复制 `ply/` 目录使用。
   本包仍以 `python-require` 形式交付（与 packaging 同构），便于依赖管理。
2. 纯 Python 包不需要 `commands.json`（R38：库包误加反而会被拦）。
3. **调用测试必须落到真实脚本文件**（见上「踩坑」）——凡是被测库用
   `inspect` 反射调用方模块的（ply/某些 lexer 生成器），`python -c` 均不可用。

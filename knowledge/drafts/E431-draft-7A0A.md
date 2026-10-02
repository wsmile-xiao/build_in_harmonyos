# DRAFT E431 — 上游子包绝对导入 `from core.*` + `__init__` 未导出：整子系统不可导入

- **条目主题**：riscemu 2.2.7（及当前 master）的 `riscemu.priv` 子系统**完全不可导入**：
  子模块写的是顶层绝对导入 `from core.usermode_cpu import *`（应为 `from ..core...`），
  且 `priv/__main__.py` 的 `from riscemu import RunConfig` 在 `riscemu/__init__.py` 中并不存在。
  适配时不擅自打补丁，而是**如实记录不可用面**，并把「依赖可用性」的证明改走可达路径。
- **状态**：草稿（待知识库主编审核提升编号）
- **关联**：riscemu 2.2.7 适配（`archives/r/riscemu/2.2.7`）、E432（同批：测试接入）

## 症状

```bash
$ python3 -c "import riscemu.priv"
ImportError: cannot import name 'RunConfig' from 'riscemu'
    (/.../site-packages/riscemu/__init__.py)

$ python3 -m riscemu.priv --help
ModuleNotFoundError: No module named 'core'

$ python3 -c "import riscemu.priv.ElfLoader"
ModuleNotFoundError: No module named 'core'      # ElfLoader.py: from core.traps import *
```

三条路径（源码树、pip 安装后的 site-packages、上游 master）**全部复现**，与 OHOS 无关，
是长年遗留的上游缺陷。

## 根因

```python
# riscemu/priv/__main__.py:1
from riscemu import RunConfig            # ← riscemu/__init__.py 只有 __version__/__author__/__copyright__
# riscemu/priv/PrivCPU.py
from core.usermode_cpu import *          # ← 绝对导入，应为 from ..core.usermode_cpu
from core.traps import *
# riscemu/priv/ElfLoader.py:5
from core.traps import *                 # ← 同上
```

Python 3 下 `core` 不是顶层可导入名（它在 `riscemu.core` 下），且 `riscemu.priv` 未被任何
上游测试覆盖（上游 `test/` 与 `test/filecheck/` 都不触碰 priv），所以缺陷长期无人发现。

**连带影响**：唯一使用 `pyelftools` 的代码就在 `ElfLoader.parse()` 里，priv 不可导入意味着
该运行时依赖在上游代码中成为**不可达死代码**——不能靠「跑一遍上游功能」证明依赖可用。

## 处置（本次适配的选择）

1. **不打补丁**：不改 `from ..core`、不补齐 `__init__` 导出。保持产物与上游 tag 逐字节一致
   （可 sha256 复核），把缺陷留给上游修复；在 `notes.md` / `manifest.yaml` 的未覆盖项里显式记录。
2. **消费者测试回避 `riscemu.priv`**，改为验证可达面（CLI、decoder、指令集、Int/Float 语义等）。
3. **依赖可用性改走可达路径证明**：直接驱动 `pyelftools` 解析真实 ELF：

```python
from elftools.elf.elffile import ELFFile
with open(sys.executable, "rb") as fh:            # 或 /proc/self/exe
    elf = ELFFile(fh)
    assert elf.elfclass in (32, 64)
    assert elf.header["e_machine"]                 # EM_*
    assert len(list(elf.iter_sections())) > 0
assert elftools.__version__ == "0.30"              # 与 pyproject 的 ^0.30 对齐
```

## 验证

```bash
$ python3 -c "import riscemu.priv"                      # 期望 ImportError（如实记录）
$ python3 -c "from riscemu.riscemu_main import RiscemuMain; print('ok')"   # 可达面正常
$ python3 -c "from elftools.elf.elffile import ELFFile; f=ELFFile(open('/proc/self/exe','rb')); print(f.elfclass)"
```

## 禁止做法

- ❌ 为了让测试全绿而给上游打补丁（`from core.` → `from ..core.`、补 `RunConfig` 导出）：
  产物偏离上游、上游修复后形成分叉。
- ❌ 因为「不可导入」就删掉 `pyelftools` 依赖或伪声明：依赖仍是上游运行时声明，
  且本仓 pytest 用例（`test_isa.py` 等）与 wheel 元数据都要求它存在。
- ❌ 用 `try/except ImportError: pass` 把 `riscemu.priv` 静默跳过后再宣称「priv 已验证」。

## 查重关键词

绝对导入、`from core import`、包内相对导入、`__init__` 未导出、`RunConfig`、
`python -m <pkg>.priv`、上游缺陷（master 同样未修）、死代码依赖、pyelftools 不可达、
不擅自打补丁、未覆盖项记录

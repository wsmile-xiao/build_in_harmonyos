# DRAFT：Windows Python 控制台 GBK 编码打印 emoji/中文崩溃（ohc-run.py 子命令假失败）

> Draft（未 promote）— 来源于 xfpt 1.00 本机预检（2026-09-29）
> 对应 `.kv` 文件同 stem：`DRAFT-windows-python-gbk-console-emoji-crash.kv`

## 症状

Windows 工作站跑本机门禁模拟命令：

```powershell
python scripts\ohc-run.py prescan <源码目录>
```

在收尾打印处崩溃，exit code 1：

```
File "scripts/ohc/pre_scan.py", line 602, in main
    print(f"  {emoji_map.get(level, '\u2753')} {level}: {count} 项")
UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f7e1' in position 2: illegal multibyte sequence
```

lang-preflight 也可能出现同类 stderr（PowerShell 把 python 的 stderr 行包装成
NativeCommandError），实际正文是"✅ 语言匹配: task=cpp, detected=c"。

## 根因

- Windows Python 的 `sys.stdout` 编码跟控制台 locale 走，中文系统默认 GBK；
- ohc-run.py 输出含 emoji（🟡✅❌）与中文，GBK 无法编码 → **打印阶段**抛
  UnicodeEncodeError；
- 关键误导：**实际工作往往已完成**——prescan 崩溃前已把报告写入
  `<src>/.pre-scan-report.yaml`；lang-preflight 崩溃前已完成判定。
  exit code 非零 ≠ 预检失败。

## 方案

1. 会话开头统一预设再调工具：

```powershell
$env:PYTHONIOENCODING='utf-8'
```

2. 崩溃后**先查目标产物是否已生成**再决定重跑：
   - prescan → `<src>/.pre-scan-report.yaml`
   - result 草稿 → result.json
3. 同族问题：`json.load(open(f))` 读含中文的 UTF-8 文件（如 commands.json）
   报 GBK 解码错误 → 显式 `open(f, encoding='utf-8')`（Windows Python
   默认 open 编码也是 GBK）。

## 复用面

所有在 Windows 工作站上直接驱动 `scripts/ohc-run.py`（lang-preflight /
prescan / conan-verify / finish / result / feedback）或读仓库 UTF-8
产物的协作者。

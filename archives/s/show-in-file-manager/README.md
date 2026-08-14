# show-in-file-manager

**Show in File Manager** — 打开系统文件管理器并在其中选中指定文件/目录的
跨平台 Python 工具包。其核心不是"打开"文件，而是在文件管理器中"选中"
它们（highlight），便于用户快速定位。

- Homepage: https://github.com/damonlynch/showinfilemanager
- License: MIT
- 纯 Python 包（Python 3.6+，setuptools / PEP 517），无 C 扩展、无编译
- 提供 Python 模块 `showinfm` 与命令行工具 `showinfilemanager`
- 用法:
  - `python3 -c "from showinfm import show_in_file_manager; show_in_file_manager('/path/to/file')"`
  - `showinfilemanager file1.txt file2.txt`

## Version

- 1.1.4 (built)

## Dependencies

- python3（解释器）
- packaging（运行时，linux.py 无条件导入）
- pyxdg（可选导入，try/except ImportError）
- pywin32（仅 Windows，本归档不涉及）

## OHOS Adaptation

- 纯 Python 项目，无 C/C++ 编译，无 ELF 签名需求
- 平台补丁 0001：`platform.system()` 在 HarmonyOS 上返回 "HarmonyOS"，
  上游仅识别 Windows/Linux/Darwin 会抛 NotImplementedError，按 Linux 处理
- 平台补丁 0002：HarmonyOS 上 /proc/version 不可读（Permission denied），
  detect_wsl()/wsl_version() 捕获 OSError
- 安装方法: 模块树铺到 lib/python3.12/site-packages/showinfm/ +
  bin/showinfilemanager 入口脚本（等价 console script）

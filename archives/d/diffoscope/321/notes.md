# diffoscope 321 — 适配笔记

## 平台
- 目标: OpenHarmony (aarch64)
- 构建系统: pip (Python)

## 编译步骤
1. pip install diffoscope (源码安装)
2. 安装依赖: libmagic (file 5.46), libarchive (3.8.7)
3. 打补丁: logging.py curses 导入降级

## 产物
- diffoscope 命令 (Python 脚本)

## 已知限制
- Python curses 模块缺失 (已降级处理)
- 依赖 libmagic, libarchive 等 C 库

# astroterm

## 简介
astroterm 是一个基于终端的星图程序，用 C 语言编写。它可以在终端中显示恒星、行星和星座的实时位置，使用 ASCII 渲染精确可视化。

## OHOS 适配
- OHOS SDK 的 fortify/string.h 头文件需要 size_t 在包含前已定义
- 需要在 <string.h> 之前添加 #include <stddef.h>
- toybox 的 xxd 不支持 -i 选项，需要使用 Python 替代脚本生成嵌入式头文件

## 依赖
- argtable3 >= 3.0 (命令行参数解析)
- ncurses >= 6.0 (终端界面)
- math library

## 功能验证
```bash
astroterm --version
astroterm --help
```

## 参考
- GitHub: https://github.com/da-luce/astroterm

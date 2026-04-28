# boxes — OpenHarmony 编译档案

## 软件简介
boxes 是命令行 ASCII 框绘制/移除工具，可自定义框样式。

## OHOS 适配要点
- 自定义 Makefile，需修改 CC 变量允许环境覆盖
- 依赖 libunistring 和 PCRE2 需在 vendor 目录编译
- ncurses 使用 stub 函数绕过（configure 在 OHOS 上不兼容）
- 终端列数/行数固定为 80/24

## 依赖关系
- libunistring 1.0
- PCRE2 10.40
- ncurses: stub（绕过）

## 参考资料
- [boxes 官方](https://boxes.thomasjensen.com/)
- [boxes GitHub](https://github.com/ascii-boxes/boxes)

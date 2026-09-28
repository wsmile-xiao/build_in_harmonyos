# sent

`sent` 是 suckless 社区出品的极简 X11 演示文稿工具：不用 LaTeX、不用 LibreOffice，
直接读纯文本，**每个段落就是一页幻灯片**，也可以插图片。

上游首页：<https://tools.suckless.org/sent/>

## 用法

```
sent [-v] [file]
```

- `-v`：打印版本后退出（实现里写到 stderr，尽管 `sent.1` 手册页声称是 stdout）
- 不给 `file` 或给 `-`：从标准输入读演示文稿
- 翻页：鼠标左键/滚轮，或 `→ ↓ 空格 l j n Enter`；反向用 `← ↑ h k p Backspace`
- `r` 重新加载（仅文件输入有效），`q`/`Esc` 退出

输入行里以 `@` 开头表示插入指向该文件名的图片，`#` 开头表示注释行，`\` 开头表示
按字面输出后续字符。

## 打包说明

本包用上游裸 `Makefile` + `config.mk` 构建（没有 configure，也没有 CMake），
依赖通过 Conan 声明；细节见 `1/notes.md`。运行需要一个 X11 display。

# libthai

泰文语言支持库：**断词**、断行与字符分类。

泰文书写时词与词之间不留空格，程序要正确换行、选中词、做全文检索，都得先知道
一串泰文该在哪里断开。libthai 用词典（由 libdatrie 的双数组 Trie 构建）完成这件事。

- 上游：https://github.com/tlwg/libthai
- 许可证：LGPL-2.1-only
- 鸿蒙 PC 适配版本：见各版本目录

## 依赖

- `libdatrie`：既是链接依赖，也是**构建期工具依赖**——`configure.ac` 通过
  `AC_CHECK_PROGS(TRIETOOL, [trietool-0.2 trietool])` 找它 `bin/` 下的可执行文件来生成词典。

## 词典路径

词典装在包内 `share/libthai/`，配方以 `runenv_info` 声明 `LIBTHAI_DICTDIR`，
消费方无需硬编码路径。

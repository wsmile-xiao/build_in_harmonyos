# Yodl

Yodl 是一个文档预处理器，可将 Yodl 源文件转换为 HTML、LaTeX、man、纯文本和 XML。

## 功能

- `yodl` 处理 Yodl 文档源文件。
- `yodl2html`、`yodl2latex`、`yodl2man`、`yodl2txt` 和 `yodl2xml` 提供常用格式转换入口。
- `yodlverbinsert` 将输入文件内容转换为 Yodl verbatim 内容。

## HarmonyOS PC 适配

Yodl 4.05.01 使用 CMake 直接构建上游 C/C++ 源码，不需要 icmake。程序、转换脚本和宏数据都安装在 Conan 包的私有目录中。适配补丁让宏生成与转换脚本通过 `/usr/bin/env` 查找 HNP 提供的 Bash 和 Perl。

## 依赖

运行时不依赖其他 Conan 包。构建使用 HarmonyOS HNP 的 Clang/Clang++、CMake、Bash 和 Perl。

## 参考

- 官网：https://fbb-git.gitlab.io/yodl/
- 上游源码：https://gitlab.com/fbb-git/yodl

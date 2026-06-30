# halibut

文档制作系统，由 Simon Tatham（PuTTY 作者）开发。

Halibut 是一个文档制作工具，接受单一输入文件（.but 格式），可输出多种文档格式：
纯文本、HTML/XHTML、Windows HTML Help、Man 页面、GNU Info、PostScript 和 PDF。

## 链接
- 主页: https://www.chiark.greenend.org.uk/~sgtatham/halibut/
- 源码: https://www.chiark.greenend.org.uk/~sgtatham/halibut/halibut-1.3/halibut-1.3.tar.gz

## 许可证
MIT License — 允许自由使用、修改、分发

## 可用版本
| 版本 | 状态 | 构建系统 | 备注 |
|------|------|---------|------|
| 1.3 | published | cmake | 需要 CMAKE_POLICY_VERSION_MINIMUM=3.5 以兼容 CMake 4.x |

## 功能概述
- 6 种输出格式：text, html, man, info, ps, pdf
- 支持多字符集（ASCII, ISO-8859-1~16, UTF-8, CP437/850/852 等）
- 支持宏定义、索引、目录、交叉引用
- Unicode 完整支持
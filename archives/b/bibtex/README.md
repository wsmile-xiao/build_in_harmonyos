# BibTeX — OpenHarmony 编译档案

## 软件简介
BibTeX 是 TeX/LaTeX 的参考文献处理器，读取 .aux 文件、.bib 文献数据库和 .bst 样式文件，生成 .bbl 输出供 LaTeX 使用。

## 功能概述
- 处理 .aux 文件中的 \citation 和 \bibstyle 命令
- 从 .bib 数据库中检索文献条目
- 按 .bst 样式文件格式化输出
- 生成 .bbl 文件供 LaTeX 二次编译

## OHOS 适配要点
- 修改 config.guess 添加 HarmonyOS (__OHOS__) LIBC 检测和系统识别
- HMDFS 上 mktemp -d 不支持，configure 脚本改用 mkdir 创建临时目录
- 三层 configure 构建: kpathsea → web2c → web2c/web2c
- 编译器环境由 Conan AutotoolsToolchain 从 profile 获取（R33 合规）
- 无 --build/--host 参数，config.guess 补丁处理平台检测（R15 合规）
- 无 runtime 修改生成文件，全部固化为补丁（R6 合规）

## 依赖关系
- 无外部 Conan 依赖
- kpathsea 库内嵌于 TeX Live 源码树（in-tree 构建）

## 参考资料
- [BibTeX 官方文档](https://tug.org/bibtex/)
- [TeX Live 源码](https://github.com/TeX-Live/texlive-source)

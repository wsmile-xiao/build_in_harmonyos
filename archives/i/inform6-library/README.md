# inform6-library — OpenHarmony 编译档案

## 软件简介
inform6-library（inform6lib）是 Inform 6 交互式小说语言的标准库：一组被游戏
源码 `Include` 的 Inform 语言头文件（`english.h`、`parser.h`、`verblib.h`、
`grammar.h` 等 8 个），提供解析器、语法、动词库等核心基础设施。本档案对应
6.12.6 版（2022-02 发布）。**纯文本数据包**：无编译、无链接（Debian/Ubuntu
亦以 `all` 架构数据包分发，安装到 `/usr/share/inform6/library/`）。
许可证为 Artistic License 2.0。

## OHOS 适配要点
- 纯数据包（kicad-demos 同款范式）：`build()` 仅做防漂移清单校验，
  `package()` 将全部 14 个文件（8 个 `.h` + 6 个文档/许可证）复制到
  `share/inform6/library/`，`package_id` 清空
- 与编译器包 `inform6/6.44-r7`（自带 6.12.8 库，装于 `share/inform6/std/`）
  互不冲突：本包装于 `share/inform6/library/`，路径独立
- 消费者（inform6 编译器）经命令行 `+目录` 参数或源内 `+include_path`
  指向本目录使用

## 依赖关系
- 无编译/运行依赖（纯数据）
- 被依赖: 无（由 inform6 编译器运行时按路径消费，非 conan 依赖）

## 参考资料
- [IF Archive: inform6 library](https://ifarchive.org/indexes/if-archive/infocom/compilers/inform6/library/)
- [Debian inform6-library 源码包](https://packages.debian.org/source/trixie/inform6-library)

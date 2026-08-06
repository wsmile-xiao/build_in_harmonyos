# Aiksaurus

Aiksaurus 是一个英文同义词库（thesaurus）库与工具集。核心为 C++ 库
`libAiksaurus`，附带两个命令行前端（`aiksaurus` 与 `caiksaurus`）以及
基于词典数据（`words.dat` / `meanings.dat`）的查询引擎。
历史上是 AbiWord 文字处理器的拼写/同义词依赖组件。

## 功能概述

- C++ 同义词查询库：`Aiksaurus::find(word)` + `Aiksaurus::next()` 遍历各义项及同义词
- C 接口：`AiksaurusC.h`（`aiksaurus_c_*` 系列）
- 命令行工具：
  - `aiksaurus <word>` — 查询并打印各义项同义词
  - `caiksaurus <word>` — C 接口版本的命令行前端
- 随包发布词典数据 `words.dat` / `meanings.dat`（约 0.5MB），运行时定位到 `share/aiksaurus/`

## OHOS 适配

- **config.guess/config.sub 升级**：上游 2004 版无法识别 HarmonyOS（E007），
  替换为 GNU 官方 2023-08-22 版，识别三元组 `aarch64-unknown-linux-ohos`。
- **umask 077 修复**：configure 生成的 config.status 用 `umask 077` 创建临时目录，
  在 HMDFS 文件系统上目录 owner 不可写，移除 `umask 077` 解决（E046 模式）。
- **GTK+ 前端禁用**：`--with-gtk=no`，不依赖 gtk+-2.0。
- **仅 shared 构建**：configure.ac 含 `AC_DISABLE_STATIC`，不支持静态库；
  aiksaurus 不是系统同名库，动态链接不违反 R26。
- **已知限制**：上游 `AC_CHECK_FUNC(getenv)` 未配 AC_DEFINE，导致 `config.h`
  缺少 `HAVE_GETENV`，`AIK_DATA_DIR` 环境变量覆盖词典路径不生效
  （默认编译期路径 `share/aiksaurus/` 正常）。如需覆盖，可用
  `Aiksaurus(meanings_path, words_path)` 构造传入显式路径。

## 依赖关系

- 编译依赖：无（仅 autotools + C++ 标准库）
- 运行依赖：libc++ / libc（OHOS 系统提供）
- 上游仓库：<https://github.com/AbiWord/aiksaurus>（官方发布经 Debian 源镜像）

## 参考资料

- 官网：<http://aiksaurus.sourceforge.net/>
- 上游源码：<https://github.com/AbiWord/aiksaurus>
- 版本归档：<https://deb.debian.org/debian/pool/main/a/aiksaurus/>

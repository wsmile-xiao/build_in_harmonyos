# daps

daps（DocBook Authoring and Publishing Suite）是 SUSE 出品的 DocBook 文档发布
工具套件，上游仓库为 <https://github.com/openSUSE/daps>。源码主体为 bash
脚本套件（`bin/daps` 主程序 + `lib/` 下 bash 函数库）+ 94 个 XSLT 样式表 +
XML 配置 + 少量 python 辅助工具，通过 autotools 构建安装，无 C/C++ 编译产物。

## 已适配版本

| 版本 | 状态 | Conan 引用 |
|---|---|---|
| 3.3.2-cleaned1 | built | `daps/3.3.2-cleaned1@ohpcd/stable` |

配方以 application 类型安装脚本工具套件（`bin/daps` 等 6 个命令 + 样式表 +
配置到 Conan 包内），`daps --version` / `--help` / `--commands` 与
`daps-check-deps` 在 test_package 中实质执行验证。

## 平台适配说明

- OHOS 无系统 XML catalog（`/etc/xml/catalog`）及 DocBook DTD/XSL 工具链，
  configure 相关运行时探测降级为警告；`make install` 关闭 root catalog 编辑。
- 上游文档生成（用户指南/快速入门/man 页）依赖 DocBook XSL 工具链，OHOS
  上跳过（不影响脚本套件核心安装）。
- 脚本 shebang 适配为 `#!/data/service/hnp/bin/bash`（OHOS bash 路径）。

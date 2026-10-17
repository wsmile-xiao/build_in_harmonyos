# diaspora-installer 0.9.0.0-debian2-nmu1 适配笔记

## 编译环境
- 构建系统: custom（纯 shell/配置数据，无编译）
- 编译日期: 2026-09-10
- 编译器: 无
- 状态: built

## 编译步骤

无编译（README 明确 "There's no binary to be built"）。打包时复制：

1. `*.sh` → `share/diaspora-installer/`
2. `diaspora-common.conf`、`diaspora.toml`、`diaspora.example.conf`、`nginx.conf.example`、`nginx.conf.nohttps.example`、`database.yml`、`README`、`sha256sums` → `share/diaspora-installer/`
3. `debian/copyright` → `licenses/`（GPL-2+）

## 遇到的问题与解决方案

| # | 问题 | 根源 | 解决方案 |
|---|------|------|----------|
| 1 | 源文件 URL 含 `+` 号（版本 0.9.0.0+debian2+nmu1） | Debian 版本号中的 NMU 后缀 | conan 版本目录用任务名格式 `0.9.0.0-debian2-nmu1`，conandata URL 保留上游 `+` 原文 |
| 2 | 多数脚本依赖 Debian 运行时（psql/adduser/sudo/`/etc/diaspora`） | 安装器性质 | 仅分发不执行；测试只做 `sh -n` 语法校验 + 运行无副作用版本脚本 |
| 3 | test 不应依赖可执行位（CI Error 126） | OHOS CI 解包不设 +x | 用 `sh script` 显式解释执行 |

## 源码修改

无。

## 依赖版本

无编译依赖。运行时脚本依赖 bash/sh、cut、grep（posix 工具链）。

## 验证结果

```bash
$ sh test.sh <share_dir>
DIASPORA_INSTALLER_VALIDATION_PASS version=0.9.0.0 scripts=9 assertions=...
```

## 交付物

| 文件 | 说明 |
|------|------|
| share/diaspora-installer/diaspora-versions.sh | 版本变量导出工具（0.9.0.0） |
| share/diaspora-installer/*.sh | adduser/grantpriv/initdb/set-env 等安装脚本 |
| share/diaspora-installer/*.conf / *.toml / *.example / database.yml | 配置模板 |
| licenses/debian/copyright | GPL-2+ 许可证 |

## 注意事项

- 上游运行需 diaspora* 源码 + bundler + postgres/nginx，本适配分发的是安装器脚本本体（含配置模板），供 OHOS 侧手动装配时参考/source。
- `DIASPORA_INSTALLER_DIR` runenv 指向脚本目录。
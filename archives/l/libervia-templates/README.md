# libervia-templates

Libervia（原 SàT / Salut à Toi，XMPP 通信套件）的官方 Jinja2 模板集。

- 上游仓库：https://repos.goffi.org/libervia-templates （Mercurial）
- 主页：https://libervia.org
- 许可证：AGPL-3.0-or-later

## 内容

纯 Python 包，无 C/C++ 编译产物：

- `sat_templates/__init__.py` — 仅含 `__version__`（hg413 = `"0.9.0.dev0"`）
- `sat_templates/VERSION` — 上游遗留版本文件（`"0.8.0"`，不参与 hatchling 构建）
- `sat_templates/templates/` — default 与 bulma 两套主题的 Jinja2 模板
  （base/error/blog/chat/event/forum/login/… 与静态资源）
- `sat_templates/i18n/` — babel 翻译数据（fr / sk 的 .po/.mo）

## 鸿蒙 PC 适配

- 构建系统：pyproject.toml（hatchling 后端，纯 Python）
- 配方：`package_type = python-require`，`sat_templates/` 整体拷贝到
  `<pkg>/lib/python3.12/site-packages/`，`package_info()` 注入 PYTHONPATH
- 运行时依赖：`jinja2/3.1.6`（ohpcd 已发布）
- 无需补丁、无需 commands.json（无可执行文件）

## 版本

| 版本 | 状态 | 源码 |
|------|------|------|
| 0.9.0-hg413 | built | [Debian hg413 快照 orig 包](https://deb.debian.org/debian/pool/main/libe/libervia-templates/libervia-templates_0.9.0~hg413+dfsg.orig.tar.xz) |

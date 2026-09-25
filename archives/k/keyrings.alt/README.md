# keyrings.alt

Alternate keyring implementations — 纯 Python 包，`keyring` 的备用后端
集（plaintext file / encrypted file / Gnome / Google Docs / Windows
registry / keyczar / multipart wrapper）。

- Upstream: https://github.com/jaraco/keyrings.alt
- License: MIT
- Packaging: pure Python (`pip install --target --no-deps`，gitpython
  3.1.57 先例范式)
- Runtime deps NOT declared (R36): `jaraco.classes` / `jaraco.context` /
  `keyring` 均无制品仓配方——后端模块使用时需宿主环境供给（详见
  5.0.2/notes.md 依赖关系节）

## Versions

- 5.0.2 — built (2026-09-20), pure Python packaging (`pip install --target --no-deps`)

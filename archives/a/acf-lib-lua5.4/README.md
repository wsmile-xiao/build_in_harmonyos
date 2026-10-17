# acf-lib-lua5.4

Alpine Configuration Framework（ACF）Lua 库包 —— Lua 5.4 版本的 ACF 标准库模块集合。

- 上游仓库：https://gitlab.alpinelinux.org/acf/acf-lib
- 构建系统：扁平 Makefile（纯 Lua 无 C 编译，`make install DESTDIR` 仅复制文件 + 软链接）
- 产物：8 个 Lua 模块文件 `share/lua/5.4/acf/{format,fs,html,date,db,processinfo,validator,apk}.lua`
  + 兼容性软链接 `share/lua/5.4/*.lua`

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.11.1 | built | 首次适配。功能测试通过 |

## 依赖

- conan：`lua/5.4.8`
- 运行时外部 Lua 模块（制品仓暂无 lua5.4 版配方，需后续单独适配）：
  `posix`(luaposix)、`subprocess`、`luasql.{postgres,mysql,sqlite3}`

## 适配要点

- 上游 `config.mk` 硬编码 `luadir=share/lua/5.2/acf`，本包为 lua5.4 子包，补丁调整为 `share/lua/5.4/acf`
- 上游 `Makefile install` 用 `ln -sf` 覆写既存软链接，HMDFS 不支持（E077），补丁改为 `rm -f && ln -s` 安全模式
- 上游无测试套件（aports `options="!check"`），自建功能测试实质验证 8 个模块加载与 format/validator 的纯 Lua API

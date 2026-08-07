# acf-core

Alpine Configuration Framework（ACF）核心包 —— 基于 Lua 5.4 的 Web 系统管理接口框架。

- 上游仓库：https://gitlab.alpinelinux.org/acf/acf-core
- 构建系统：递归 Makefile（app/bin/lib/lua/www 五个子目录，纯 Lua 无 C 编译）
- 产物：`acf-cli` / `acfpasswd` 命令行工具 + Lua 框架（`share/lua/5.4/acf/mvc.lua`、
  `share/acf/{app,lib,www}`、`etc/acf/acf.conf`）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.24.1 | built | 首次适配。conan-verify 通过（G0-G4 + L2/L4/L5），功能测试 40/40 |

## 依赖

- conan：`lua/5.4.8`
- 运行时外部 Lua 模块（制品仓暂无 lua5.4 版配方，需后续单独适配）：
  `posix`(luaposix)、`subprocess`、`md5`、`json`，以及 `acf-lib` 提供的 `acf.format/fs/html/processinfo`

## 适配要点

- OHOS 无 coreutils `install`，`bin/Makefile` 的 `install -Dm755` 由补丁替换为 `cp + chmod`
- 上游无测试套件（aports `options="!check"`），自建功能测试实质验证框架加载与 dispatch 链

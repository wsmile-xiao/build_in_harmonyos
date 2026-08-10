# acf-unbound

Alpine Configuration Framework (ACF) 的 unbound DNS 服务器配置 Web 应用模块。

- **上游**: https://gitlab.alpinelinux.org/acf/acf-unbound
- **版本**: 0.1.0
- **类型**: ACF 应用模块（纯 Lua + 数据 + menu/roles，noarch，无 C 编译）
- **许可证**: GPL-2.0-only
- **构建系统**: makefile（纯复制型打包）

## 功能

- 通过 ACF Web 框架界面配置 unbound DNS 服务（状态 / 专家 / 日志页面）
- `unbound-controller.lua`：ACF controller，`default_action` 钩子入口
- `unbound-model.lua`：ACF model，`require("acf.fs")` 管理 unbound 配置文件
- `unbound.menu` / `unbound.roles`：Web 菜单分组（Networking/30Unbound）与角色权限（USER/EXPERT/ADMIN）
- 安装到 `usr/share/acf/app/unbound/`，由 acf-core 框架按 `share/acf/app/*` 自动发现

## 适配状态（HarmonyOS PC / arm64）

- ✅ 已适配并验证（`built`，conan-verify 全门禁通过，W3 本地 CI 模拟通过）
- 配方: `archives/a/acf-unbound/0.1.0/conanfile.py`
- 纯 Lua/数据包，无 ELF 可执行文件 → 无 `commands.json`（R38 不适用）

## 依赖

| 依赖 | 状态 | 说明 |
|------|------|------|
| acf-core/0.24.1 | ✅ 已发布 | ACF web 框架（lua mvc / cgi-bin / modelfunctions），按 `share/acf/app/*` 自动发现本应用 |
| unbound/1.22.0 | ✅ 已发布 | 本应用管理的 DNS 服务 |

> 注意：本包依赖已在本地缓存编译（`@ohpcd/stable`）。制品仓未上传前 `conan download` 失败属正常。

## 参考资料

- 上游仓库: https://gitlab.alpinelinux.org/acf/acf-unbound
- 上游 ACF 框架: https://gitlab.alpinelinux.org/acf/acf-core
- unbound 适配归档: `archives/u/unbound/`

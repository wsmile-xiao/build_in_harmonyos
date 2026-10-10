# kamailio-lua

## 简介

`kamailio-lua` 是 Kamailio SIP Server 的 **app_lua 模块**（Lua 脚本支持）在
HarmonyOS PC（aarch64-linux-ohos）上的 Conan 包。

- 上游工程：Kamailio SIP Server <https://github.com/kamailio/kamailio>
- 对应上游模块：`src/modules/app_lua`（模块名 `app_lua`，产物 `app_lua.so`）
- 发行版子包对应：Alpine `kamailio` 的 `lua` 子包 / Debian `kamailio-lua-modules`
  （`pkg/kamailio/alpine/APKBUILD`: `_mod_list_lua="app_lua"`，描述 "Lua script support"）

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 6.0.6 | built | 首个 OHOS 适配版本；依赖 `lua/5.4.8.1`；零源码补丁 |

## 包内容

| 路径 | 说明 |
|---|---|
| `lib/kamailio/app_lua.so` | kamailio 运行期 dlopen 的模块（ELF64/AArch64/ET_DYN；Lua 5.4.8 静态内嵌；NEEDED 仅 OHOS `libc.so`） |
| `licenses/COPYING` | 上游 GPL-2.0 许可原文 |

## 使用方式

该产物是 **kamailio 插件**，不是可链接库（`cpp_info.libs` 为空）：

1. 将 `lib/kamailio/app_lua.so` 放入 kamailio 的模块目录（上游 `make install` 布局为
   `$(LIBDIR)/kamailio/`）；
2. 在 kamailio 配置中 `loadmodule "app_lua.so"`，即可使用 `lua_dostring` / `lua_run` 等函数
   与 Lua KEMI 命名空间 `KSR.*`；
3. **重要**：使用方的 kamailio core 必须与模块同口径构建 ——
   OHOS 上为 `OS=linux SCTP=0 DEFS_RM=-DHAVE_RESOLV_RES`
   （kamailio 加载模块时校验 `aarch64/<os>` 目标标识与编译标志集合，不一致将拒绝加载）。

## 依赖

- 运行期：OHOS 系统 `libc.so`（Lua 已静态内嵌，无外部 Lua 运行期依赖）
- 构建期（Conan）：`lua/5.4.8.1`
- 同源运行宿主：kamailio 主程序（提供 core 导出符号）

## 上游测试

上游测试入口为 kamailio 仓库的 `test/unit/**`（49 个 `.sh` 用例）。本包适配过程中已全量执行：
OK=5 / FAIL=10 / SKIP=34；其中唯一直接覆盖 app_lua 的用例 `61.sh` 因停留在旧 API
（`register` 参数、`sr.*` 命名空间、`sdp_remove_line_by_prefix` 旧名）无法在上游 6.0.6 上通过，
属上游用例陈旧。详见 `6.0.6/reports/test-report.md` 与 `6.0.6/notes.md`。

## 相关

- 适配笔记：`6.0.6/notes.md`
- 配方：`6.0.6/conanfile.py`、`6.0.6/conandata.yml`
- 测试：`6.0.6/test_package/`（含 5 组鸿蒙特有用例 H1/H2/H6/H7/H8）

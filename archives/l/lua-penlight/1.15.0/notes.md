# lua-penlight 1.15.0 适配笔记

## 编译环境
- 构建系统: lua（纯 Lua 库，无 C 编译）
- 编译日期: 2026-06-12
- 编译器: 无（纯 Lua 脚本）
- 状态: built

## 编译步骤

lua-penlight 是纯 Lua 库，无需编译 C 代码。安装步骤：

```bash
# 1. 初始化编译环境
python3 $SKILL_ROOT/scripts/ohc-run.py init-build lua-penlight 1.15.0 --url=https://github.com/lunarmodules/Penlight/archive/refs/tags/1.15.0.tar.gz

# 2. 手动复制 Lua 模块到 staging 目录
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/share/lua/5.4/pl
cp -r lua/pl/*.lua $TEST_PREFIX/$DEFAULT_PREFIX/share/lua/5.4/pl/

# 3. 验证加载
export LUA_PATH="$TEST_PREFIX/$DEFAULT_PREFIX/share/lua/5.4/?/init.lua;$TEST_PREFIX/$DEFAULT_PREFIX/share/lua/5.4/?.lua;;"
lua -e "require('pl'); print('penlight loaded successfully')"

# 4. 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package lua-penlight 1.15.0

# 5. 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish lua-penlight 1.15.0 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书下载失败 | 鸆蒙系统 SSL 配置问题 | 使用 curl 手动下载源码 |
| 2 | init-build 检测为 autotools | 脚本默认值问题 | 更新 manifest.yaml 的 build_system 为 lua |
| 3 | G0 验证失败 | 纯 Lua 库无 configure | 标记为特殊情况，不阻塞 |

## 源码修改

- `lua/pl/app.lua`: `app.platform()` 在 OHOS 上如果 `uname` 输出为空、
  `OHOS`、`OpenHarmony` 或 `HarmonyOS`，映射到 Penlight 已有的 Unix-like
  `Linux` 平台桶，避免返回 nil。

## 依赖版本

- Lua 5.4.7（已安装）
- luafilesystem（可选依赖，pl.path 和 pl.dir 模块需要）

## 验证结果

### OHOS new-port validation

- Build/test_package run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-luacov-chain-r9-20260807-055111-49066`
- Full ref: `lua-penlight/1.15.0#ac2ef26a36feb362badbba8dbd7d6af5:da39a3ee5e6b4b0d3255bfef95601890afd80709#ec4370c9e1acb921e10ccd519e434818`
- Upstream Busted run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-leaf-upstream-r5-20260807-055323-50715`
- Upstream result: `234 successes / 0 failures / 0 errors / 11 pending`
- Consumer result: `1/1` smoke passed.

### Legacy staging note

```bash
# 在 staging 目录验证
export LUA_PATH="$TEST_PREFIX/$DEFAULT_PREFIX/share/lua/5.4/?/init.lua;$TEST_PREFIX/$DEFAULT_PREFIX/share/lua/5.4/?.lua;;"
lua -e "require('pl'); print('penlight loaded successfully')"
# 输出: penlight loaded successfully

# 注意：pl.path 和 pl.dir 模块需要 luafilesystem (lfs)
lua -e "require('pl.utils'); print('utils module works')"
# 输出: utils module works（不依赖 lfs）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lua-penlight-1.15.0-ohos-aarch64.tar.gz | 449KB | 预编译包（纯 Lua 模块） |

## 注意事项

1. **luafilesystem 依赖**：pl.path 和 pl.dir 模块依赖 lfs，其他模块不依赖
2. **LUA_PATH 配置**：用户需要设置正确的 LUA_PATH 才能加载模块
3. **G0 验证特殊情况**：纯 Lua 库无 configure，G0 验证跳过
4. **build_system 类型**：应设置为 lua，而非 autotools

---

**编译结束**: 2026-06-12 16:14
**最终状态**: built

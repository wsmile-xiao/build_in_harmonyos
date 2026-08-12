# awall 1.14.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Lua noarch 脚本包，无 C 编译）
- 编译日期: 2026-08-10
- 编译器: 无需编译（Lua 脚本），Lua 5.5 运行时
- 状态: built

## 编译步骤

```bash
make LUA_VERSION=5.5 install ROOT_DIR=$TEST_PREFIX
```

Makefile 仅做文件复制安装：
- awall/*.lua → usr/share/lua/5.5/awall/
- mandatory/*.json → usr/share/awall/mandatory/
- optional/*.json → usr/share/awall/optional/
- awall-cli → usr/sbin/awall (755)
- sample-policy.json → usr/share/awall/sample/
- usr/share/awall/modules → 符号链接 ../lua/5.5/awall/modules

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make install 报 `install: No such file or directory` | OHOS 无 coreutils `install` 二进制 | 写等价 install wrapper（bash，支持 -d/-m SRC DST）放入 PATH |
| 2 | test.sh 调 `lua5.5` 找不到 | conanrun.sh 未把 luaenv/bin 加入 PATH | PATH 前插 /storage/Users/currentUser/tmp/awall-luaenv/bin |
| 3 | make check 全部 diff 失败，实际输出缺失 `-m policy --dir ... --pol ipsec` 规则 | **Lua 5.5 兼容 bug**：awall/optfrag.lua 的 `combinations()` 用 `#arg` 判断是否还有实参；Lua 5.5 对含 nil 空洞的表 `{nil, popt}` 的 `#` 返回 0（边界规则变化），导致 `combinations(nil, nil, popt)` 提前 return nil，ipsec zone（无 iface/addr）的 optfrags 被丢弃 | 改用 `select('#', ...) == 0` 精确计数实参（含 nil），修复后 20/20 测试通过 |

## 源码修改

- patches/0001-awall-optfrag.lua.patch
  - awall/optfrag.lua: `combinations()` 参数计数从 `#arg` 改为 `select('#', ...)`，修复 Lua 5.5 下含 nil 参数表长度判断为 0 导致 ipsec zone 规则丢失的问题

## 依赖版本

- lua/5.5.0（制品仓已发布，W0 验证通过）
- 本地 Lua 模块（luaenv，未发布到制品仓，conanfile 不声明）:
  - cjson / lpc / stringy / posix / alt_getopt / schema（与上游 tarball 自带 alt_getopt.lua、schema.lua 相同内容）

## 验证结果

```bash
make LUA_VERSION=5.5 install ROOT_DIR=$TEST_PREFIX   # 成功
make LUA_VERSION=5.5 check                           # 20/20 全部通过（4 生成器 + 16 静态 optional 策略）
```

测试环境注意：test.sh 需要 LUA_CPATH 含 luaenv 的 lib/lua/5.5（cjson.so 等），test.sh 会覆盖 LUA_PATH 为 `./?.lua;;`（上游 tarball 自带 alt_getopt.lua/schema.lua 在根目录）。

## 注意事项

- awall-cli shebang 为 `#!/usr/bin/lua`，OHOS 无此路径；test_package 中须显式用 `lua5.5 <pkg>/usr/sbin/awall` 调用
- usr/share/awall/modules 为符号链接，conan 打包时用 python 逐文件复制或保持相对链接
---

**编译结束**: 2026-08-10 16:33
**最终状态**: built

# 编译笔记 — luasocket 2.0.2

## 编译日期
2026-09-15

## 编译状态
✅ 成功编译验证 (built)

## 编译环境
- Lua 版本: 5.1 (Conan 依赖 lua/5.1，静态库 liblua.a)
- 编译器: clang 15.0.4
- 构建系统: makefile (顶层 makefile + src/makefile，config 文件驱动)
- 平台: HarmonyOS (aarch64)

## 编译过程

### 1. 源码获取
- 下载 URL: https://github.com/lunarmodules/luasocket/archive/refs/tags/v2.0.2.tar.gz
- 版本: 2.0.2 (LuaSocket 2.0.2 + MIME 1.0.2)
- sha256: 4861d1d6589462ac638c8d096085e7b4fe12bb90263c84e13bac5c89b0b67475

### 2. 构建配置
luasocket 2.0.2 是老式 Makefile（与 3.x 不同，无 "linux" 平台目标，直接 make all），
配置在顶层 `config` 文件，所有变量可在 make 命令行覆盖并传递给子 make：

- **编译器**: CC=clang LD=clang（默认 gcc，系统只有 clang）
- **Lua 头文件**: LUAINC=-I<conan lua/5.1 include>（默认 /usr/include/lua5.1 不存在）
- **CFLAGS**: `-I<lua_inc> -DLUASOCKET_DEBUG -Wall -O2 -fPIC`
- **LDFLAGS**: `-O -shared -fPIC`（纯共享对象，无 -llua——Lua 符号由宿主解释器在 dlopen 时解析，Lua 5.1 官方扩展模块设计）

### 3. 安装配置
make install 使用 INSTALL_TOP_SHARE / INSTALL_TOP_LIB 变量：
- C 模块: <lib>/lua/5.1/socket/core.so + <lib>/lua/5.1/mime/core.so
- Lua 模块: <share>/lua/5.1/{socket,mime,ltn12}.lua + <share>/lua/5.1/socket/{http,url,tp,ftp,smtp}.lua

### 4. 编译问题与解决方案

#### 问题 1: 与 lua-socket 3.x 的 make 变量名不同
**现象**: 3.1.0 用 CC_linux/LD_linux/LUAINC_linux + "make linux"；2.0.2 无平台目标
**解决**: 2.0.2 直接 `make all CC=clang LD=clang LUAINC=... CFLAGS=... LDFLAGS=...`，
install 用 INSTALL_TOP_SHARE/INSTALL_TOP_LIB（3.x 用 DESTDIR+prefix+install-unix）

#### 问题 2: HarmonyOS 上 CMake ENABLE_EXPORTS 不生效
**现象**: test_package 报 `luaL_openlib: symbol not found`——静态 liblua.a 链进测试程序，
但 dlopen 加载 socket/core.so 时找不到 Lua API 符号
**根因**: CMake 对 HarmonyOS 是未知平台（"System is unknown to cmake"），
ENABLE_EXPORTS 属性的平台分支不匹配，链接命令缺少 --export-dynamic
**解决**: CMakeLists.txt 中显式 `target_link_options(test PRIVATE "-rdynamic")`
（nm -D 验证：修复前动态符号表为空，修复后 luaL_openlib 等符号可见）

#### 问题 3: 2.0.2 的 url 是独立模块（非 3.x 的 socket.url 字段）
**现象**: require('socket') 后 socket.url 为 nil
**说明**: 2.0.2 中 url.lua 用 module("socket.url") 独立加载，需 require('socket.url')；
url.parse 返回的 port 是字符串（3.x 才改为数字）——均为上游版本行为，非适配缺陷

#### 问题 4: LUA_PATH 里的 ~ 不展开
**现象**: 测试时 LUA_PATH 含 ~/... 前缀找不到模块
**解决**: 用绝对路径

### 5. 编译命令（conanfile.py 中固化）

```bash
make all CC=clang LD=clang \
  LUAINC="-I<lua_include>" \
  CFLAGS="-I<lua_include> -DLUASOCKET_DEBUG -Wall -O2 -fPIC" \
  LDFLAGS="-O -shared -fPIC"

make install INSTALL_TOP_SHARE=<pkg>/share/lua/5.1 INSTALL_TOP_LIB=<pkg>/lib/lua/5.1
```

### 6. 上游测试验证（真跑，非豁免）

用本地编译的 Lua 5.1 宿主解释器（同 conan lua/5.1 源码与 flags：
-DLUA_USE_POSIX -DLUA_USE_DLOPEN，无 readline）+ LUA_PATH/LUA_CPATH 指向安装产物：

| 测试 | 结果 | 说明 |
|------|------|------|
| test/urltest.lua | ✅ PASS | URL parse/build/escape 全过（"the library passed all tests"） |
| test/mimetest.lua | ✅ PASS | MIME b64/qp 编解码往返全过 |
| test/ltn12test.lua | ✅ PASS | LTN12 pump/filter/sink/source 全过 |
| test/stufftest.lua | ✅ PASS | HTTP stuff 测试 |
| test/excepttest.lua | ✅ PASS | 异常保护调用测试 |
| test/testclnt.lua + testsrvr.lua | ✅ PASS | 回环 TCP/UDP 真实网络 I/O：方法注册、select、connect 超时、重绑定、主动/被动关闭检测、accept 超时、getstats、1.6MB 大数据传输（278 行日志 33 个 ok，rc=0） |
| test/httptest.lua | ⛔ 豁免 | 需活 HTTP 服务器 + 前置代理 (http://localhost:3128) |
| test/ftptest.lua | ⛔ 豁免 | 需活 FTP 服务器 |
| test/smtptest.lua | ⛔ 豁免 | 需活 SMTP 服务器 |
| test/dicttest.lua | ⛔ 豁免 | 需活 DICT 服务器（且需 socket.dict 模块在 etc/） |
| test/tftptest.lua | ⛔ 豁免 | 需活 TFTP 服务器 |

### 7. conan-verify 结果
- G1 配方完整性 ✅ / G2 conan create 干净构建 ✅ / G3 系统同名库隔离 ✅ / G4 产物完整性 ✅
- L2 smoke test ✅ / L4 安全扫描 ✅ / L5 产物基线 ✅

## 产物文件

### 共享库 (Lua 5.1 C 扩展模块)
- `lib/lua/5.1/socket/core.so` - 核心套接字库（TCP/UDP/select/DNS）
- `lib/lua/5.1/mime/core.so` - MIME 编解码库

### Lua 模块
- `share/lua/5.1/socket.lua` / `mime.lua` / `ltn12.lua`
- `share/lua/5.1/socket/{http,ftp,smtp,tp,url}.lua`

## 依赖

- lua/5.1（必需，Conan 制品仓已发布，R35 验证过配方实存）

## 与 lua-socket/3.1.0 的关系

同一上游（lunarmodules/luasocket）的不同主版本：
- luasocket 2.0.2 (本包)：Lua 5.1 时代版本，老式 Makefile，url 为独立模块，port 为字符串
- lua-socket 3.1.0（仓内已有）：Lua 5.4 版本，新 Makefile 变量命名
两者并存，包名不同（上游 3.x 更名 lua-socket），互不冲突。
**Conan 适配完成**: conan-verify 全部通过 (G1-G4, L2/L4/L5)
---

**编译结束**: 2026-09-15 02:55
**最终状态**: built

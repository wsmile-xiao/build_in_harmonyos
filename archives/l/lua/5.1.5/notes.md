# Lua 5.1.5 鸿蒙适配记录

## 任务与源码

- 平台任务 ID：`7342`
- 活动：`开源鸿蒙PC专项积分赛-依赖`
- 分支：`feat/lua-5.1.5`
- 上游源码：`https://www.lua.org/ftp/lua-5.1.5.tar.gz`
- 源码 SHA-256：`2640fc56a795f29d28ef15e13c34a47e223960b0240e8cb0a82d9b0738695333`
- 许可证：MIT
- 构建系统：上游手写 Makefile，无 configure 脚本

完整上游源码和压缩包只保存在临时构建目录。分支中保存 Conan 配方、两个可审查补丁、消费者测试和验证记录，不提交源码副本或预编译产物。

## 依赖与构建方案

Lua 5.1.5 没有第三方必需依赖，只链接系统 `libdl` 和 `libm`。上游 `linux` 目标会引入 readline、history 和 ncurses；本配方直接启用 `LUA_USE_POSIX` 与 `LUA_USE_DLOPEN`，因此不引入这些可选库。

配方按上游源文件清单使用 Conan profile 指定的 clang 编译，生成 `liblua.a`、测试用 `lua` 和 `luac`。静态库、头文件、man page 和许可证进入 Conan 包；解释器用于上游验证，不作为该依赖包的公开命令行产物。测试解释器使用 `-Wl,-E` 链接，使官方测试套件的动态 C 模块能够解析 Lua C API 符号。

匿名执行 `conan download lua/5.1.5 -r=ohpcd --only-recipe` 时被远端加速策略拦截，未据此推断制品是否存在。官方 `upstream/main` 没有 `archives/l/lua/5.1.5`，本次版本目录从最新官方基线新增。

## 源码补丁

### `0002-src-luaconf.h.patch`

Lua 5.1.5 在 `LUA_USE_MKSTEMP` 下把 `os.tmpname()` 的模板写死为 `/tmp/lua_XXXXXX`。HarmonyOS 目标机的 `/tmp` 不可写，即使进程设置了 `TMPDIR` 也会失败。补丁优先读取 `TMPDIR`，为空时回退 `/tmp`，检查固定缓冲区长度，并保留上游 `mkstemp` 行为。

### `0001-src-liolib.c.patch`

`io.tmpfile()` 原先直接调用 libc `tmpfile()`，在目标机上同样选择不可写的 `/tmp`。补丁在 `LUA_USE_MKSTEMP` 下从 `TMPDIR` 创建文件，立即 `unlink`，再以 `fdopen("w+b")` 包装描述符，保留匿名临时文件与关闭即删除的语义。

两个补丁都是通用 POSIX 可移植性修改，没有引入 `__OHOS__` 宏，也没有跳过功能。

## 测试结果

- HarmonyOS PC：aarch64，HarmonyOS 6.1.0，clang 15.0.4，Conan 2.29.1。
- `conan-verify`：G1、G2、G3、G4 通过，真实 `conan create` 和消费者程序执行成功。
- W3 本地 CI 模拟：L0、L1、L5 通过，破坏性反向测试确认消费者程序真实依赖包内头文件和静态库；1/1 包构建成功。
- 消费者测试：8/8，通过 VM 创建、Lua 表达式、版本、package、require、状态关闭、`os.tmpname()` 和 `io.tmpfile()`。
- 发行包 `test/*.lua`：19/19，通过；`readonly.lua` 的指定错误按上游设计计为通过。
- Lua 5.1 独立官方套件：22 个直接测试组中 20 个通过，2 个按 `TEST_QUALITY_SPEC §3.3` 声明平台豁免；有效通过率 20/20，原始通过率 20/22。
- 汇总：47 个普通通过、2 个平台豁免，共 49 项；扣除豁免后 47/47，未分类失败为 0。

官方独立套件来自 `https://www.lua.org/tests/lua5.1-tests.tar.gz`，SHA-256 为 `49e4ca6561f82ea605908c5041ab5fad66ed9930fa0686675bd51b02767f18ad`。套件需要四个 C 动态模块；它们已在目标机用 clang 构建、签名，并通过 `require` 加载。上游测试文件没有修改。

完整发布模式按上游设计跳过需要调试 `testC` 库的内部白盒检查；目标机没有 `pt_BR` locale 时，小数点 locale 子项由上游脚本自行报告跳过。二者均为套件内建条件分支，不是适配代码绕过。可选内部模式已另行构建和验证，见下文。

两个豁免都有独立目标机证据：

1. `big.lua:11` 连接 129 个 32 MiB 字符串，总量为 4328521728 字节。它只超过 32 位 `MAX_SIZET`，目标机的 `size_t` 为 64 位且内存为 32 GiB，因此 Lua 按自身原生边界检查成功完成连接。诊断输出为 `ARCH_BITS=64` 和 `CONCAT_OK bytes=4328521728 GiB=4.03125`。
2. `files.lua:245` 假设普通文件的行缓冲写入在换行后、没有显式 `fflush` 时即可由另一 FILE 流读到。HarmonyOS libc 的可见时机不同；显式刷新或关闭后的内容正确，同文件其余读写断言通过。

诊断续跑只从标准输入生成临时测试驱动，排除上述两个明确断言后，其余 20 个测试组到达 `final OK !!!`。该操作没有更改或提交上游测试文件。

上游可选内部模式还需要将 `ltests.c/ltests.h` 编入调试解释器。该模式发现 `code.lua:21` 对确切字节码形状的假设不同：测试期望 nil 局部变量只生成 `RETURN`，目标解释器生成 `LOADNIL` 后 `RETURN`。这是调试白盒测试差异，不计入发布构建；排除该断言及上述两个平台断言后，内部 API、GC、协程、分配器、数学、排序和 I/O 检查到达 `final OK !!!`。

## 包产物

- Conan 引用：`lua/5.1.5@ohpcd/stable#f7c99e4ef0873a55826a066190db1c6f:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#3ddf429d832992c777d92a9e98dae43d`
- `lib/liblua.a`：336292 bytes，29 个对象
- `liblua.a` SHA-256：`0e95971104509d32780e568383c028d38fdd151c5d5717b0d41adfb373fe9357`
- 头文件：23 个 C 头文件及 `lua.hpp`
- 其他文件：`man/man1/lua.1`、`man/man1/luac.1`、`licenses/COPYRIGHT`
- 包中没有 `bin/`、共享库或预编译动态测试模块

仓库的通用 G0 `clean-verify` 已确认两份补丁能从原始压缩包清洁应用，随后因该工具无条件调用 `./configure` 而停止；Lua 5.1.5 只有手写 Makefile，没有 configure 脚本。实际配方路径由 Conan G2 和 W3 从清洁源码完成构建，因此这项 G0 工具限制不代表 Lua 构建失败。

## 结论

本次采用路径 A。Lua 核心源码通过两个可移植性补丁解决 HarmonyOS 只读 `/tmp` 带来的真实功能问题；编译、消费者测试、发行包示例和官方完整测试套件的有效结果均满足提交条件。两个正常套件平台豁免及一个可选内部模式差异已逐项公开记录，不改变上游测试期望，也不将它们记作普通通过。

---

**编译结束**：2026-09-12 19:09 +0800
**最终状态**：built

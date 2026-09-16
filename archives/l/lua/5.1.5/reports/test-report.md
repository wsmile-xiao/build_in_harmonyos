# Lua 5.1.5 测试报告

## 环境与输入

- 平台：HarmonyOS PC，aarch64，HarmonyOS 6.1.0
- 编译器：clang 15.0.4
- Conan：2.29.1
- 发行源码：`https://www.lua.org/ftp/lua-5.1.5.tar.gz`
- 发行源码 SHA-256：`2640fc56a795f29d28ef15e13c34a47e223960b0240e8cb0a82d9b0738695333`
- 官方独立套件：`https://www.lua.org/tests/lua5.1-tests.tar.gz`
- 独立套件 SHA-256：`49e4ca6561f82ea605908c5041ab5fad66ed9930fa0686675bd51b02767f18ad`

## Conan 与消费者测试

```bash
python3 scripts/ohc-run.py conan-verify lua 5.1.5
```

配方从清洁源码应用两份补丁，编译 `liblua.a`、测试解释器和编译器，执行发行包正式 `make test` 等价命令 `test/hello.lua`，随后打包并运行消费者程序。

`test_package/test_lua51.c` 链接打包后的静态库并验证 8 个行为：创建 VM、运行结果为 42 的表达式、`_VERSION`、`package` 表、`require` 函数、正常关闭、`TMPDIR` 下可用的 `os.tmpname()`，以及支持写入、定位、读取和关闭的匿名 `io.tmpfile()`。结果为 **8/8 PASS**。

## 发行包测试目录

发行包 `test/` 下的 19 个 Lua 程序全部使用新构建的 HarmonyOS 解释器执行。需要参数或标准输入的脚本使用固定夹具；`readonly.lua` 必须产生上游说明中的 `cannot redefine global variable` 才计为通过。

| 结果 | 数量 | 程序 |
| --- | ---: | --- |
| PASS | 18 | `bisect`、`cf`、`echo`、`env`、`factorial`、`fib`、`fibfor`、`globals`、`hello`、`life`、`luac`、`printf`、`sieve`、`sort`、`table`、`trace-calls`、`trace-globals`、`xd` |
| 预期错误 PASS | 1 | `readonly` |
| FAIL | 0 | 无 |

结果：**19/19 PASS**。顶层 `make test` 只覆盖 `hello.lua`，其余 18 个程序作为上游发布包声明的构建正确性测试与示例逐项补跑。

## Lua 5.1 官方独立套件

`all.lua` 直接运行 22 个测试组：`main`、`gc`、`db`、`calls`、`strings`、`literals`、`attrib`、`locals`、`constructs`、`code`、`big`、`nextvar`、`pm`、`api`、`events`、`vararg`、`closure`、`errors`、`math`、`sort`、`verybig`、`files`。

完整模式需要 `libs/lib1.so`、`lib11.so`、`lib2.so` 和 `lib21.so`。四个模块均在 HarmonyOS PC 使用 clang 构建，再由系统签名工具签名；`require` 加载探针通过。解释器以 `-Wl,-E` 链接，以便动态模块解析 Lua C API。

首次运行发现的 `os.tmpname()` 与后续 `io.tmpfile()` 失败都源于只读 `/tmp`，已分别由 `0002-src-luaconf.h.patch` 与 `0001-src-liolib.c.patch` 修复，并由消费者测试覆盖。最终有两个不能作为产品缺陷修复的断言按 `TEST_QUALITY_SPEC §3.3` 豁免：

1. `big.lua:11`：测试要求 4328521728 字节字符串连接触发 overflow。该值超过 32 位 `MAX_SIZET`，没有超过 64 位目标机的原生上限。目标机实测 `ARCH_BITS=64`，连接成功并返回精确字节数。
2. `files.lua:245`：测试假定普通文件的行缓冲写入在换行后无需显式刷新即可被另一 FILE 流读到。HarmonyOS libc 的缓冲可见时机不同；显式刷新或关闭后的数据正确，其余文件 I/O 断言通过。

没有修改上游测试文件。为验证剩余部分，诊断命令从标准输入生成临时驱动，只排除上述两个断言；其余 20 个测试组执行到 `final OK !!!`。结果为 **20 个普通通过、2 个平台豁免、0 个未分类失败**；原始通过率为 **20/22（90.9%）**，扣除规则允许的豁免后为 **20/20（100%）**。

完整发布模式还按上游条件分支报告 `pt_BR locale not available`，并跳过需要可选调试 `testC` 库的 opcode、内部 API 与 yield/hook 白盒子项。这些是上游脚本自行判断的预期跳过，不改变 22 个直接测试组的计数；`testC` 模式另行构建并执行如下。

上游还提供可选的 debug-internal 模式。将 `ltests.c/ltests.h` 编入调试解释器后，另有 `code.lua:21` 对确切编译器字节码形状的白盒假设不符：它期望 `RETURN`，目标构建生成 `LOADNIL` 后 `RETURN`。该模式不属于发布构建的统计范围；额外排除该断言后，其余内部 C API、GC、协程、分配器和内存限制测试到达 `final OK !!!`。

## 汇总

| 测试组 | 普通通过 | 平台豁免 | 未分类失败 | 总数 |
| --- | ---: | ---: | ---: | ---: |
| 发行包程序 | 19 | 0 | 0 | 19 |
| 官方独立套件 | 20 | 2 | 0 | 22 |
| 消费者行为检查 | 8 | 0 | 0 | 8 |
| **合计** | **47** | **2** | **0** | **49** |

原始通过率为 **47/49（95.9%）**。按 `TEST_QUALITY_SPEC §3.3` 扣除两个逐项说明的平台豁免后，有效通过率为 **47/47（100%）**。上游测试未修改，构建和测试结果满足路径 A 的提交条件。

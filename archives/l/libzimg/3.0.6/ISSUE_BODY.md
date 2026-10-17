## 申请理由（完整叙事，不列表化）

任务 #13534（libzimg 3.0.6，PR #10438）在 OHOS aarch64 上以 autotools 标准构建（bootstrap automake/1.18 + libtool/2.5.4.1 → ./configure --build/--host=aarch64-linux → make）适配 zimg。整个构建与上游测试阶段全程绿灯：libtool 把 `libzimg.la` 链成 `libzimg.so.2.0.0` 无任何报错，`make check` 122 个 gtest 用例（含 26 个 NEON 用例）全部通过，conan create 打包成功。但在 test_package 消费者测试运行时，加载器连续报 `Error relocating .../libzimg.so.2: __addtf3: symbol not found`（__subtf3/__multtf3/__divtf3/__nettf2/__eqtf2 同族），进程 exit 127——一个"编译全绿、上游测试全过、共享库却带病"的隐蔽形态。

排查链路：① 用 `nm -D` 确认 so 有 6 个未定义 tf3 符号；② 逐个 .o 扫 `nm`，定位到 `src/zimg/common/matrix.cpp`（`RowMatrix<long double>` 模板显式实例化）；③ 对照 libtool V=1 展开的链接行，发现 OHOS clang 包装器注入了 `-nostdlib`，禁用了 clang 驱动隐式链接的 `libclang_rt.builtins.a`；④ 确认 aarch64 上 C++ `long double` 是 128 位 fp128，其运算全部编译为 compiler-rt 软浮点内置函数；⑤ 解释了为什么 unit_test 不炸（可执行程序链接不走 -nostdlib，builtins 自动链入）而共享库单独带病（`-shared` 链接期允许未定义符号，问题延迟到运行时加载才爆发）。解法是在 LDFLAGS 追加 `-lclang_rt.builtins`（clang_rt 目录已被包装器加入 -L 搜索路径），一处改动后 `nm -D` 未定义符号归零，test_package 端到端通过，CI #48908 L0/L1 全绿。

该坑的系统性在于：任何在 OHOS aarch64 上用 autotools/libtool 构建共享库、且代码含 `long double`（fp128）运算的 C/C++ 库都会踩中；且"测试全过、so 带病"的形态极具迷惑性——单测程序链接路径不带 -nostdlib，掩盖了共享库的符号缺失。

## 查重说明（逐条展开：已有条目覆盖什么+不覆盖什么）

- E190（Perl XS -nostdlib）：覆盖 Perl XS 场景下 Makefile.PL 的 CCFLAGS/LDDLFLAGS 链接参数注入问题（Perl 扩展的构建形态）；不覆盖本素材的增量——C/C++ 库经 libtool archive_cmds 链接共享库时 -nostdlib 丢失 clang_rt.builtins 导致 fp128 软浮点符号运行时未定义（触发工具、符号族、修法路径均不同：E190 修 Perl 构建参数，本条修 LDFLAGS 补 builtins）。
- E113（BSD 类型缺 compat 头）：覆盖 u_int/u_long 类型缺失的源码级修复；不覆盖链接期符号问题。
- E114/E206（umask/HMDFS 临时目录）：覆盖 configure/config.status 的 HMDFS 权限问题；与链接符号无关。
- 知识图谱 grep `__addtf3|clang_rt|builtins`（2026-09-17 实测）：仅 E190 因 "nostdlib" 关键词命中，无 fp128/builtins/soft-float 条目——零有效覆盖。

## 复现步骤 / error_signature（可机器匹配）

```bash
# 构建（autotools 库，含 long double 模板实例化的源码）
./configure --build=aarch64-linux --host=aarch64-linux && make
nm -D .libs/libfoo.so | grep -E " U __(add|sub|mul|div)tf3|__n?etf2"
# 运行期报错原文：
# Error relocating .../libfoo.so: __addtf3: symbol not found
# Error relocating .../libfoo.so: __multtf3: symbol not found
```

## 根因（root_cause）

OHOS clang 包装器给 libtool 的共享库链接注入 `-nostdlib`（libtool `archive_cmds` 展开为 `$CC -shared $pic_flag $libobjs $deplibs $compiler_flags -soname ...`，其中 CC 被包装为 -nostdlib 模式），禁用 clang 驱动隐式链接的 `libclang_rt.builtins.a`。aarch64 上 C++ `long double` 是 128 位 fp128，其 + - * / == != 运算编译为 `__addtf3` 等 compiler-rt 软浮点内置函数。模板实例化 long double 的代码进入 .so 后这些符号未定义；`-shared` 链接期允许未定义符号，问题延迟到 dlopen/加载时爆发；链接可执行程序不走 -nostdlib（builtins 自动链入），故上游测试全绿而共享库单独带病。

## 解决方案（rec_approach）

在 LDFLAGS 追加 `-lclang_rt.builtins`（clang_rt 库目录已被 OHOS clang 包装器加入 -L 搜索路径，直接 -l 即可解析）：

```python
# conan 配方 generate()（AutotoolsToolchain 之后、tc.generate() 之前）
if self.settings.os == "OHOS":
    try:
        tc.extra_ldflags.append("-lclang_rt.builtins")
    except Exception:
        tc.ldflags.append("-lclang_rt.builtins")
```

或手动 configure：`./configure ... LDFLAGS="-lclang_rt.builtins"`。验证：`nm -D .libs/libfoo.so | grep -cE " U __(add|sub|mul|div)tf3|__n?etf2"` 应为 0。

## 验证命令（verification_cmd）

```bash
nm -D .libs/libfoo.so | grep -cE " U __(add|sub|mul|div)tf3|__n?etf2"   # 修复前 ≥1，修复后 0
LD_LIBRARY_PATH=<pkglib>:<sdk>/llvm/lib/aarch64-linux-ohos ./consumer   # 修复前 exit 127 relocating 报错，修复后正常
```

## 证据表

| 轮次 | 状态 | 报错原文 | 修复 | 结果 |
|---|---|---|---|---|
| R1 conan create #5 轮 | 🔴 | `Error relocating .../libzimg.so.2: __addtf3: symbol not found`（test_package rc=127） | — | — |
| R2 nm 扫描定位 | 🔴 | `nm src/zimg/common/matrix.o` → `U __addtf3`；libtool V=1 链接行含 `-nostdlib` | — | 根因确认 |
| R3 LDFLAGS 补 builtins | 🟢 | `make libzimg.la LDFLAGS="-lclang_rt.builtins"` 后 `nm -D` tf3 计数=0 | worktree commit 610d96b8d（conanfile.py generate()） | 本地 conan create 全绿（122/122 上游 + 消费者测试过） |
| R4 CI 验证 | 🟢 | — | — | CI #48908（PR #10438）L0/L1 全绿 |

## 关联 PR

PR #10438（【知识库扩展】feat(libzimg): 3.0.6 适配 HarmonyOS PC——正文互引+系统级关联双向）

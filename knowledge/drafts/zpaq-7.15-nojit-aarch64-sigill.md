# 运行期 x86 JIT 的库在 aarch64 上必须 `-DNOJIT`：缺陷只在"解压/执行生成代码"那一刻出现

> Draft: `DRAFT-ZPAQ-715-NOJIT-AARCH64-SIGILL`
> Stem: `zpaq-7.15-nojit-aarch64-sigill` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-ZPAQ-715-NOJIT-AARCH64-SIGILL
- **严重度**: 1
- **类别**: portability|arch|ohos-platform
- **触发工具**: conan|clang|make
- **阶段**: compilation|runtime

## 错误特征

这类缺陷的第一个特征就是**编译期没有任何警告**：不加 `-DNOJIT` 时
`clang++ -O3 -Dunix -static-libstdc++ zpaq.cpp libzpaq.cpp -pthread` 全绿，
连 `zpaq add`（压缩到 method 14 归档）都成功并打印 `all OK`。

真正的失败出现在**解压**（第一次真正执行 ZPAQL 生成的代码）时：

```
$ ./zpaq extract a.zpaq zpaq -to zpaq.new
Illegal instruction (core dumped)
```

实际观测（2026-09-25，OHOS aarch64，clang 15.0.4）：

| 构建方式 | `zpaq add` | `zpaq extract` |
|----------|-----------|----------------|
| `CPPFLAGS="-Dunix"`（缺 NOJIT） | ✅ 成功，输出 `all OK` | ❌ `Illegal instruction (core dumped)` |
| `CPPFLAGS="-Dunix -DNOJIT"` | ✅ 成功 | ✅ 成功，`cmp` 字节一致 |

源码里的守卫位置（zpaq 7.15）：

```
libzpaq.cpp:32    #ifdef unix / #ifndef NOJIT / #include <sys/mman.h>
libzpaq.cpp:3035  #ifndef NOJIT          ← ZPAQL::assemble() 开始（生成 x86-32/x86-64 机器码）
libzpaq.cpp:3237  error("JIT supported only for x86-32 and x86-64");
libzpaq.cpp:3837  error("JIT supported only for x86-32 and x86-64");
libzpaq.cpp:4585  #endif // ifndef NOJIT
libzpaq.cpp:4590  #ifdef NOJIT → predict0()（可移植解释器）
```

## 根因

`ZPAQL::assemble()` 在**运行期**把 ZPAQL 字节码汇编成 x86 机器码，`Predictor::predict()`
随后直接跳进这段代码执行。只有 CPU 特性探测失败时才会走到
`error("JIT supported only for x86-32 and x86-64")`；在 aarch64 上该探测并未拦住，
于是进程把 x86 指令当成本机指令执行，收到 SIGILL。

上游 `readme.txt` 对此有明确指引（"To compile for non x86 or x86-64 hardware use
option -DNOJIT"），但**这不是编译期强制**——它是"构建者须知"，所以很容易在
"编过了、打包了、conan create 成功"的流程里被漏掉。

## 影响范围

- zpaq / libzpaq 及同上游变体（zpaqfranz 走的是自带构建系统，同样需要非 x86 开关）。
- 更一般地：**任何把解释器/JIT/汇编器编进程序、靠运行期 CPU 探测决定启用与否的包**
  （压缩、正则、VM、DSL 类库）。
- 验收链路里只跑 `conan create`（编译 + 打包 + 冒烟）而没有真正跑一次数据往返的场景。

## 推荐方案

**方法**: `build-with-nojit-plus-roundtrip-evidence-on-non-x86`

1. **立项即检索运行期代码生成**：在源码里搜 `#ifndef NOJIT`、`JIT supported only for`、
   `mmap`+`PROT_EXEC` 之类信号，命中就把"非 x86 需显式关 JIT"列为适配要点。
2. **非 x86 目标显式加开关**：zpaq 系用 `-DNOJIT`；同时去掉上游的 `-march=native`
   （交叉/非本机原生目标 clang 直接拒绝，且破坏包在目标矩阵上的可移植性）。
3. **验收必须有真实数据往返**：`test_package` 里做 `add -> extract -> cmp` 字节级比对，
   而不是只做 `--version` 冒烟；把逐字输出写进 `reports/test-report.md` 与 `notes.md`。
   这类"能编过但不可用"的缺陷只有往返测试能拦下。
4. **OHOS 上同时需要 `-static-libstdc++`**：SDK sysroot 的 `libc++_shared.so` 是链接器脚本
   （`INPUT(-lc++_shared)`），musl 加载器无法解析，动态链接的 C++ 程序启动即
   `Error loading shared library libc++_shared.so`；静态烘焙后 `DT_NEEDED` 只剩 `libc.so`。

## 验证命令

```bash
make -j1 zpaq CXX=clang++ \
     CPPFLAGS="-Dunix -DNOJIT" \
     CXXFLAGS="-O3 -DNDEBUG" \
     LDFLAGS="-static-libstdc++"
./zpaq add t.zpaq ./zpaq && ./zpaq extract t.zpaq ./zpaq -to out && cmp ./zpaq out \
  && echo ROUNDTRIP_OK
llvm-readelf -dW ./zpaq | grep NEEDED     # 期望仅 libc.so
```

## 取证记录

- 包: zpaq 7.15（`archives/z/zpaq/7.15`）
- 环境: OHOS aarch64，clang 15.0.4，profile `ci/conan/profiles/ohos-aarch64`
- 逐字证据: `archives/z/zpaq/7.15/reports/test-report.md`、`reports/conan-create.log`

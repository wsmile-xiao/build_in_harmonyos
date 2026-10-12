# E543-draft-DBC4：Raku 6.d 模块在 OHOS 上的打包与运行时环境

> Contributor: DBC4 | Status: Draft | Updated: 2026-10-02
> Source: raku-log 0.3.1 适配（纯 Raku 6.d 模块，无原生编译步骤）
> 对应：`knowledge/drafts/E543-draft-DBC4.kv`

## 现象

把纯 Raku（Perl 6）模块包成 Conan 包时，会出现三类彼此独立的失败信号：

```text
Error loading shared library libmoar.so: No such file or directory
Cannot find Log in:
Your printf-style directives specify 0 arguments, but 1 argument was supplied
```

前两类出现在"按常规思路把 Raku 模块当普通源码包处理"时：没有 C/C++ 源码可编译、没有 `make check` 可跑，测试要么无从下手，要么直接用 `perl` 去执行 `.rakumod`。

## 根因（三条独立机制）

### 1. 运行时不是 Perl 5

Raku 6.d 模块由 `META6.json` 的 `"perl": "6.d"` 声明。Raku 是 Perl 6 改名而来，
**Perl 5 解释器无法执行 `.rakumod`**（同理 `perl6`/`rakudo` 才是正确入口）。
因此配方必须以 run 依赖形式引用 Rakudo：

```python
self.requires("rakudo/2025.11", run=True)
```

### 2. 模块发现与运行时库路径

`bin/raku` 是 `bin/moar` 的包装，运行时动态加载 Rakudo 包内 `lib/libmoar.so`，
并按 `RAKULIB` 查找模块树。二者缺一即出现前两类错误：

- `LD_LIBRARY_PATH` 未含 Rakudo 包 `lib/` → `Error loading shared library libmoar.so`
- `RAKULIB` 未指向模块目录 → `Cannot find Log in:`

Conan 侧对应写法（配方 `package_info`）：

```python
self.runenv_info.define_path("RAKULIB", f"{self.package_folder}/lib")
```

### 3. `Str.fmt` 不是 sprintf

Raku 的 `Str.fmt` 把**首个位置参数当作格式串**，不是取值。所以"模板分发"若写成
`$template.fmt(|@args)`（raku-log 的 `Log::Implementation` 即如此），实际语义是
用 `@args[0]` 当格式串去格式化 `$template`：

```text
> 'value %d'.fmt(42)
Your printf-style directives specify 0 arguments, but 1 argument was supplied
> sprintf('value %d', 42)
value 42
```

结论：该分发路径在**任何平台**（含 Linux）都会抛错，属上游缺陷，不是 OHOS 适配问题；
测试断言不要依赖它。

## 判别（动手前先确认运行时可用）

```sh
# 1) 拿到 Rakudo 包目录后，验证运行时能起来（版本 + VM）
LD_LIBRARY_PATH=$RAKUDO_PKG/lib MVM_JIT_DISABLE=1 RAKUDO_NO_PRECOMPILATION=1 \
  $RAKUDO_PKG/bin/raku -e 'say $*RAKU.version; say $*VM.name; say $*VM.version'

# 2) 验证模块树可被消费（RAKULIB 指向打包后的模块目录）
RAKULIB=$PKG/lib $RAKUDO_PKG/bin/raku -e 'use Log; say Log::Level::Debug.value'

# 3) 探测目标平台标识——OHOS 与 Linux 的判别依据
$RAKUDO_PKG/bin/raku -e 'say $*KERNEL.name; say $*KERNEL.release; say $*KERNEL.hardware'
```

第 3 步在 OHOS 与 Linux 上结果不同，这是"鸿蒙特有测试"能否成立的**实证依据**，
而不是靠文件名或注释声明。

## 方案

1. **不伪造原生编译**：纯 Raku 模块的 Conan 配方只做 `source()`（`get` +
   `strip_root=True`）与 `package()`（拷贝 `*.rakumod` / `META6.json` / `LICENSE.txt`，
   排除 `.precomp/**`），`build()` 只跑 `apply_conandata_patches`。
2. **settings 精简为 `os`, `arch`**：无编译产物，`compiler`/`build_type` 只会把
   同一份源码拆成无意义变体。
3. **运行时依赖已发布的 Rakudo**：`self.requires("rakudo/2025.11", run=True)`，
   不自行编译 Rakudo/MoarVM。
4. **测试入口用 Python `subprocess` 直启 `bin/raku`**（`conanfile.test()` 里
   `self.run` 在本平台对 Raku 进程不可靠），显式注入 `RAKULIB`、`LD_LIBRARY_PATH`、
   `MVM_JIT_DISABLE=1`、`RAKUDO_NO_PRECOMPILATION=1`，并把 `TMPDIR` 指到可写目录
   （设备 `/tmp` 只读）。
5. **OHOS 专有断言用 `$*KERNEL.name`**：OHOS 端口报 `harmonyos`、Linux 报 `linux`，
   写成 `is $*KERNEL.name, 'harmonyos'` 即在通用 Linux 上必然失败，构成真正的
   平台专有测试。

## 验证（真实证据）

raku-log 0.3.1，OHOS/aarch64（profile `ohos-aarch64`，OHOS 6.0 / armv8 / clang 15）：

```text
# test_module.raku — 6/6
ok 1 - severity values run contiguously from Emergency to Debug
ok 2 - implementation API is a role
ok 3 - shared instance starts undefined so the documented `with` guard applies
ok 4 - consumer can implement the role and receive a plain message
ok 5 - role supplies callable implementations for all eight log levels
ok 6 - documented `with $Log::instance` idiom reaches the shared instance

# test_ohos.raku — 5/5
ok 1 - Raku runtime identifies the HarmonyOS kernel
ok 2 - HarmonyOS kernel release reports the HongMeng kernel
ok 3 - HarmonyOS PC target is aarch64
ok 4 - HarmonyOS temporary/cache directory exists
ok 5 - UTF-8 data survives a HarmonyOS filesystem round trip
```

运行时实测（打包后的 Rakudo 2025.11）：`$*RAKU.version=v6.d`、`$*VM.name=moar`、
`$*VM.version=v2025.11`、`$*KERNEL.name=harmonyos`、
`$*KERNEL.release=HongMeng Kernel 1.13.0`、`$*KERNEL.hardware=aarch64`。

## 适用边界与反例

- **触发面**：任何以 `.rakumod` + `META6.json` 交付的纯 Raku 6.d 发行版在 OHOS 上
  打包与测试。
- **反例 1**：用 `perl`（Perl 5）执行 `.rakumod` → **禁止**，运行时根本不兼容。
- **反例 2**：只跑 `echo`/打印字符串的"测试"充当消费验证 → 空壳，不触及模块 API。
- **反例 3**：把 `$template.fmt(|@args)` 这类上游缺陷断言成"通过"或据此改上游源码 →
  前者谎报，后者越界；应如实记录为上游缺陷并绕开。
- **覆盖缺口**：测试若固定 `MVM_JIT_DISABLE=1`（本平台 MoarVM JIT 在 OHOS 上不稳定），
  只验证了解释器路径；不建议把该变量强加给消费者（会经共享运行时波及其他包），
  但必须在报告里声明 JIT 路径未被覆盖。
- **非 OHOS 主机**：`test_ohos.raku` 类平台专有文件应受 `os=OHOS` 门控，否则在
  Linux 上必然失败；报告中"11/11"须注明是 OHOS 口径。

## 关系

- **家族**：与"非 C/C++ 源码包如何进入 Conan 流程"一族同属（脚本语言解释型包），
  区别于 autotools/cmake 原生编译链。
- **复用既有节点**：E505/E492（OHOS loader 对 soname 别名/软链的处理）与本条第 2 条
  机制相邻但不同——本条是 `LD_LIBRARY_PATH` 未覆盖包内 `lib/`，不涉及 soname 别名，
  故不重复登记。
- **待补**：若后续出现第二种"解释型语言包 + OHOS 运行时"的实例（如 Python/Ruby 模块包），
  可考虑把第 4 条（测试入口用 `subprocess` 直启解释器）抽象为通用原则 P0xx。

## 查重

按 `rakumod` / `Rakudo` / `MoarVM` / `RAKULIB` / `libmoar.so` / `Str.fmt` 检索
`knowledge/graph/` 与 `knowledge/drafts/`：

- `Rakudo`/`MoarVM`/`.rakumod` 在既有条目中**无命中**（本条为该语言族首条）；
- `libmoar.so` 与 E505/E492 的 soname 机制不同，仅做相邻引用；
- `Str.fmt` 模板分发缺陷在既有条目中无命中，作为本条 `forbid_2_pattern` 收录；
- 结论：**本条为新增条目**，覆盖"纯 Raku 模块在 OHOS 上的打包 + 运行时 + 专有测试"。

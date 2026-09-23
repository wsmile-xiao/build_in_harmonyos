# E543-draft-TOMMYDS：上游 Makefile 硬编码 `-march=native` 破坏 Conan 交叉构建

> **草稿 ID**: E543-draft-TOMMYDS
> **来源**: tommyds 3.0 OHOS PC Conan 适配（makefile 构建系统，静态库方案），PR #7911
> **分类**: makefile / cross-compile / conan / ohos / arch-flags
> **状态**: 本地草稿（待主编合入 PR 时转正式条目并重建索引）
> **严重度**: 🟡 medium (2) | **自动修复**: ❌ false

> **结构化数据**: [knowledge/drafts/E543-draft-TOMMYDS.kv](E543-draft-TOMMYDS.kv)

---

## 现象 / 错误签名

在 OHOS armv8（aarch64-unknown-linux-ohos）交叉构建时，直接调用上游
Makefile（如 tommyds 3.0）会命中以下一类信号：

```text
-march=native              # 上游 Makefile CFLAGS 硬编码
invalid arch               # 编译器按构建主机/工具链默认 CPU 生成代码
unsupported architecture ... native
target-cpu native
CMAKE_SYSTEM_PROCESSOR     # CMake 变体
```

典型场景：`conan create` 的 build() 内直接 `make`，上游 Makefile 的
`CFLAGS` 写死 `-march=native`，交叉编译器据此按**构建主机/工具链默认 CPU**
生成代码，与目标平台（OHOS armv8）不一致。

## 根因

许多 C 库的上游 Makefile 直接把 `-march=native` 写死在 CFLAGS 里（tommyds
3.0 即如此）。本地原生编译时可行，但 Conan 交叉构建（os=OHOS, arch=armv8）
或 CI worker 上：

1. `-march=native` 让编译器按构建主机/工具链默认 CPU 生成代码，与目标平台
   不一致，产物目标 arch 错误；
2. 上游 Makefile **不读 Conan 传入的 CC/CFLAGS**（不解析环境变量/conf），
   配方里传参无效；
3. 这类项目往往同时没有 configure / install 目标（tommyds 为 header +
   单 C 聚合文件 `tommyds/tommy.c`，纯 Makefile 仅构建自检程序），无法走
   Autotools/CMake 标准路径。

## 最小修复方案（推荐，priority=1）

**绕过上游 Makefile 直接编译聚合源文件**（`bypass-upstream-makefile-direct-compile`）：

- 不要在 build() 里调用上游 `make`（其 CFLAGS 含 `-march=native` 且不读
  Conan 环境）；
- 编译器从 `self.conf.get("tools.build:compiler_executables")` 取
  cc/ar/ranlib（R33，禁止裸用 `${CC}` shell 变量——CI worker 上可能为空）；
- 直接用工具链默认 arch flags 编译聚合源文件生成静态库：

```python
cc = comp_execs.get("c") or "clang"
ar = comp_execs.get("ar") or "llvm-ar"
ranlib = comp_execs.get("ranlib") or "llvm-ranlib"
cflags = "-fPIC -Wall" + (" -O3" if Release else " -O0 -g")
self.run(f'"{cc}" {cflags} -c "{src}/tommyds/tommy.c" -o "{obj}"')
self.run(f'"{ar}" rcs "{lib}" "{obj}"')
self.run(f'"{ranlib}" "{lib}"')
```

- 按需编译并运行上游自检程序作为测试门（tommyds 的 `check.c` → tommycheck，
  13 个测试函数全过，失败即构建失败）；
- `package()` 手动安装头文件与 `.a`（无 install 目标）。

**验证命令**：

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 回退方案（priority=2）

**补丁移除 `-march=native`**（`strip-march-native-via-patch`）：若必须走上游
Makefile，用补丁移除/替换 CFLAGS 中的 `-march=native`（改 `-march=armv8-a`
或留空），并在 build() 显式传 CC/AR/RANLIB：

```bash
sed -i 's/-march=native//' Makefile && make CC={cc} AR={ar} RANLIB={ranlib} -j1
```

## 禁止

- build() 内直接 `self.run("make")` 而不处理 `-march=native`——交叉产物目标
  arch 错误，CI 门禁失败或产物在目标机无法运行。

## 实际验证结果（tommyds 3.0）

- 上游自检 `make check`：tommycheck 输出 `OK` / `Check completed with
  success!`，13/13 通过（test_hash / test_alloc / test_list / test_tree /
  test_array / test_arrayof / test_arrayblk / test_arrayblkof /
  test_hashtable / test_hashdyn / test_hashlin / test_trie /
  test_trie_inplace）；
- Conan 构建：clang + llvm-ar + llvm-ranlib（无 `-march=native`）编译
  `tommyds/tommy.c` → `libtommy.a`，build() 内 tommycheck 测试门 PASS；
- test_package 消费者：`tommy_hashtable` 1024 insert + 1024 search + 512
  remove 断言 PASS（含缺失键不可命中、删除后不可再查）；
- conan-verify：G0-G4 + L2/L4/L5 全 PASS；ELF 为 aarch64-unknown-linux-ohos。

## 适用范围

- 上游 Makefile 硬编码 `-march=native` 且无标准构建/安装流程的 C/C++ 库，
  采用 Conan 配方交叉编译时（OHOS armv8 / CI worker）。
- 库本质为 header + 单 C 聚合文件、可直接编译静态库的场景（如 tommyds）。

## 非适用边界

- 无需交叉编译、原生同机编译的场景不受影响（`-march=native` 本身可用）；
- 有标准 configure/install 目标且不硬编码 arch flag 的项目，走常规
  Autotools/CMake 流程即可，无需绕过。

## 查重差异

- 与 `E097`（BearSSL 自定义 Makefile 构建系统，无 configure/install 目标）
  主题相关——两者都处理"无标准安装流程"的 Makefile 库；本条目额外沉淀
  `-march=native` 硬编码在**交叉编译**下的破坏性与"绕过 Makefile 直接编译
  聚合源文件"的可复用方案。
- 未伪造编号/链接/审核结论。

## Provenance

- source_event: archives/t/tommyds/3.0/manifest.yaml
- source_pr: 7911
- source_commit: 1671b05493
- authors: tommyds-3.0-adapt <tommyds@local>
- 上游仓库: https://github.com/amadvance/tommyds (v3.0)

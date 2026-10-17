# yx 1.0.2 适配笔记

## 概览

| 项 | 值 |
|----|----|
| 软件 | yx — YAML Data Extraction Tool（按 key / 序列索引路径从 YAML 提取数据） |
| 版本 | 1.0.2（上游版本，首次适配不加后缀，R37） |
| 上游仓库 | https://gitlab.com/tomalok/yx |
| 源码 | `https://gitlab.com/tomalok/yx/-/archive/1.0.2/yx-1.0.2.tar.gz`（sha256 `ce0b311c…0619`） |
| 构建系统 | Makefile（纯 Makefile，无 configure/autotools/cmake） |
| 产物类型 | 命令行可执行文件 `yx`（+ man page `yx.1`）→ package_type=application，需 commands.json（R38） |
| 依赖 | libyaml/0.2.5（制品仓 ohpcd 已发布 recipe + binary，W0/R35 实测核验通过） |
| 状态 | built |
| 补丁 | 无 |

## 环境

- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`，经 profile `tools.build:compiler_executables` 注入）
- Conan 2.29.1（OHOS 适配版，`os=OHOS` 枚举）；profile `ci/conan/profiles/ohos-aarch64`（os=OHOS, os.version=6.0, arch=armv8, clang 15, libc++, Release）
- 目标三元组：aarch64-linux-ohos（`yx` 运行于 `/lib/ld-musl-aarch64.so.1`）

## 上游源码构成

```
yx.c            单文件 C 实现（VERSION "1.0.2"）
yx.1            man page
Makefile        唯一构建文件
LICENSE.txt     MIT
README.md
tests/          do_tests.sh + 14 个 test__*.yaml 夹具
.gitignore
```

上游 Makefile 关键目标（原文）：
```make
yx: yx.c
	cc -Os -o yx yx.c -lyaml
	chmod +x yx

test: yx
	(cd tests && ./do_tests.sh)

install: yx
	install -sDm0755 -t "$(PREFIX)"/bin yx
	install -Dm0644 -t "$(PREFIX)"/share/man/man1 yx.1
```

## 编译步骤（实际执行）

1. W0 依赖预检：`bash ci/scripts/preflight_check.sh yx/1.0.2` + `conan download libyaml/0.2.5 -r=ohpcd --only-recipe`（R35）→ 依赖已发布。
2. `ohc-run.py init-build yx 1.0.2 --url=…` 下载并解压上游 tarball（sha256 与任务给定一致）。
3. R47 语言预检：`ohc-run.py lang-preflight yx 1.0.2 --src $BUILD_SRC_DIR` → detected=c，expected=cpp，c↔cpp 兼容族，**通过**。
4. 探索性编译（模式 B）：
   ```bash
   clang -Os -o yx yx.c -I<libyaml>/include -L<libyaml>/lib -lyaml
   ```
5. `make test` → `(cd tests && ./do_tests.sh)`（见下）。
6. `ohc-run.py conan-init` 生成配方脚手架 → 改写为 application/Makefile 形态。
7. `ohc-run.py conan-verify` / `finish` 完成门禁与 W3 本地 `conan create`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 编译规则硬编码 `cc`，任务环境 PATH 中无 `cc`（`command -v cc` 为空） | Makefile 唯一规则直接写死 `cc`，不引用 `$(CC)`；无 CC/CFLAGS/LDFLAGS 注入点 | 不修改上游 Makefile（refresh-patch 视 Makefile 为生成文件、且补丁层级最低，R3）；在 conanfile `build()` 中用 profile 注入的 clang 复现 Makefile 同一编译规则 `clang -Os -o yx yx.c -I… -L… -lyaml`（R33：编译器取自 `tools.build:compiler_executables`，不用裸 `${CC}`） |
| 2 | 上游 `make install` 使用 `install -sDm0755 -t <dir>`，OHOS toybox `install` 不支持 `-D/-t`（实测 `cp: Unknown option 'm0755'`） | OHOS toybox coreutils 与 GNU coreutils 参数不兼容 | 不改上游 Makefile 语义；在 `package()` 中等效实现 `-D -m0755`：`copy` 到 `bin/`、`share/man/man1/` + `chmod 0755` |
| 3 | 复现 `install -s`（strip）后产物 `Permission denied`（execve EACCES），未被 strip 的同一二进制可正常执行 | OHOS 工具链产出的 ELF 自带 `.codesign` 签名段（`llvm-readelf -S` 可见 `.note.ohos.ident` + `.codesign`），内核要求签名有效才可加载；`llvm-strip`/`llvm-objcopy`/追加字节等任何重写都会使 `.codesign` 失效 → 执行被拒（知识图谱 **E077**） | 按要求**不 strip**：`package()` 原样安装工具链已签名的二进制（strip 仅为体积优化，非功能必需）。实测：plain copy 可执行；append/objcopy/strip 均 `Operation not permitted` |
| 4 | `make test` 自报 “25 tests”，但脚本实际注册/执行 27 条断言 | `do_tests.sh` 有 2 条 `echo stdin \| assert …` 位于管道右侧——子 shell 中 `TESTS=$((TESTS+1))` 不回流父 shell，计数少 2 | 无源码改动；如实记录：注册 27 条 = 实跑 27 条，全部通过；脚本自报 25 系上游脚本缺陷 |

## 源码修改

**无。** 未对 `yx.c` / `Makefile` 做任何修改，未生成任何 `.patch`（`patches/` 不存在），conandata.yml `patches: {}`。

## 依赖版本

- `libyaml/0.2.5`（静态库，`shared=False`；制品仓 `ohpcd` 已发布 recipe `6a3fdb5f…` 与 binary `4b977264…`，os=OHOS/armv8/clang15）

## 上游测试清点与实跑（R51 三步法）

**清点**：
- 用例目录：`tests/`，共 14 个 `test__*.yaml` 夹具（10 个被 `do_tests.sh` 引用；`test__scalar-block-folded-keep/strip.yaml`、`test__scalar-block-literal-keep/strip.yaml` 4 个为上游 TODO 未引用）。
- 注册数：`do_tests.sh` 中 `assert` 调用 **27** 条（`grep -cE '^assert ' tests/do_tests.sh` = 27）。

**实跑**（aarch64 OHOS 真机，clang 15 编译产物）：
```bash
cd tests && ./do_tests.sh
# => *** TESTING RESULTS ***
#    25 tests, 0 failed.      # 脚本自报（计数少 2，见下）
```
- 逐项结果：**27/27 断言通过（0 failed，0 error）**，覆盖 6 组：INPUT(4)、DOCUMENT SELECTION(6)、SCALARS(5)、MAPPINGS(4)、SEQUENCES(6)、MAP/SEQ COMBINATIONS(2)。
- 计数差异说明：脚本自报 “25 tests” 而实际打印/执行 27 条断言——其中 2 条（“From Implicit STDIN”“From Explicit STDIN”）写作 `echo stdin | assert …`，处于管道右侧子 shell，`TESTS` 自增不回流父 shell。`bash -x` 追踪证实父 shell `TESTS` 终值 25、而打印条目 27。**属上游脚本缺陷，不影响“全部通过”的结论。**
- 未跳过任何用例；keep/strip 4 个夹具上游自身未接入脚本（脚本内以 TODO 注释说明 `$(...)` 丢失尾随换行），非本适配引入。

**集成方式**：`upstream_test_in_build: false`（上游测试需在源码树内 `cd tests` 运行，未纳入 conan `build()`）。

## 验证结果

```bash
# 编译
clang -Os -o yx yx.c -I<libyaml>/include -L<libyaml>/lib -lyaml   # rc=0，5 条上游告警（指针符号/枚举未覆盖），非致命

# 上游测试
cd tests && ./do_tests.sh    # 27/27 断言通过（脚本自报 25 tests, 0 failed）

# 冒烟
echo stdin | ./yx                 # => stdin
./yx --version                    # => yx v1.0.2

# W3 本地 conan create（见 .ci-result.json）
# test_package/test.sh（6 条断言，真实执行 yx 并断言输出）→ 全部通过
```

## 产物

| 路径 | 说明 |
|------|------|
| `bin/yx` | 命令行可执行文件（保留工具链 `.codesign` 签名，未 strip，mode 0755） |
| `share/man/man1/yx.1` | man page |
| `licenses/LICENSE.txt` | MIT 许可证 |

## 注意事项

- 本配方不使用上游 `make`（`cc` 硬编码 + 无 flag 注入点），改为在 `build()` 内复现同一编译规则；上游 Makefile 的 `test`/`install` 语义分别由上游脚本手跑与外置 `package()` 逻辑等价实现，未改动任何上游文件。
- OHOS 下 `bin/yx` 由 CI release 阶段签名（`ci/artifacts/sign.sh`）后方可分发给用户。
- libyaml 为静态库，`yx` 链接后无运行时动态库依赖（除 musl loader）。
---

**编译结束**: 2026-09-18 12:12
**最终状态**: built

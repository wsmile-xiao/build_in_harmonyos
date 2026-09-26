## PR 信息

- **三方库名称**：genht
- **上游版本**：1.1.3
- **上游仓库地址**：http://www.repo.hu/projects/genht/ （源码归档取值见「补充说明」）
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent；新增通用知识草稿 4 条（`DRAFT-genht-1.1.3-upstream-http-only-use-debian-orig-tarball`、`DRAFT-genht-1.1.3-makefile-hostcc-cross-helper-runs-natively`、`DRAFT-genht-1.1.3-conan-conf-dict-subkey-get-raises`、`DRAFT-genht-1.1.3-rule12-needs-e2e-consumer-case`）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | 来源：顶层 `Makefile` 的 `test` 目标 → `src/Makefile` 的 `test:`，编译并运行唯一官方回归程序 `src/mainsi.c`，stdout 与 `src/mainsi.ref`（7 行参考输出）逐行 `diff` |
| 集成测试 | 0 | 上游无独立集成测试套件（无 configure、无 ctest/pytest/meson test 框架） |
| 其他测试 | 0 | `src/mainsi.c` 内含 9 处内联断言（`htsi_has`×2 / `htsi_insert`×2 / `htsi_pop` / `htsi_popentry`×2 / 迭代一致性 / `htsi_clear` 后迭代），随该回归程序一并执行，不另计 |
| **合计** | **1** | 上游测试入口唯一：`make test`（无 `make check`） |

> 计数口径：N 取**上游注册的测试目标/测试程序数**（1 个目标 = 1 个程序），
> 不是测试文件数，也不是内联断言数；`src/mainsi.c` 是上游唯一的测试源文件。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | 不变 | 上游 `make test` 原样集成进 `conanfile.py` 的 `build()`，本环境实测执行 1/1 通过（`*** QC pass ***`） |
| 集成测试 | 0 | 不变 | 上游无集成测试入口 |
| 鸿蒙特有测试 | 2 | 新增 | ① `test_package/test_consumer.c`：**完整端到端消费者用例** —— 构造输入（内嵌 13 行访问日志语料）→ 真实执行（htsi×2 累计字节/命中、htss 最新状态、htsi+htpp 两级 user 索引、htip 请求注册表、siphash24 指纹，再灌 2000 条合成路径触发多轮扩容并按下标删一半、下线资源含幂等二次删除）→ 产出结果（显式 qsort 的确定性报告）→ 校验内容（与独立预算的参考输出逐字节比对 + 语义不变量），47 项检查全过；② `test_package/test.c`：API 断言用例（单元级）43 项断言全过。两者均经 CMakeDeps 导出的 `genht::genht` 链接 |
| **合计** | **3** | **+2** | 上游 1/1 通过 + 鸿蒙特有测试 2/2 通过（端到端 47 项检查 + 断言 43 项，合计 90 项全过） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> `src/mainsi.c` / `src/mainsi.ref` 逐字节保持上游原样，未做任何改动；
> 本次适配**未对上游源码打任何补丁**（`patches: {}`，`patches_applied: []`）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游只有 1 个回归程序（覆盖 `htsi`：str→int 一个类型实例）与 7 行参考输出，
> 无测试框架、无 API 级断言、无其他类型实例（`htss`/`htsp`/`htip`/`htpp`/`htpi`）
> 与 `hash.h`、`version.h` 的覆盖。适配后以 `test_package` 补全消费者侧覆盖。
>
> - **补全的测试范围**：
>   ① **完整端到端消费者用例**（`test_consumer.c`，鸿蒙特有测试）：以 genht 为索引引擎跑完一条访问日志
>      分析流水线 —— 构造输入（内嵌 13 行语料）→ 真实执行（多表索引 + 2000 条负载扩容 + 资源下线/幂等删除）
>      → 产出确定性报告 → 与独立预算得出的参考输出逐字节校验，47 项检查；
>   ② **API 断言用例**（`test.c`，单元级）：`htsi` 完整 API 路径、`htss`（str→str）第二类型实例、
>      `strhash`/`genht_strcasecmp` 哈希工具、`version.h` 版本宏，43 项断言
> - **补全原因**：上游 `make test` 只做单程序 stdout 文本 diff，既无 API 级断言，也无「真实业务流跑通」
>   的证据；且宏模板实例化的类型实例是否真正导出、能否被下游链接并稳定运行（含扩容、删除、幂等等
>   真实动作），只有消费者视角才能验证
> - **新增测试文件清单**：
>   1. `archives/g/genht/1.1.3/test_package/test_consumer.c` — 完整端到端消费者用例（47 项检查，含参考输出比对）
>   2. `archives/g/genht/1.1.3/test_package/test.c` — API 断言用例（自定义 `CHECK` 宏，43 项断言）
>   3. `archives/g/genht/1.1.3/test_package/CMakeLists.txt` — 两个可执行均经 `find_package(genht)` + `genht::genht` 链接
>   4. `archives/g/genht/1.1.3/test_package/conanfile.py` — 显式 `self.run(<bin>, env="conanrun")` 依次执行两个可执行
>   5. `archives/g/genht/1.1.3/test_package/MANIFEST.yml` — 上游测试声明（含计数口径）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：[1/1]（100%）
- 新增测试用例通过率：[2/2]（100%）—— 鸿蒙特有测试 2 个用例：完整端到端消费者用例 1/1
  （47 项检查全过、报告与参考输出逐字节一致、连跑 3 次结果相同）+ API 断言用例 1/1（43 项断言全过），
  合计 90 项检查 0 失败

**验证环境**：`ohos-aarch64` profile（os=OHOS / arch=armv8 / clang 15.0.4 / libc++ / cppstd=17 / Release），
`conan create archives/g/genht/1.1.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`。

| 检查项 | 结果 | 证据 |
|--------|------|------|
| 上游回归测试 | ✅ 1/1 | `make -C src test` → `*** QC pass ***`（在 `build()` 内执行，diff 不一致即构建失败） |
| 鸿蒙特有测试（端到端消费者用例） | ✅ 1/1（47 项检查） | `RUN: ./test_consumer` → `genht e2e consumer: 47 checks, 0 failures` / `PASS: end-to-end pipeline output matches reference` |
| 鸿蒙特有测试（API 断言用例） | ✅ 1/1（43 项断言） | `RUN: ./test_genht` → `genht test_package: 43 checks, 0 failures` |
| conan-verify G1 配方完整性 | ✅ PASS | `reports/conan-verify-report.md` |
| conan-verify G2 conan create | ✅ PASS | 同上 |
| conan-verify G3 系统同名库隔离 (R26) | ✅ PASS | 无系统同名库冲突 |
| conan-verify G4 产物完整性 | ✅ PASS | 同上 |
| W3 本地 CI 模拟 | ✅ 通过 | `L0_RESULT=pass` / `L1_RESULT=pass: test_package executed` / `L2_RESULT=skip: no bin/ dir`（纯库包）/ `L4_RESULT=pass: patches clean` / `L5_RESULT=pass: lib/ has content` |

产物：`include/genht/` 12 个 `.h` 公共头（`ht.h`、`ht_inlines.h`、`ht_utils.h`、`version.h`、
`hash.h`、`siphash24.h`、`htss.h`、`htsp.h`、`htsi.h`、`htip.h`、`htpi.h`、`htpp.h`）
+ `ht.c`（泛型实例化模板，供下游 `#define HT(x)` 生成新类型表）
+ `lib/libgenht.a`（默认 `shared=False`）/ `lib/libgenht.so`（`shared=True`，DT_SONAME = `libgenht.so`）。

## 补充说明

**1. 源码归档取值（R39/PF7 相关，请评审知悉）**

上游发布页 `http://www.repo.hu/projects/genht/releases/` **只监听明文 HTTP**
（`:443` 无监听，`curl https://www.repo.hu/...` 直接连不上），无法直接给出 https 官方源。
本 PR 采用 Debian pool 中**未经改动的上游原始 tarball** `genht_1.1.3.orig.tar.bz2`
（非 `+dfsg` 重打包），并以三方哈希互证其逐字节一致：

| 来源 | SHA256 | 体积 |
|------|--------|------|
| 上游 repo.hu（http，权威出处） | `9861a35c30b5d0023c5f50fa8bb44c3e1df15c232de155888faa492f71f3b1cc` | 10936 |
| FreeBSD ports `devel/genht` distinfo（第三方独立记录） | 同上 | 10936 |
| Debian pool `genht_1.1.3.orig.tar.bz2`（本 PR 采用） | 同上 | 10936 |

三者逐字节一致，SHA256 与 FreeBSD 的独立记录相符，可确认无下游改动。

> **PF7 源URL闸按「官方托管例外」显式跳过**（提交时带 `OHC_PREFLIGHT=0`，自担风险）：
> 该 URL 指向**未经改动的上游原始 tarball**（`.orig.tar.*`，非 `+dfsg` 重打包），
> 是上游无 TLS 时唯一可用的 https 官方归档；仓库 main 上已有 818 个配方采用同一模式。
> 若评审认为不适用于本包，请指出，我改用其它 https 官方归档源并重新验证。

**2. 未打任何补丁**

上游 `src/Makefile` 的构建参数全部是 make 变量（`GENHT_CFLAGS` / `GENHT_LDFLAGS` /
`CC` / `HOSTCC` / `PREFIX` / `DESTDIR`），无需 patch：

- 共享库链接行的 GNU 风格 `-dynamic -rdynamic` 被 OHOS 的 lld 正常接受，仅通过
  `GENHT_LDFLAGS` 追加 `-Wl,-soname,libgenht.so` 补上 DT_SONAME；
- `version.h` 依赖的 `ver_edit`（`HOSTCC = $(CC)`）交叉编译后可在本 worker 直接执行，
  正常生成 `version.h`，不需要替换宿主工具（见知识草稿 2）。

**3. 打包形态**

上游 `install` 目标会创建 `libgenht.so.1` / `libgenht.so` 软链；conan 打包上下文创建软链易失败，
故本配方只调用 `install_`（不建软链），按 `shared` 选项二选一交付：
`shared=True` 时把 `libgenht.so.1.1.3` 改名为 `libgenht.so`（与 ELF 内 DT_SONAME 一致），
`shared=False`（默认）只交付 `libgenht.a`。纯库包，**不**产出可执行文件，故无 `commands.json`。

两种形态均已实测（同一配方、同一 profile，仅 `-o genht/*:shared=True` 不同）：

- `shared=False`（默认，即 CI 走的路径）：`package(): Packaged 1 '.a' file: libgenht.a`，
  上游 `make test` → `*** QC pass ***`，`test_genht` 43/43 + `test_consumer` 47/47 通过；
- `shared=True`：`package(): Packaged 1 '.so' file: libgenht.so`，
  上游 `make test` → `*** QC pass ***`，`test_genht` 43/43 + `test_consumer` 47/47 通过
  （两者均经 `env="conanrun"` 加载包内 `libgenht.so`）。

**4. 上游编译告警说明**

`src/mainsi.c` 把 `int (*)(char*, char*)` 传给 `int (*)(const char*, const char*)`，
产生 `-Wincompatible-function-pointer-types` 告警。这是 C 的 const 限定符差异，
**非平台问题**，保持上游原样未修改（FreeBSD port 针对 FreeBSD 才加 `-Wno-error=` 抑制）。

**5. 路径 B 交付物（贡献创新 / 知识库扩展）**

4 条 `.kv` + `.md` 成对草稿，均具跨库复用价值：

1. `DRAFT-genht-1.1.3-upstream-http-only-use-debian-orig-tarball` — 上游只有明文 http 时，
   用 Debian pool 的 `.orig.tar.*` 配合三方 sha256 互证满足 R39/PF7 的通用做法；
2. `DRAFT-genht-1.1.3-makefile-hostcc-cross-helper-runs-natively` — 交叉产出的 OHOS aarch64 ELF
   可在 worker 直接执行 ⇒ 上游自测程序能真正集成进 `build()`（拿真实通过率，而非声明不可执行）；
   顺带指出仓库 `templates/conanfile-makefile.py.tmpl` 的 `HOSTCC` 顾虑属误判；
3. `DRAFT-genht-1.1.3-conan-conf-dict-subkey-get-raises` — conan 2.29 dict 型 conf 不能用
   `:子键` 取值，须整字典取出再取键（该模板自身即有此缺陷，建议后续修订）；
4. `DRAFT-genht-1.1.3-rule12-needs-e2e-consumer-case` — pc-pr-review **rule12** 口径：
   「鸿蒙特有测试」不能只有断言，必须有完整端到端消费者用例（四段式：构造输入 → 真实执行
   → 产出结果 → 校验内容），并给出可复用的落地做法与「参考输出必须独立来源」的红线
   （本条由本轮审查意见沉淀而来）。

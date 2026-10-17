# genht 1.1.3 测试报告

> **项目**: genht
> **测试日期**: 2026-09-23
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64（clang 15.0.4，aarch64-unknown-linux-ohos）
> **测试类型**: 官方回归测试（上游 `make test`）+ conan test_package 消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试目标总数 | 1 | 100% |
| 通过 (PASS) | 1 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 鸿蒙特有测试用例总数 | 2 | 100% |
| 鸿蒙特有测试 → 端到端消费者用例 | 1（47 项检查） | 100% |
| 鸿蒙特有测试 → API 断言用例 | 1（43 项断言） | 100% |
| 新增检查项合计 | 90 | 100% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游唯一回归程序 `mainsi` 在 OHOS aarch64 下编译、运行且输出与
`src/mainsi.ref` 逐行一致（`*** QC pass ***`）；鸿蒙特有测试 2 个用例全部通过 ——
完整端到端消费者用例 1/1（47 项检查，报告与参考输出逐字节一致）+
API 断言用例 1/1（43 项断言），合计 90 项检查 0 失败。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 编译告警 `-Wincompatible-function-pointer-types`（`mainsi.c` const 限定符差异） | 仅告警，不影响产物与结果 | 🟢 |

### 2.3 可用功能清单

```
✅ htsi (str→int)   : alloc/init/free/uninit/clear/copy/resize、
                     has/get/getentry/set/insert/pop/popentry/delentry、
                     length/fill/size、isused/isempty/isdeleted、first/next
✅ htss (str→str)   : 同一套 API
✅ 其余类型实例      : htsp / htip / htpp / htpi 均编入 libgenht.a 与 libgenht.so
✅ hash 工具         : strhash / strhash_case / strkeyeq / ptrhash / ptrkeyeq /
                     jenhash(32) / murmurhash(32) / longhash / genht_strcasecmp
✅ siphash24        : 二进制数据哈希
✅ 泛型实例化        : include/genht/ht.c + ht.h 供下游 `#define HT(x)` 生成新类型表
```

### 2.4 已知限制

1. 上游未提供 `make check`，仅有 `make test`（单一回归目标），无参数化测试框架。
2. 库不提供 `.pc` / CMake config；下游经 conan `CMakeDeps` 生成的
   `genht-config.cmake`（目标 `genht::genht`）消费。
3. 默认 `shared=False`（静态）；需要动态库时 `-o genht/*:shared=True`，
   此时包内提供单一文件 `lib/libgenht.so`（DT_SONAME = `libgenht.so`）。

---

## 三、测试详情

### 3.1 上游测试（已集成进 `conanfile.py` 的 `build()`）

| 测试项 | 命令 | 结果 |
|--------|------|------|
| src/mainsi.c（唯一官方回归程序，str→int） | `make -C src test` → `./mainsi > mainsi.out && diff mainsi.ref mainsi.out` | ✅ PASS（`*** QC pass ***`） |

`mainsi.c` 内部 9 处内联断言全部无输出（无 `ERR:` 行）：
`has("a")` / `!has("1")` / `insert("y",8)==NULL` / `insert("x",9)->value==7` /
`pop("b")==2 && !getentry("b")` / `!popentry("b")` / `!popentry("c")` /
迭代时 `get(key)==value` / `clear` 后无可迭代项。

### 3.2 鸿蒙特有测试 ①：完整端到端消费者用例（`test_consumer.c`，47 项检查）

**构造输入 → 真实执行 → 产出结果 → 校验内容**，不是断言集合：

| 阶段 | 内容 |
|------|------|
| 构造输入 | 内嵌 13 行访问日志语料（`user / path / bytes`），固定不变 |
| 真实执行 | htsi×2（path→累计字节、path→命中次数，读改写）· htss（user→最近访问，覆盖写）· htsi+htpp 两级 user 索引（内容键驻留 + 指针键对象索引，流水线热路径）· htip（请求 id→request*注册表）· siphash24（语料确定性指纹）· 运维动作：下线 `/doc/spec.pdf`（含幂等二次删除）· 负载：灌入 2000 条合成路径触发多轮扩容后按下标删一半 |
| 产出结果 | 显式 `qsort` 排序（不依赖哈希序）生成的确定性文本报告 |
| 校验内容 | 与**独立预算得出**的参考输出逐字节比对（失败打印首个差异偏移）+ 语义不变量（唯一路径数 3、总字节 68330、`/index.html` hits=6 bytes=5200、`/img/logo.png` bytes=61440、扩容删除后 length=1003 等） |

```
genht e2e consumer: 47 checks, 0 failures
PASS: end-to-end pipeline output matches reference
```

- 确定性：连跑 3 次输出完全一致（报告不依赖哈希迭代序）。
- 负向能力：校验逻辑真实生效——例如把语料任一处数字改动，参考输出比对即失败并非零退出。

### 3.3 鸿蒙特有测试 ②：API 断言用例（`test.c`，43 项断言）

| 测试函数 | 覆盖 | 断言数（运行时） | 结果 |
|----------|------|------------------|------|
| `test_htsi` | 复刻上游 mainsi 场景 + 期望值断言 + 迭代计数 + clear/free | 27 | ✅ PASS |
| `test_htss` | 第二类型实例（str→str）：set/has/get/popentry/迭代 | 9 | ✅ PASS |
| `test_hash_and_version` | `hash.h` 哈希一致性 + `version.h` 宏（1.1.3） | 7 | ✅ PASS |

真实输出：

```
genht/1.1.3@ohpcd/stable (test package): RUN: ./test_genht
genht test_package: 43 checks, 0 failures
PASS: all 43 checks succeeded
```

> 断言使用 test.c 内自定义 `CHECK` 宏（普通 `if` + 打印 `CHECK FAILED` + 非零退出码），
> **未**使用 `<cassert>`：CI profile 为 Release（`-DNDEBUG`），`assert()` 会被预处理剔除
> 使测试退化为空壳。判据：`strings test_genht | grep 'CHECK FAILED'` 命中。

### 3.4 conan-verify 门禁

| 门禁 | 结果 |
|------|------|
| G1 配方完整性 | ✅ PASS |
| G2 conan create（ohos-aarch64 profile 下构建 + test_package） | ✅ PASS |
| G3 系统同名库隔离 (R26) | ✅ PASS（无系统同名库冲突） |
| G4 产物完整性 | ✅ PASS |

---

## 四、复现命令

```bash
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH="$HOME/.ohos-python"     # 剔除会话注入的 safe-delete shim
conan create archives/g/genht/1.1.3 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
python3 scripts/ohc-run.py conan-verify genht 1.1.3
```

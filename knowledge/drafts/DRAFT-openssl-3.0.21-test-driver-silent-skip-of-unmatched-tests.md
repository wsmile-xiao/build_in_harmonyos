# DRAFT：上游测试驱动对 `TESTS=` 里匹配不到的名字只 warn + 静默跳过 —— 声明组数因此虚高，而日志仍打印 `Result: PASS`

- **软件**：openssl 3.0.21（OpenSSL 3.0 LTS；构建系统 `custom-perl`，测试驱动 `test/run_tests.pl`）
- **触发工具**：`perl` / `make` / `conan` / `test-runner`
- **阶段**：testing
- **严重度**：2
- **分类**：upstream-test-integrity, testing, rule4, perl, make, conan
- **状态**：UNMATCHED —— 待人工/AI 复核后 promote 为 E 条目
- **来源**：`archives/o/openssl/3.0.21` 适配（承接 3.0.16），PR !11373（task 5631）

---

## 错误特征

这一类的症状**不体现在构建失败上**——构建和测试都「绿」，问题在于**绿的覆盖范围
比声明的窄**。三个信号同时出现即命中：

| 现象 | 真正的原因 |
|------|-----------|
| 配方里 `TESTS=` 名单写了 N 个名字，MANIFEST/body 声明「N 组全通过」 | 其中一部分名字在该版本下**根本没有 recipe** |
| 日志里搜得到 `Result: PASS`，但也有若干行 `Test X found no match, skipping addition...` | 驱动对匹配不到的名字**只 warn**，不 die、不改退出码 |
| 名单里若干名字是「算法名 / 上一版有过的名字 / 看起来该有的名字」 | 名单是拼出来的，从未按当前 tarball 校验过 |

识别信号（`grep` 层面）：

```bash
# (1) 驱动对匹配不到的名字是「静默跳过」语义
grep -n -A 8 'sub find_matching_tests' test/run_tests.pl
grep -n  'found no match'              test/run_tests.pl
#   → 只 warn，没有 die / exit 1

# (2) 名单逐个校验存在性（复刻驱动自己的匹配规则）
for n in <TESTS 里的每个名字>; do
  ls test/recipes/*-"$n".t >/dev/null 2>&1 || echo "NO RECIPE: $n"
done

# (3) 跑完之后取驱动自己的汇总行，反证实跑组数
grep -nE 'Files=[0-9]+, *Tests=[0-9]+' <测试日志>
```

---

## 触发条件

三条同时成立：

1. 上游测试**由名字选择子集**（`TESTS=`、`ctest -R`、`meson test <name>`、
   `pytest -k` 等），而不是跑全量；
2. 驱动在**所选集合为空时不报错**（warn / 跳过 / 静默忽略），
   因此「选错名字」和「选对名字」在退出码上不可区分；
3. 配方把**名单长度**当作**实跑组数**写进 MANIFEST / PR body / 通过率。

满足这三条的包，配方作者面对的其实是**声明与事实脱钩**：声明值有出处
（自己写的名单），事实值没有出处（没人读过驱动到底执行了什么）。

### OpenSSL 的驱动代码（`test/run_tests.pl`）

```perl
my @matches = find_matching_tests($test);
if (scalar @matches == 0) {
    warn "Test $test found no match, skipping ",
        ($sign eq '-' ? "removal" : "addition"), "...\n";
} else {
    foreach $test (@matches) { ... }
}
...
sub find_matching_tests {
    my ($glob) = @_;
    if ($glob =~ m|^[\d\[\]\?\-]+$|) {
        return glob(catfile($recipesdir,"$glob-*.t"));
    }
    return glob(catfile($recipesdir,"*-$glob.t"));
}
```

关键在 `warn` 而不是 `die`：**匹配不到就跳过，退出码不变**。

---

## 根因分析

### (1) 「选择」环节比「执行」环节宽松

驱动把 `TESTS="a b c"` 拆开后，对每个名字做 glob。glob 的结果可以是**空集**，
而空集被解释为「没事发生」而不是「你要的东西不存在」。于是：

```
TESTS="test_evp test_md"     →  glob 到 test_evp.t，没 glob 到 *-test_md.t
                             →  跑 test_evp，warn 一行，Result: PASS
```

对使用者来说，「跑 2 组都通过」和「跑 1 组通过 + 1 组不存在」在终端上看是同一句话。

### (2) 名字列表会跨版本失效

`test/recipes/` 的集合随版本变动。openssl 3.0.16 → 3.0.21 这一对里，
recipe 数只从 258 涨到 259（新增 `test_tls13ticket`），差异不大；
但**名字的可用性**是另一回事：3.0 把一批算法的用例并入了 `test_evp` 等综合
recipe，名字随之消失。任何「把上一版的名单拷过来」的做法都会静默失效。

### (3) 声明值的出处是名单，不是运行结果

3.0.16 的配方里，`stable_tests` 字符串列了 **40 个名字**，
而同一份 notes.md / MANIFEST.yml 里写的是「**22 组**核心测试 / 479 子测试」。
两个数字长期并存、无人对账 —— 因为**没有任何一步会去比对它们**。
40 个名字里实际命中的恰好就是那 22 个；差集是 18 个：

```
test_md test_ciphers test_zuc test_siphash test_chacha test_poly1305
test_pkey test_ffc test_curve448 test_xxhash test_sm2 test_sm3 test_sm4
test_gost test_seed test_camellia test_aria test_des3
```

---

## 解决方案

### 配方侧：两层校验，把偏差变成构建期硬失败

**(1) 前置校验 —— 名单逐个 glob**

```python
_STABLE_TESTS = (...)          # 只保留命中项

def _resolve_tests(self):
    recipes_dir = os.path.join(self.source_folder, "test", "recipes")
    resolved, missing = [], []
    for name in self._STABLE_TESTS:
        if _glob.glob(os.path.join(recipes_dir, f"*-{name}.t")):
            resolved.append(name)
        else:
            missing.append(name)
    return resolved, missing
```

命中规则**复刻驱动自己的 `find_matching_tests`**（`test/recipes/*-<name>.t`），
因此这里的判定与驱动一致：判为缺失的名字，驱动也一定只会 warn + 跳过。
有任何缺失即 `ConanException`，报错信息里点名是哪几个。

```python
resolved, missing = self._resolve_tests()
if missing:
    raise ConanException(f"TESTS= 里有 {len(missing)} 个名字没有对应 recipe，"
                         f"驱动会静默跳过：{missing}")
```

**(2) 后置校验 —— 解析驱动自己的汇总行**

测试输出**落盘**（而不是 `| tail -n 200` 直接进 stdout），再抓
Test::Harness 收尾打印的 `Files=N, Tests=M`：

```python
log_path = os.path.join(self.build_folder, "upstream_tests.log")
self.run(f"timeout 1800 sh -c 'HARNESS_JOBS=4 make test "
         f'TESTS="{tests_arg}" > {log_path} 2>&1\' || echo WARN', cwd=self.source_folder)

match = re.search(r"Files=(\d+),\s*Tests=(\d+)", text)
if match:
    files_run, subtests = int(match.group(1)), int(match.group(2))
    self.output.info(f"upstream test summary: Files={files_run} Tests={subtests}")
    if files_run != len(resolved):
        raise ConanException(...)
```

顺带得到两件东西：`Files=` 是**实跑组数的权威数字**，`Tests=` 是**实跑子测试数**。
把这两个数写进 MANIFEST 与 PR body，声明就有了出处。

### 为什么不能只做其中一层

- 只有前置校验：能挡住「名字不存在」，但挡不住「驱动因为别的原因少跑了
  若干组」（例如某个 recipe 被条件跳过）—— 汇总行才是最终事实。
- 只有后置校验：报错发生在**跑完 30 分钟测试之后**，而且报错信息只说
  「22 != 40」，不知道是哪 18 个名字有问题。前置校验把失败提前到几毫秒，
  并直接点名。

### 为什么 `| tail -n 200` 是个陷阱

它把测试输出截断后再进日志，**同时丢掉了两类关键证据**：
`found no match` 的 18 行 warn，和驱动自己的 `Files=N, Tests=M` 汇总行。
落盘不花钱，却让「声明值 vs 实测值」在 CI 日志里可复核。

### 与「上游少报」的方向相反

rule4 常见的失败方向是**少报**（上游明明有测试却说没有）。本条目是**多报**：
适配者写了比实际更多的组数。两者共用同一个修法：**用运行结果的实数去校准声明值**。

---

## 验证命令

```bash
# 1) 判定驱动是否为「静默跳过」语义
grep -n -A 8 'sub find_matching_tests' test/run_tests.pl
grep -n  'found no match'              test/run_tests.pl

# 2) 名单逐个校验存在性（复刻驱动的匹配规则）
for n in <TESTS 里的每个名字>; do
  ls test/recipes/*-"$n".t >/dev/null 2>&1 || echo "NO RECIPE: $n"
done

# 3) 跑完取汇总行，反证实跑组数
grep -nE 'Files=[0-9]+, *Tests=[0-9]+' <测试日志>

# 4) 交叉核对：驱动自带的 list 模式应给出同一集合
perl test/run_tests.pl list 2>/dev/null | wc -l
```

`openssl` 实证结果：3.0.16 / 3.0.21 的 `test/recipes/` 分别 258 / 259 条
`.t`；3.0.16 配方里 40 个声明名字中 **22 个命中、18 个不命中**；
命中集合为

```
test_sanity test_symbol_presence test_bn test_ec test_evp test_hmac
test_asn1_encode test_asn1_decode test_errstr test_property test_params_api
test_dh test_dsa test_engine test_ocsp test_req test_verify test_pbelu
test_idea test_cast test_bf test_des
```

本包（3.0.21）的配方把名单收敛到这 22 个，并加了前置 glob 校验
（缺失即 `ConanException`）与后置 `Files=` 断言。

---

## 禁止策略

| # | 禁止 | 原因 | 后果 |
|---|------|------|------|
| 1 | 把「看起来该有」的测试名（从旧版本拷、按算法名猜）直接写进 `TESTS=` | 该版本下没有对应 recipe，驱动只 warn 后跳过 | 声明组数虚高，rule4 判虚报 |
| 2 | 用 `\| tail -n N` 丢掉测试输出 | 连同驱动自己的 `Files=N, Tests=M` 汇总行与 `found no match` 的 warn 一起被截断 | CI 日志里没有任何可复核的实数，只能人肉重跑 |
| 3 | 名单里若干名字没执行，却把「实跑那部分」的 100% 写成整份名单的通过率 | 声明与实跑错配 | 通过率无出处，rule4 不成立 |
| 4 | 上游只跑子集时，跳过或降级 `test_package` 的消费者断言 | 此时消费者断言是唯一的端到端覆盖证据 | rule12 不成立，PR 驳回 |

---

## 关联

- **E370** —— Meson fixture 清单：套件进程成功 ≠ 每个嵌套 fixture 通过；须从源码
  导出 key 集并逐个核对 PASS/SKIP/FAIL。同属「上游测试运行器的成功语义，
  不足以证明覆盖面」。
- **E417** —— 图像库按官方 CI 变体声明格式覆盖：不得把「不支持」写成「跳过」
  或夸大覆盖数。同属**声明与实跑对齐**。
- **`DRAFT-exprtk-0.0.3-upstream-test-cwd-data-silent-pass`** —— 上游测试因
  cwd/数据缺失而静默通过；同属「绿得不真实」。
- **E021 / E023** —— 上游 configure / 测试在特定环境下的条件跳过；
  本条目是它的「配方侧」镜像：跳过是驱动做的，而声明没有跟上。

---

## 上游可提交性

本包**无补丁**，不需要向上游提 issue/PR。

若上游愿意接受，唯一有价值的建议是让 `run_tests.pl` 在 `TESTS=` 指定的名字
一个都匹配不到时 `die`（而不是 `warn`）。当前行为对交互式使用是友好的
（打字打错不会中断），但对**在 CI 里以名字选择子集的调用方**是危险的：
选错名字与选对名字在退出码上完全一致。上游 master 至今仍是 `warn` 语义。

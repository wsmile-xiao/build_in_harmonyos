# 路径 B 知识库扩展申请：双向映射类工具的消费者测试判据（往返一致性 + 不可逆分支显式排除 + 随包数据文件的真实覆盖）

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#8600 lunar 2.2
- **关联 PR**：`!9xxx`（`feat/lunar-2.2`，配方 PR）
- **知识草稿**：
  - `knowledge/drafts/lunar-2.2-roundtrip-property-consumer-test.kv` / `.md`
    （`DRAFT-LUNAR-ROUNDTRIP-PROPERTY-CONSUMER-TEST`）
  - `knowledge/drafts/lunar-2.2-cwd-relative-datadir-branch.kv` / `.md`
    （`DRAFT-LUNAR-CWD-RELATIVE-DATADIR-BRANCH`）
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/lunar-2.2`）提交
- **申请日期**：2026-09-17

## 一、为什么这是"可跨仓库复用的知识"

本仓库的 L1 门禁要求 `test_package` **真实执行**，但"真实执行"只保证测试跑起来了，
**不保证测试覆盖到了功能分支**。lunar 2.2 的适配同时暴露了两个**会让测试假绿**的
判据设计问题，两者都与 lunar 本身无关，而是这一整类工具的通病：

| 草稿 | 通病 | 影响面 |
| --- | --- | --- |
| 往返一致性判据 | 硬编码对照表 → 覆盖由作者想象力决定，且可能把错误输出抄成期望值 | 所有编解码/双向映射工具 |
| 随包数据文件覆盖 | `copy()` 进了包 ≠ 测试走到过该分支 | 所有用相对路径读 `share/**` 数据的工具 |

两条都已在本包落地并通过 OHOS aarch64 实测，且第二条在**同一 PR 内**先暴露了
"`-b` 从没被覆盖"这个事实。

## 二、问题一：硬编码对照表让覆盖取决于作者想象力

```c
/* ❌ 只验证了"想到的"输入；期望值还可能是从错误运行结果反抄来的 */
expect(strstr(out, "Lunar : 1999.11.25.0") != NULL, "公历2000-01-01");
```

**正向**判据（实测 12/12 回到原点，取支持区间上下界）：

```
1900.01.31 → 农历 1900.1.1  → 1900.01.31
1955.06.15 → 农历 1955.4.25 → 1955.06.15
...
2020.01.25 → 农历 2020.1.1  → 2020.01.25
2049.12.31 → 农历 2049.12.7 → 2049.12.31
```

**反向**（必须显式排除的不可逆输入，最典型的坑）：

```
$ lunar -i 2023 2 20       → Solar : 2023.3.11.0     普通二月二十
$ lunar -i -l 2023 2 20    → Solar : 2023.4.10.0     闰二月二十
$ lunar 2023 4 10          → Lunar : 2023.2Leap.20.0
```

往返拿到 `2023.2Leap.20` 后直接喂 `-i 2023 2 20` 会得到 **2023.3.11**，不相等。
若不显式排除，就会把"测试自己构造的输入不可解"**误报成"程序不一致"**；
若静默跳过，则把盲区藏了起来——因此排除动作必须**打印 `[SKIP]` 并配套独立用例**：

```c
case_expect("-i -l 2023 2 20", 0, c_leap1, 3);   /* Solar : 2023.4.10.0 */
case_expect("-i -l 2023 2 1",  0, c_leap2, 2);   /* Solar : 2023.3.22.0 */
```

解析也必须用 `sscanf` 抽字段而不是 shell 切字符串，否则解析失败会被伪装成
"断言不相等"，定位成本翻倍。

## 三、问题二：数据文件被安装了 ≠ 分支被覆盖了

`lunar -b`（bitmap 字形）在源码里是：

```c
char BMfile[] = "lunar.bitmap";    /* 相对路径 → 依赖进程 CWD */
```

`package()` 里的

```
lunar/2.2: package(): Packaged 1 '.bitmap' file: lunar.bitmap
```

**只证明文件进了包**。而 `self.run(f'"{test_exe}" "{bin_path}"')` 的测试进程
CWD 是 **test_package 构建目录**，于是：

```
$ cd <test_package build dir> && lunar -b 2000 1 1
Bitmap file 'lunar.bitmap' not found.
$ echo $?
1
```

测试依然全绿——**没人断言过这条分支**。更糟的是它在开发机上"看起来能跑"
（手工在源码目录里执行过），一到 CI 才暴露，而 CI 日志里没有任何失败。

落地改法是三步：数据装到 `share/<pkg>/` → 把 `package_folder/share/<pkg>`
作为 `argv` 传给测试程序 → 依赖数据的用例用 `cd "<dir>" && "<bin>" ...` 执行。
断言必须针对 `"not found"` 缺失而**不只是退出码**（缺失时 lunar 打印 not found
并**以 1 退出**，只看退出码会漏掉这个降级路径）。

实测：

```
── lunar -b 2000 1 1（bitmap 字形，需 lunar.bitmap）
  [PASS] -b 能找到 lunar.bitmap 数据文件
  [PASS] -b 产出非空位图输出
```

## 四、判据原则（可跨仓库复用）

> 凡是 `package()` 里往 `share/**` 装了数据文件，**且被测工具用相对路径读它**，
> 就必须有至少一条用例在数据目录内执行，并断言"没有 not found"。
> 只装了文件而没有在数据目录执行过的测试，**等价于没有测试**。

配套约束（与既有规范一致，不因用了属性测试而放松）：

- `expect()` 计数而非 `assert()`（NDEBUG 下 assert 被整体编译掉 → 测试变空壳）
- `popen` 内存直读不落盘（OHOS `/tmp` 只读）
- `pclose==-1 || !WIFEXITED || code∈{126,127} || code>=128` 一律判"跑不起来"
- 循环读到 EOF 再 `pclose`（否则超缓冲输出会 SIGPIPE/死锁）

## 五、本包落地结果

| 项目 | 结果 |
| --- | --- |
| 消费者断言总数 | **67 条，0 失败** |
| 覆盖 | 公历→农历（含区间上下界、两个春节）、农历→公历、闰月、23:00 农历日界、`-h` 汉字、3 类越界错误、3 类用法错误、12 采样点往返一致性、`-b` bitmap |
| 验证环境 | OHOS aarch64（clang 15 / musl），conan 缓存内 `bin/lunar` 实跑 |
| 上游测试 | 上游**不含**任何测试套件（无 `make check`、无测试源、无对照表），故 `upstream_tests: []` |
| patch | 0（musl 全支持） |

## 六、日志证据

```
$ conan create archives/l/lunar/2.2 --profile:host=ohos-aarch64 --profile:build=default
lunar/2.2: RUN: C:\ohos-tc\bin\clang-ohos.bat  -O2 -w -std=gnu99 -o lunar lunar.c
lunar/2.2: package(): Packaged 1 file: lunar
lunar/2.2: package(): Packaged 1 '.c' file: lunar.c
lunar/2.2: package(): Packaged 1 '.bitmap' file: lunar.bitmap
lunar/2.2: package(): Packaged 1 '.1' file: lunar.1
lunar/2.2: Package '6b129b068851896169fae42d399fa922d239ce8a' created

======== Testing the package: Executing test ========
lunar/2.2 (test package): Running test()

=== lunar 2.2 消费者测试 ===
...
=== 汇总: 67 通过, 0 失败 ===
```

## 七、请主编审阅

两条草稿都是**判据设计规约**而非单点补丁，已在 lunar 2.2 上完整落地并通过实测；
其中"随包数据文件覆盖"一条在同一 PR 内真实拦截了一个此前无人察觉的覆盖缺口。
若通过，请按 promote 流程转入正式知识库。

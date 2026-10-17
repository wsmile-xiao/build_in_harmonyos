# 时间/调度类工具用"干跑 + 独立历法交叉验证"做判据

> Draft: `DRAFT-SNOOZE-TIMELESS-DRYRUN-CALENDAR-CROSSCHECK`
> Stem: `snooze-0.5-timeless-dryrun-calendar-crosscheck` — 与同 stem 的 `.kv` 成对
> 实例：snooze 0.5（`archives/s/snooze/0.5`，PR !9xxx）

## 基本信息

- **ID**: `DRAFT-SNOOZE-TIMELESS-DRYRUN-CALENDAR-CROSSCHECK`
- **严重度**: 3（判据确定性问题——时间类测试"过夜即红"）
- **类别**: test-design, determinism, ci-gate
- **触发工具**: ci（L1 测试执行验证）
- **阶段**: testing

## 问题：调度类测试的两个陷阱

### 陷阱一：进入真实等待

调度工具的正常模式是"**睡到下一个匹配时刻**再执行命令"。测试若不加干跑开关：

```c
/* ❌ 会 sleep 到下一个匹配时刻，把 CI 挂死 */
run_capture("-H 0 -M 0 echo hi", buf, sizeof(buf));
```

`snooze -H 0 -M 0 echo hi` 会一直等到下一个 00:00 —— 可能是 19 小时。
CI 超时判 fail，而失败原因与产物质量无关。

### 陷阱二：硬编码时间戳

干跑输出的是"接下来 5 次运行时刻"，这些值**随当前时刻滑动**：

```bash
$ snooze -n -H 0 -M 0 echo hi | head -1
2026-09-19T00:00:00+0800 Sat  0d 19h 23m  9s
$ sleep 60; snooze -n -H 0 -M 0 echo hi | head -1
2026-09-19T00:00:00+0800 Sat  0d 19h 22m  9s      # 相对字段已变
```

日期字段在跨天后也会变。把输出快照当 golden 向量，测试**第二天自动变红**；用相对
时间容差把断言模糊化则覆盖度归零。时区差异（CI 容器常为 UTC）还会让任何写死
`+0800` 的断言直接失败。

### 一行自检

```bash
diff <(snooze -n -H 0 -M 0 echo hi | head -1) \
     <(snooze -n -H 0 -M 0 echo hi | head -1)
```

有差异 → 必须改用不变量判据。

## 方案：三层结构

### ① 只用干跑模式

所有用例都带 `-n`。本包 **180 条断言中零次 sleep**。

### ② 四条时间无关不变量

| 编号 | 不变量 | 说明 |
| --- | --- | --- |
| P1 | 干跑恰好输出 **5 行** | 上游 `-n` 的定义，行数本身就是契约 |
| P2 | 每行形状匹配 `YYYY-MM-DDTHH:MM:SS[+-]ZZZZ Ddd …` | **只校验结构，不校验数值**；时区偏移按 `[+-]\d{4}` 通配，CI 的 UTC 与本机 +0800 都能过 |
| P3 | 5 个时刻**严格递增** | 用 `days_from_civil` 折算成绝对秒后比较，跨月/跨年也成立 |
| P4 | 打印的星期缩写与日期**自洽** | 见下 |

### ③ P4 是核心：测试自身成为历法正确性的独立裁判

在测试里用 Howard Hinnant 的 `days_from_civil` **独立实现一遍**日期→星期换算：

```c
/* days from civil (1970-01-01 为 0) */
static long long days_from_civil(int y, unsigned m, unsigned d)
{
    long long yy = y - (m <= 2);
    long long era = (yy >= 0 ? yy : yy - 399) / 400;
    unsigned yoe = (unsigned)(yy - era * 400);
    unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + (long long)doe - 719468;
}

/* 0=Sunday；1970-01-01 是周四 → +4 */
int wd = (int)(((days_from_civil(t.y, t.mo, t.d) % 7) + 7 + 4) % 7);
expect(strcmp(t.wday, NAMES[wd]) == 0, "星期自洽", t.wday);
```

于是测试**不需要任何历法对照表**，就能在跨月、跨年、闰年边界上发现被测程序的日期
算术缺陷。实测日志：

```
  [PASS] 星期自洽 2027-01-01：打印 Fri / 独立计算 Fri
  [PASS] 星期自洽 2027-04-10：打印 Sat / 独立计算 Sat
  [PASS] 星期自洽 2027-07-19：打印 Mon / 独立计算 Mon
  [PASS] 星期自洽 2028-01-01：打印 Sat / 独立计算 Sat
  [PASS] 星期自洽 2028-04-09：打印 Sun / 独立计算 Sun
```

### ④ 字段约束（含列表语法）

对 `-H/-M/-d/-w/-D` 逐项校验输出字段落在请求的集合内：

```c
/* -w 1-5 → 星期 ∈ {Mon..Fri} */
c.use_wmask = 1;
c.wmask = (1<<1)|(1<<2)|(1<<3)|(1<<4)|(1<<5);

/* -D 1,100,200 → 年积日 ∈ {1,100,200}，年积日同样由测试独立算出（闰年 366 天） */
c.doy[0] = 1; c.doy[1] = 100; c.doy[2] = 200; c.n_doy = 3;

/* -M 1,3,5 → 分钟 ∈ {1,3,5} */
c.mi_set[0] = 1; c.mi_set[1] = 3; c.mi_set[2] = 5; c.n_mi_set = 3;
```

### ⑤ 负向对照

```c
/* -J 30 时每行必须出现精确后缀 */
expect(all_have("(plus up to 30s for jitter)"), "-J 30 每行都带抖动后缀", "");
/* 不带 -J 时输出里不得出现 jitter */
expect(strstr(buf, "jitter") == NULL, "无 -J 时不出现 jitter 后缀", "");
```

**只测"有"不测"没有"**，会让"恒为真"的实现蒙混过关。

## 实测结果

```
── snooze -n -d 1 -H 14 -M 15 echo hi
  [PASS] 第 1 行日 == 01
  [PASS] 第 1 行小时 == 14
  [PASS] 第 1 行分钟 == 15
  [PASS] 星期自洽 2026-10-01：打印 Thu / 独立计算 Thu
  ...
── snooze -n -H 99 echo hi
  [PASS] 退出码 (期望 1)
  [PASS] 报错含 "number outside 0 <= n < 24"
...
=== 汇总: 180 通过, 0 失败 ===
```

断言分布：字段约束与不变量约 160 条，非法模式 14 条（7 个越界选项 ×
退出码 + 精确范围文案），抖动后缀正/负向 3 条，无模式默认值 15 条。

## 可套用范围

| 工具 | 干跑开关 |
| --- | --- |
| snooze | `-n` |
| cron / anacron | 无（需靠 mock 时间） |
| systemd-timer | `systemd-analyze calendar` |
| `rsync` | `--dry-run` |
| `logrotate` | `-d`（debug，不实际轮转） |
| `find` | `-mtime` + 固定 `-newermt` 基准 |
| `date`/`cal`/`tzdata` 消费者 | `-d <固定时刻>` 显式传参，消除"现在" |
| 备份保留策略计算器 | 通常自带 `--dry-run` |

★ 通用原则：**把"当前时刻"从被测程序那里拿掉**——优先用工具的干跑开关；没有干跑
开关时用 `TZ` + 显式基准时间参数固定；两者都不可行时（如验证"延迟确实生效"），
显式放宽超时并把睡眠压到秒级，且在用例名里写明"该用例含真实睡眠"。

## 与其它判据的分工

| 判据 | 适用 |
| --- | --- |
| 往返一致性（`DRAFT-LUNAR-ROUNDTRIP-PROPERTY-CONSUMER-TEST`） | 可逆转换 |
| 结构不变量（`DRAFT-LETTERIZE-STRUCTURAL-INVARIANT-CONSUMER-TEST`） | 不可逆但输出有约束 |
| 两段式调用（`DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS`） | 有状态的修改类工具 |
| **干跑 + 独立历法交叉验证**（本条） | 输出与当前时刻相关 |

四者都不需要外部对照表；本条额外提供"**测试自身作为独立裁判**"的模式——
用另一份独立实现算出期望值，而不是抄被测程序的输出。

## 参考实现

- `archives/s/snooze/0.5/test_package/test_snooze.c` — 180 条断言
- `archives/s/snooze/0.5/test_package/conanfile.py` — 传参并执行（CI host==build 时真实运行）

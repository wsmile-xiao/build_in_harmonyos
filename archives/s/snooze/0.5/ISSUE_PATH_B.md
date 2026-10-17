# 路径 B 知识库扩展申请：时间/调度类工具的时间无关判据（干跑 + 独立历法交叉验证）

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#10770 snooze 0.5
- **关联 PR**：`!9xxx`（`feat/snooze-0.5`，配方 PR）
- **知识草稿**：`knowledge/drafts/snooze-0.5-timeless-dryrun-calendar-crosscheck.kv` / `.md`
- **草稿 ID**：`DRAFT-SNOOZE-TIMELESS-DRYRUN-CALENDAR-CROSSCHECK`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/snooze-0.5`）提交
- **申请日期**：2026-09-17

## 一、为什么这是"可跨仓库复用的知识"

本仓库所有 `test_package` 都要过 CI 的 L1「测试执行验证」。而**调度/时间类工具**
有两个与产物质量无关的失败面，它们会让绿灯失去意义甚至让 CI 挂死：

| 陷阱 | 后果 |
| --- | --- |
| 进入真实等待 | `snooze -H 0 -M 0 cmd` 会 sleep 到下一个 00:00（可能 19 小时），CI 超时判 fail |
| 硬编码时间戳 | 干跑输出随当前时刻滑动，快照式 golden **第二天自动变红**；时区差异（CI 常为 UTC）还会让写死 `+0800` 的断言直接失败 |

本条目给出一套**完全时间无关**的判据结构，并额外提供一种"**测试自身作为独立裁判**"
的模式：用另一份独立实现算出期望值，而不是抄被测程序的输出。它在 snooze 0.5 上
完整落地并通过 OHOS aarch64 实测（180/180）。

## 二、陷阱一：进入真实等待

```c
/* ❌ 会 sleep 到下一个匹配时刻 */
run_capture("-H 0 -M 0 echo hi", buf, sizeof(buf));
```

正确做法是**只用干跑模式**：`snooze -n` 打印"接下来 5 次会运行的时刻"并立即退出。
本包 180 条断言中**零次 sleep**。

## 三、陷阱二：硬编码时间戳

```bash
$ snooze -n -H 0 -M 0 echo hi | head -1
2026-09-19T00:00:00+0800 Sat  0d 19h 23m  9s
$ sleep 60; snooze -n -H 0 -M 0 echo hi | head -1
2026-09-19T00:00:00+0800 Sat  0d 19h 22m  9s      # 相对字段已变
```

一行自检：连续两次调用同一命令，首行有差异 → 必须改用不变量判据。

## 四、四条时间无关不变量

| 编号 | 不变量 | 说明 |
| --- | --- | --- |
| P1 | 干跑恰好输出 **5 行** | 上游 `-n` 的定义，行数本身就是契约 |
| P2 | 每行形状匹配 `YYYY-MM-DDTHH:MM:SS[+-]ZZZZ Ddd …` | **只校验结构，不校验数值**；时区偏移按 `[+-]\d{4}` 通配，CI 的 UTC 与本机 +0800 都能过 |
| P3 | 5 个时刻**严格递增** | 用 `days_from_civil` 折算成绝对秒后比较，跨月/跨年也成立 |
| P4 | 打印的星期缩写与日期**自洽** | 见第五节 |

## 五、P4 是核心：测试自身成为历法正确性的独立裁判

在测试里用 Howard Hinnant 的 `days_from_civil` **独立实现一遍**日期→星期换算：

```c
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

这样测试**不需要任何历法对照表**，就能在跨月、跨年、闰年边界上发现被测程序的日期
算术缺陷。实测（跨年点全覆盖）：

```
  [PASS] 星期自洽 2027-01-01：打印 Fri / 独立计算 Fri
  [PASS] 星期自洽 2027-04-10：打印 Sat / 独立计算 Sat
  [PASS] 星期自洽 2027-07-19：打印 Mon / 独立计算 Mon
  [PASS] 星期自洽 2028-01-01：打印 Sat / 独立计算 Sat
  [PASS] 星期自洽 2028-04-09：打印 Sun / 独立计算 Sun
```

年积日同样由测试独立算出（含闰年 366 天规则）：

```c
static int day_of_year(int y, int m, int d)
{
    static const int cum[12] = {0,31,59,90,120,151,181,212,243,273,304,334};
    int doy = cum[m-1] + d;
    if (m > 2 && is_leap(y)) doy++;
    return doy;
}
```

## 六、字段约束（含列表语法）

```c
/* -w 1-5 → 星期 ∈ {Mon..Fri} */
c.use_wmask = 1; c.wmask = (1<<1)|(1<<2)|(1<<3)|(1<<4)|(1<<5);
/* -D 1,100,200 → 年积日 ∈ {1,100,200} */
c.doy[0]=1; c.doy[1]=100; c.doy[2]=200; c.n_doy=3;
/* -M 1,3,5 → 分钟 ∈ {1,3,5} */
c.mi_set[0]=1; c.mi_set[1]=3; c.mi_set[2]=5; c.n_mi_set=3;
```

## 七、负向对照：只测"有"不测"没有"是不够的

```c
/* -J 30 时每行必须出现精确后缀 */
expect(all_have("(plus up to 30s for jitter)"), "-J 30 每行都带抖动后缀", "");
/* 不带 -J 时输出里不得出现 jitter */
expect(strstr(buf, "jitter") == NULL, "无 -J 时不出现 jitter 后缀", "");
```

缺少负向对照时，"恒为真"的实现会蒙混过关。

## 八、实测结果

```
=== snooze 0.5 消费者测试 ===
── snooze -n -d 1 -H 14 -M 15 echo hi
  [PASS] 行数 (期望 5)
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

**180 条断言，0 失败，零次真实睡眠**。断言分布：

| 分组 | 条数 |
| --- | --- |
| 时间模式字段约束与不变量（8 个模式用例） | ~160 |
| 非法模式（7 个越界选项 × 退出码 + 精确范围文案） | 14 |
| 抖动后缀正/负向对照 | 3 |
| 无模式时默认午夜每日 | 15 |

## 九、可套用范围

| 工具 | 干跑/固定时间手段 |
| --- | --- |
| snooze | `-n` |
| systemd-timer | `systemd-analyze calendar` |
| `rsync` | `--dry-run` |
| `logrotate` | `-d`（debug，不实际轮转） |
| `find` | `-mtime` + 固定 `-newermt` 基准 |
| `date`/`cal`/tzdata 消费者 | `-d <固定时刻>` 显式传参，消除"现在" |
| 备份保留策略计算器 | 通常自带 `--dry-run` |

★ 通用原则：**把"当前时刻"从被测程序那里拿掉**。优先用工具自带的干跑开关；没有时用
`TZ` + 显式基准时间参数固定；两者都不可行时（如验证"延迟确实生效"）显式放宽超时、
把睡眠压到秒级，并在用例名里写明"该用例含真实睡眠"。

## 十、与其它判据的分工

| 判据 | 适用 | 参考 |
| --- | --- | --- |
| 往返一致性 | 可逆转换（encode/decode） | `DRAFT-LUNAR-ROUNDTRIP-PROPERTY-CONSUMER-TEST` |
| 结构不变量 | 不可逆但输出有约束（枚举/展开） | `DRAFT-LETTERIZE-STRUCTURAL-INVARIANT-CONSUMER-TEST` |
| 两段式调用 | 有状态的修改类工具 | `DRAFT-PAXCTL-MUTATE-THEN-READ-SEPARATE-INVOCATIONS` |
| **干跑 + 独立历法交叉验证** | 输出与当前时刻相关 | 本条 |

四者都不需要外部对照表；本条额外提供"测试自身作为独立裁判"的模式。

## 十一、请主编审阅

本条草稿是**判据设计规约**，在 snooze 0.5 上完整落地并通过 OHOS aarch64 实测
（180/180）。若通过，请按 promote 流程转入正式知识库。

# DRAFT-kcalcore-5.116.0-qt5-qtimezone-zoneinfo-ldpreload-shim — Qt 5.15 QTimeZone 硬编码 zoneinfo 的 LD_PRELOAD 修复

> 草稿知识项 — Qt 5.15 线的 QTimeZone tz 后端把 zoneinfo 路径写死（无 QT_ZONEINFO
> 覆盖，那是 Qt 6.5+ 特性），OHOS 无 zoneinfo 数据库且 /usr 只读，命名时区构造
> 全部失效。对日历/时间类库（kcalcore 等）的连锁破坏是上游测试大面积失败与
> 递归死循环。修复模式：配方内嵌 libc 路径重定向 shim，LD_PRELOAD 注入
> conan tzdata 包的 zoneinfo 树。
> 来源：kcalcore 5.116.0 适配（任务 #7770，j669539，2026-10-04）
> 同 stem 配对：`knowledge/drafts/DRAFT-kcalcore-5.116.0-qt5-qtimezone-zoneinfo-ldpreload-shim.kv`

## 问题（现象 / error_signature）

Qt5 日历类库的上游数据驱动测试在 OHOS 上大面积失败：

```
# 单测输出侧（期望 "PDT America/Los_Angeles"，实际）：
1997-09-02T09:00:00 GMT

# ctest 侧：
191/497 注册项失败；testrecurson 在 TZID=America/Denver 的月度递归上
100% CPU 9+ 分钟不退出（正常 0.16s）——ctest 整体挂死
```

Qt 侧根因证据（qtbase 5.15.2 源码 src/corelib/time/qtimezoneprivate_tz.cpp）：

```cpp
// loadTzTimeZones():
QString path = QStringLiteral("/usr/share/zoneinfo/zone.tab");
if (!QFile::exists(path))
    path = QStringLiteral("/usr/lib/zoneinfo/zone.tab");
// QTzTimeZoneCache::findEntry():
tzif.setFileName(QLatin1String("/usr/share/zoneinfo/") + QString::fromLocal8Bit(ianaId));
// 5.15 全源码 grep "QT_ZONEINFO|TZDIR|qEnvironmentVariable" → 零命中（无任何覆盖通道）
```

## 根因（root_cause）

1. Qt 5.15 tz 后端的三个硬编码路径：`/usr/share/zoneinfo/zone.tab`（可用性哈希源，
   失败回退 `/usr/lib/zoneinfo/zone.tab`）、`/usr/share/zoneinfo/<ianaId>`（每时区
   TZif 文件，回退 `/usr/lib/zoneinfo/<id>`）、`/etc/localtime`（系统时区）。
   **QT_ZONEINFO 覆盖是 Qt 6.5+ 特性，5.15 源码中不存在**（grep 实证）——Qt6 线
   配方（kcalendarcore 6.26.0）设 env 即可，Qt5 线没有这个通道。
2. OHOS 不带 zoneinfo 数据库，且 `/usr` 只读（`mkdir: Read-only file system`），
   无法像 Linux 发行版那样放置数据库。
3. 连锁破坏（kcalcore 实测）：`readICalDateTime` 中 `QTimeZone(tzid)` 构造无效 →
   `QDateTime` 回退 LocalTime → 递归展开跨时区边界永不收敛：191/497 失败 +
   testrecurson 死循环；输出特征是命名时区行全变 `GMT`。
4. TZDIR 对 Qt5 命名时区查找**无效**（Qt5 直接读文件不走 TZDIR；TZDIR 只影响
   musl localtime_r 通道）——踩坑点：先设了 TZDIR+QT_ZONEINFO 完全无效。

## 修复（solution）

配方内嵌 ~180 行 `zoneinfo_redirect.c`（ZONEINFO_SHIM_SOURCE），构建期用 profile 的
OHOS clang（`tools.build:compiler_executables` 的 c + `--target=aarch64-linux-ohos`）
编译为 `zoneinfo_redirect.so`，ctest 环境 `LD_PRELOAD=<shim>` +
`KCALCORE_ZONEINFO_DIR=<tzdata conan 包 zoneinfo 树>`：

- 拦截九个路径类 libc 调用（libQt5Core 实际 UND 导入面）：open/openat/fopen/
  stat/lstat/fstatat/access/faccessat/opendir，`dlsym(RTLD_NEXT)` 转发
  （authbind 先例）
- 仅 `/usr/share/zoneinfo` 与 `/usr/lib/zoneinfo` 两前缀命中重写为
  `$KCALCORE_ZONEINFO_DIR + 后缀`，其余路径原样放行（零污染）
- tzdata/2026.3 包自带 zone.tab（可用性哈希源）与全部 IANA TZif
- `ctest --timeout 120` 兜底第二道防线；`TZ=UTC` 固定本地时区

验证链（单点对照 → 全量）：

```
无 shim：  1997-09-02T09:00:00 GMT        （1 行，错）
带 shim：  1997-09-02T09:00:00 PDT America/Los_Angeles  （8 行，与 .ref 逐行一致）
死循环项： ConnectDaily2.ics 带 shim 秒级完成（100% CPU 9min → <1s）
全量：    ctest 191 失败 → 492/492 全过（497 注册，5 项 tzdata 快照差异另行排除定性）
```

## 边界与排除（修复后仍不过的 5 项，tzdata 快照差异定性）

| 测试 | 差异 |
|------|------|
| testicaltimezones.write() | QTimeZone("Europe/Prague") 序列化对照旧时区库录的 VTIMEZONE 快照，RRULE 分段不同（6.26.0 线同款排除先例） |
| RecurNext/RecurPrev-LibICal_TestCase44 | 远期日期 2032-11-02 的缩写（PDT/PST）取决于最后转移之外的表示：tzdata 2026.3 slim TZif 带 POSIX footer 而 Qt 5.15 tz 后端不外推 |
| Compat-AppleICal_1.5 / Compat-MSExchange | VTIMEZONE 往返内嵌同样的历史转移分段差异（6.26.0 线同款排除 AppleICal） |

## 回退（fallback）

若目标场景不能注入 LD_PRELOAD：(1) 构建期 patch qtbase 的
qtimezoneprivate_tz.cpp 自造环境变量覆盖（代价：qtbase 包不能用 registry 二进制）；
(2) 命名时区用例全部按"环境限制"排除申报（损失大块真实覆盖，最后手段）。
禁止写 /usr/share/zoneinfo（只读）；禁止指望 TZDIR 影响 Qt5 命名时区（实测无效）。

## 验证与参考实现

- verify_builds: kcalcore/5.116.0 本地 conan create（qt5-qtbase/5.15.2.2 +
  libical3/3.0.20 + tzdata/2026.3 图）——round6 `100% tests passed, 0 tests
  failed out of 492`；round8 RC=0，test_package 15/15
- reference_impl: `archives/k/kcalcore/5.116.0/conanfile.py`（ZONEINFO_SHIM_SOURCE
  内嵌 + `_build_zoneinfo_shim()` + `_run_upstream_tests()` 注入）
- 拦截先例：`archives/a/authbind/2.2.0`（dlsym RTLD_NEXT）；构建期 LD_PRELOAD
  先例：`archives/b/baloo/26.04.3`（passwd_shim.so）；Qt6 对照（设 env 即可）：
  `archives/k/kcalendarcore/6.26.0`

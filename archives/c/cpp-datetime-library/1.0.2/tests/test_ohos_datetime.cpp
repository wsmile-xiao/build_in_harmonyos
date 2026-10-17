/* 鸿蒙专项测试 — cpp-datetime-library 1.0.2
 *
 * 验证在 HarmonyOS（musl libc + clang）目标平台上：
 *   1. 库的公开头文件可编译、静态库可链接、可运行；
 *   2. 日期时间运算（闰年/加天数/格式化）在 OHOS 上输出与
 *      上游一致的平台无关结果（纯算法，无平台特定 API）；
 *   3. 与 time_t/ctime 互操作的公有 API（to_string 格式）行为正确。
 *
 * 仅使用库安装的公开头文件（datetime.h/timespan.h）与公开 API。
 */
#include <cassert>
#include <cstdio>
#include <string>

#include <datetime/datetime.h>
#include <datetime/timespan.h>

using namespace jed_utils;

int main() {
    int failures = 0;

    /* 1) 闰年判定（纯算法，OHOS 平台上应与上游一致） */
    if (!datetime::is_leapyear(2000) || datetime::is_leapyear(1900) ||
        !datetime::is_leapyear(2024) || datetime::is_leapyear(2023)) {
        std::printf("[OHOS-fail] leapyear logic mismatch\n");
        ++failures;
    }

    /* 2) 日期加法跨月/跨年（内部日历重算，验证 OHOS 上的算术一致） */
    datetime dt(2016, 12, 15);
    dt.add_days(30);            /* 越过 2016 年尾 */
    if (dt.get_year() != 2017 || dt.get_month() != 1 || dt.get_day() != 14) {
        std::printf("[OHOS-fail] add_days crossing year: %d-%d-%d\n",
                    dt.get_year(), dt.get_month(), dt.get_day());
        ++failures;
    }

    /* 3) 12 小时制 period -> 24 小时转换与格式化 */
    datetime pm(2024, 3, 5, 9, 30, 0, period::PM);
    std::string iso = pm.to_string("yyyy-MM-dd HH:mm:ss");
    if (iso != "2024-03-05 21:30:00") {
        std::printf("[OHOS-fail] PM format: %s\n", iso.c_str());
        ++failures;
    }

    /* 4) timespan 运算（纯整数，检查字节序无关性） */
    timespan ts(0, 23, 59, 58);
    if (ts.get_total_seconds() != 23 * 3600 + 59 * 60 + 58) {
        std::printf("[OHOS-fail] timespan total seconds: %d\n",
                    ts.get_total_seconds());
        ++failures;
    }

    /* 5) datetime - datetime => timespan 差值（跨天） */
    datetime a(2024, 3, 10, 12, 0, 0);
    datetime b(2024, 3, 8, 12, 0, 0);
    timespan d = a - b;
    if (d.get_days() != 2) {
        std::printf("[OHOS-fail] date diff days: %d\n", d.get_days());
        ++failures;
    }

    if (failures == 0) {
        std::printf("[OHOS-PASS] cpp-datetime-library on OHOS: all 5 checks OK\n");
        return 0;
    }
    std::printf("[OHOS-FAIL] %d check(s) failed\n", failures);
    return 1;
}
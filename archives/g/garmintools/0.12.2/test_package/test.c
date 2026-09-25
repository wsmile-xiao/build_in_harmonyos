/*
 * test_garmintools — Conan L1 consumer test (test_package)
 *
 * 通过 garmintools 已安装的公开头文件 <garmintools/garmin.h> 与
 * libgarmintools 链接，调用公开 API：
 *   - garmin_lpid():  garmin_pid -> 链路层 packet id（协议映射）
 *   - garmin_gpid():  链路层 packet id -> garmin_pid（协议映射，round-trip）
 *   - garmin_load():  加载不存在的 .gmn 文件应返回 NULL（错误路径）
 * 验证第三方使用者可编译、链接、调用并得到可观察结果。
 */
#include <garmintools/garmin.h>
#include <stdio.h>
#include <stdlib.h>

static int failures = 0;

static void check(int cond, const char *what) {
    if (cond) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

int main(void) {
    uint16 lpid;
    garmin_pid gpid;

    /* 1. garmin_pid -> link L001 链路包 ID */
    lpid = garmin_lpid(link_L001, Pid_Wpt_Data);
    check(lpid == L001_Pid_Rte_Wpt_Data,
          "garmin_lpid(link_L001, Pid_Wpt_Data) == L001_Pid_Rte_Wpt_Data");

    /* 2. round-trip: 链路包 ID -> garmin_pid
       （上游映射非对称：Pid_Wpt_Data 在 L001 链路层与航路点共用
       L001_Pid_Rte_Wpt_Data，逆向解析回 Pid_Rte_Wpt_Data） */
    gpid = garmin_gpid(link_L001, L001_Pid_Rte_Wpt_Data);
    check(gpid == Pid_Rte_Wpt_Data,
          "garmin_gpid(link_L001, L001_Pid_Rte_Wpt_Data) == Pid_Rte_Wpt_Data");

    /* 3. link L002 协议映射 */
    lpid = garmin_lpid(link_L002, Pid_Position_Data);
    check(lpid == L002_Pid_Position_Data,
          "garmin_lpid(link_L002, Pid_Position_Data) == L002_Pid_Position_Data");

    /* 4. 未知 packet id 应映射为 0（无匹配） */
    lpid = garmin_lpid(link_L001, Pid_Nil);
    check(lpid == 0x0000, "garmin_lpid(link_L001, Pid_Nil) == 0x0000");

    /* 5. garmin_load 对不存在的文件返回 NULL（错误路径可观察） */
    check(garmin_load("/nonexistent/garmin_consumer_test.gmn") == NULL,
          "garmin_load() on missing file returns NULL");

    if (failures == 0) {
        printf("test_garmintools: ALL %d CHECKS PASSED\n", 5);
        return 0;
    }
    printf("test_garmintools: %d CHECK(S) FAILED\n", failures);
    return 1;
}

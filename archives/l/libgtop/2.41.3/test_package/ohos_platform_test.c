/*
 * HarmonyOS 专项测试 — libgtop on OHOS platform integration.
 *
 * 与消费者冒烟测试（test_consumer.c，仅验 CPU/mem/uptime 非零）不同，本用例
 * 专门覆盖 OHOS 内核（HongMeng Kernel）上容易出问题的平台集成点：
 *   1. glibtop_get_proclist   — 从 /proc 枚举真实进程表
 *   2. glibtop_get_proc_state — 读取首个进程的 uid/gid/state（/proc/<pid>/stat）
 *   3. glibtop_get_sysinfo    — 系统信息（ncpu/cpuinfo，OHOS 上
 *                               release=HongMeng Kernel 1.12.0 版本码解析为 0）
 *   4. glibtop_get_netlist    — 通过 /sys/class/net 实际枚举网络设备
 *   5. glibtop_get_mountlist  — /proc/self/mounts 挂载点枚举
 * 全部使用 libgtop 公开 API 与已安装头文件，作为"第三方使用者"在 HarmonyOS
 * 上真实调用并验证可观察结果。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <glibtop.h>
#include <glibtop/proclist.h>
#include <glibtop/procstate.h>
#include <glibtop/sysinfo.h>
#include <glibtop/netlist.h>
#include <glibtop/mountlist.h>

static int failures = 0;

static void check(int ok, const char *fmt, unsigned long a, unsigned long b)
{
    if (!ok) {
        failures++;
        fprintf(stderr, "OHOS test FAIL: ");
        fprintf(stderr, fmt, a, b);
        fprintf(stderr, "\n");
    }
}

int main(void)
{
    glibtop *server;
    unsigned long total = 0;

    server = glibtop_init();
    if (server == NULL) {
        fprintf(stderr, "OHOS test: glibtop_init failed\n");
        return 1;
    }

    /* 1. 进程表枚举（/proc） */
    {
        glibtop_proclist plist;
        pid_t *pids = glibtop_get_proclist(&plist, 0, 0);
        total++;
        check(pids != NULL && plist.number > 0,
              "proclist empty or NULL (number=%lu,%lu)", plist.number, 0);
        printf("OHOS test OK: proclist %llu processes\n",
               (unsigned long long)plist.number);

        /* 2. 读取当前进程的 proc state（/proc/<pid>/stat 解析）。
         * OHOS 限制普通用户读取 /proc/1/stat 等系统进程（Permission denied），
         * 用 getpid() 自身进程验证（上游示例同样可读自身）。*/
        {
            glibtop_proc_state ps;
            glibtop_get_proc_state(&ps, getpid());
            total++;
            check(ps.state != 0 && ps.uid >= 0,
                  "proc_state invalid (state=%lu,uid=%lu)",
                  (unsigned long)ps.state, (unsigned long)ps.uid);
            printf("OHOS test OK: proc_state pid=%d cmd=%s uid=%d state=%u\n",
                   (int)getpid(), ps.cmd, ps.uid, ps.state);
        }
    }

    /* 3. sysinfo（uname 语义，OHOS HongMeng Kernel 版本码为 0 的告警场景）*/
    {
        const glibtop_sysinfo *si = glibtop_get_sysinfo();
        total++;
        check(si != NULL && si->ncpu > 0,
              "sysinfo NULL or ncpu=0 (%p,%lu)", (unsigned long)si, si ? si->ncpu : 0);
        if (si)
            printf("OHOS test OK: sysinfo ncpu=%llu\n",
                   (unsigned long long)si->ncpu);
    }

    /* 4. 网络设备枚举（/sys/class/net）*/
    {
        glibtop_netlist nl;
        char **devs = glibtop_get_netlist(&nl);
        total++;
        check(devs != NULL && nl.number > 0,
              "netlist empty or NULL (number=%lu,%lu)", nl.number, 0);
        if (devs != NULL && nl.number > 0)
            printf("OHOS test OK: netlist %u devices (first=%s)\n",
                   nl.number, devs[0]);
    }

    /* 5. 挂载点枚举。上游示例传 all_fs=1 走 /proc/self/mounts（OHOS 无
     * /etc/mtab，all_fs=0 会读 /etc/mtab 而失败）。*/
    {
        glibtop_mountlist ml;
        glibtop_mountentry *mounts = glibtop_get_mountlist(&ml, 1);
        total++;
        check(mounts != NULL && ml.number > 0,
              "mountlist empty or NULL (number=%lu,%lu)", ml.number, 0);
        if (mounts != NULL && ml.number > 0)
            printf("OHOS test OK: mountlist %llu mounts (first=%s)\n",
                   (unsigned long long)ml.number, mounts[0].mountdir);
    }

    glibtop_close();

    printf("OHOS test summary: %lu assertions, %d failures\n", total, failures);
    return failures == 0 ? 0 : 1;
}
/* 鸿蒙（OHOS）特有测试用例 —— libgtop2 在 OHOS 上走 sysdeps/linux 的 procfs 实现，
 * 本用例断言鸿蒙内核下 /proc 语义可被 libgtop2 正确采集（Linux 上同样成立，但断言
 * 目标是 OHOS 的 procfs 语义，故在 OHOS 平台为必跑用例）：
 *
 *   1) uname 报告的内核标识被打印（CI 日志中确认运行平台）
 *   2) glibtop_get_sysinfo()->ncpu >= 1   —— OHOS aarch64 多核拓扑可读
 *      （数据源：/proc/cpuinfo，见 sysdeps/linux/sysinfo.c）
 *   3) glibtop_get_cpu().xcpu_total[0] > 0 —— /proc/stat 每 CPU 行可解析
 *   4) glibtop_get_proclist() 枚举到 >= 1 个进程 —— /proc/<pid> 可遍历
 *      （数据源：/proc 目录扫描，见 sysdeps/linux/proclist.c）
 *
 * 全部断言通过 → 退出码 0；任一失败 → 退出码 1。
 */
#include <glibtop.h>
#include <glibtop/cpu.h>
#include <glibtop/proclist.h>
#include <glibtop/sysinfo.h>

#include <stdio.h>
#include <sys/utsname.h>
#include <unistd.h>

static int failures;

static void check(int ok, const char *what)
{
	printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
	if (!ok)
		failures++;
}

int main(void)
{
	struct utsname uts;
	glibtop_cpu cpu;
	glibtop_proclist proclist;
	const glibtop_sysinfo *info;
	pid_t *pids;

	glibtop_init();

	if (uname(&uts) == 0)
		printf("kernel: %s %s (%s)\n", uts.sysname, uts.release, uts.machine);

	glibtop_get_cpu(&cpu);
	check(cpu.xcpu_total[0] > 0, "OHOS: /proc/stat per-cpu ticks readable");

	info = glibtop_get_sysinfo();
	check(info != NULL && info->ncpu >= 1, "OHOS: sysinfo ncpu >= 1");

	pids = glibtop_get_proclist(&proclist, GLIBTOP_KERN_PROC_ALL, 0);
	check(pids != NULL && proclist.number >= 1,
	      "OHOS: /proc process table enumerable");
	if (pids != NULL) {
		printf("OHOS: proclist number=%llu\n",
		       (unsigned long long) proclist.number);
		g_free(pids);
	}

	return failures ? 1 : 0;
}

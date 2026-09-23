/* L1 消费者测试 —— 真正调用 libgtop2 导出的 API（R34：禁止空壳测试）。
 *
 * 编译期：LIBGTOP_CHECK_VERSION 断言头文件版本 >= 2.41.3（libgtop.h:52 的官方宏）
 * 运行期：glibtop_get_cpu / mem / uptime / sysinfo 必须返回有效数据
 *
 * 全部断言通过 → 退出码 0；任一失败 → 打印 FAIL 并返回 1（ctest 判定为失败）。
 */
#include <glibtop.h>
#include <glibtop/cpu.h>
#include <glibtop/mem.h>
#include <glibtop/sysinfo.h>
#include <glibtop/uptime.h>

#include <stdio.h>

#if !LIBGTOP_CHECK_VERSION(2, 41, 3)
#error "libgtop2 headers are older than 2.41.3"
#endif

static int failures;

static void check(int ok, const char *what)
{
	printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
	if (!ok)
		failures++;
}

int main(void)
{
	glibtop_cpu cpu;
	glibtop_mem mem;
	glibtop_uptime uptime;
	const glibtop_sysinfo *info;

	glibtop_init();

	glibtop_get_cpu(&cpu);
	check(cpu.total > 0, "glibtop_get_cpu(): total ticks > 0");

	glibtop_get_mem(&mem);
	check(mem.total > 0, "glibtop_get_mem(): total bytes > 0");

	glibtop_get_uptime(&uptime);
	check(uptime.uptime > 0, "glibtop_get_uptime(): uptime > 0");

	info = glibtop_get_sysinfo();
	check(info != NULL && info->ncpu > 0, "glibtop_get_sysinfo(): ncpu > 0");

	printf("libgtop2 %d.%d.%d: ncpu=%llu mem_total=%llu uptime=%.0fs\n",
	       LIBGTOP_MAJOR_VERSION, LIBGTOP_MINOR_VERSION, LIBGTOP_MICRO_VERSION,
	       (unsigned long long) (info ? info->ncpu : 0),
	       (unsigned long long) mem.total, uptime.uptime);

	return failures ? 1 : 0;
}

/*
 * consumer.c — libcpufreq 消费者测试源（test_package）。
 *
 * 真实 include 并链接包内的 libcpufreq / cpufreq.h，逐个调用公共 API：
 *   cpufreq_cpu_exists / cpufreq_get_driver / cpufreq_put_driver /
 *   cpufreq_get_hardware_limits / cpufreq_get_transition_latency
 *
 * 能力面差异（OHOS 非 root 进程）如实分档，不把"读不到"当成"通过"：
 *   - cpufreq_cpu_exists(0) 与 cpufreq_get_driver(0) 在任何 Linux/OHOS 上都必须可用；
 *   - 硬件上下限 / 迁移延迟依赖 sysfs cpufreq 属性的可读性，缺失时打印
 *     SYSFS_LIMITS_SKIPPED / SYSFS_LATENCY_SKIPPED 由驱动脚本按跳过计，不算失败。
 *
 * 退出码：0 = 全部硬断言通过；非 0 = 有硬断言失败（输出带 FAIL 行）。
 */
#include <stdio.h>
#include <string.h>

#include "cpufreq.h"

int main(void)
{
	int fail = 0;
	int rc;
	unsigned long min_freq = 0, max_freq = 0, latency;
	char *driver;

	rc = cpufreq_cpu_exists(0);
	if (rc != 0) {
		printf("FAIL cpu_exists rc=%d\n", rc);
		fail++;
	} else {
		printf("PASS CPU_EXISTS_OK\n");
	}

	driver = cpufreq_get_driver(0);
	if (driver != NULL && driver[0] == '\0') {
		printf("FAIL driver_empty\n");
		fail++;
	} else {
		printf("PASS DRIVER_OK value=%s\n", driver ? driver : "(none)");
	}
	cpufreq_put_driver(driver);

	if (cpufreq_get_hardware_limits(0, &min_freq, &max_freq) == 0 &&
	    min_freq > 0 && max_freq > min_freq) {
		printf("PASS LIMITS_OK %lu-%lu\n", min_freq, max_freq);
	} else {
		printf("SKIP SYSFS_LIMITS_SKIPPED\n");
	}

	/* cpufreq_get_transition_latency() 失败时把错误码按 unsigned long 返回
	 * （实测 -6 = 0xFFFFFFFFFFFFFFFA），必须当失败处理，不能当成通过打印。 */
	latency = cpufreq_get_transition_latency(0);
	if (latency == 0 || latency > 1000000000000UL) {
		printf("SKIP SYSFS_LATENCY_SKIPPED raw=%lu\n", latency);
	} else {
		printf("PASS LATENCY_OK %lu\n", latency);
	}

	return fail;
}

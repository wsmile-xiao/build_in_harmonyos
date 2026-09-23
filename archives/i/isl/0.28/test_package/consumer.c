/*
 * consumer.c — isl 0.28 消费者用例（test_package L1 测试）
 *
 * 模拟业务上层组件（如编译器多面体调度器）：仅使用 isl 已安装的公开头文件
 * 与公开 API，通过正常链接目标（isl::isl / -lisl）编译、链接、运行，
 * 验证第三方使用者对 isl 的可用性：
 *   1. 解析迭代域与依赖关系（isl_union_set / isl_union_map 公开 API）
 *   2. 由域 + 依赖约束计算调度（isl_schedule_constraints_compute_schedule）
 *   3. 输出调度并对已知点做可观察断言
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <isl/ctx.h>
#include <isl/union_set.h>
#include <isl/union_map.h>
#include <isl/schedule.h>

int main(void)
{
	isl_ctx *ctx;
	isl_union_set *domain;
	isl_union_map *validity;
	isl_schedule_constraints *sc;
	isl_schedule *schedule;
	char *sched_str;
	int failed = 0;

	ctx = isl_ctx_alloc();
	assert(ctx);

	/* 模拟一个 2 层循环嵌套 S0[i,j] 的迭代域 */
	domain = isl_union_set_read_from_str(
	    ctx, "{ S0[i, j] : 0 <= i <= 3 and 0 <= j <= 3 }");
	assert(domain);

	/* 模拟循环携带依赖 S0[i,j] -> S0[i+1,j] */
	validity = isl_union_map_read_from_str(
	    ctx, "{ S0[i, j] -> S0[i + 1, j] : 0 <= i <= 2 and 0 <= j <= 3 }");
	assert(validity);

	/* 由域 + 合法性约束计算调度 */
	sc = isl_schedule_constraints_on_domain(domain);
	sc = isl_schedule_constraints_set_validity(sc, validity);
	schedule = isl_schedule_constraints_compute_schedule(sc);
	assert(schedule);

	sched_str = isl_schedule_to_str(schedule);
	printf("[consumer] computed schedule: %s\n", sched_str ? sched_str : "(null)");

	/* 可观察断言：调度必须非空且包含期望的语句标识 S0 */
	if (sched_str == NULL || strstr(sched_str, "S0") == NULL) {
		printf("[consumer] FAIL: schedule does not mention S0\n");
		failed = 1;
	} else {
		printf("[consumer] PASS: schedule contains S0\n");
	}

	free(sched_str);
	isl_schedule_free(schedule);
	isl_ctx_free(ctx);

	if (failed == 0)
		printf("[consumer] ALL consumer checks PASSED\n");
	return failed;
}

/* test_package 消费者测试：通过公开头文件 lcrq.h 调用 lcrq 公开 API。
 * 实质断言（非空壳，R34）：
 *  1. rq_init/rq_free        — RaptorQ 上下文生命周期（分配内部矩阵/队列）
 *  2. rq_oti                 — 导出 OTI（Out-of-band Transmission Information）
 *  3. rq_oti_F/rq_oti_T      — OTI 反解回原始参数（F/T 往返一致）
 *  4. rq_F/rq_T/rq_Z/rq_N/rq_K — 内部参数查询 API 返回合理值
 * 纯算法路径，无网络依赖。
 */
#include <stdio.h>
#include <stdint.h>
#include <lcrq.h>

int main(void)
{
	int errors = 0;
	const uint64_t F = 1024;  /* 传输长度（字节） */
	const uint16_t T = 1024;  /* 符号大小（字节） */
	rq_t *rq = NULL;
	rq_oti_t oti = 0;
	rq_scheme_t scheme = 0;

	/* 1. 上下文生命周期 */
	rq = rq_init(F, T);
	if (rq == NULL) {
		fprintf(stderr, "FAIL: rq_init(F=%llu, T=%u) returned NULL\n",
		        (unsigned long long)F, (unsigned)T);
		return 1;
	}

	/* 2. OTI 导出 */
	if (rq_oti(rq, &oti, &scheme) != 0) {
		fprintf(stderr, "FAIL: rq_oti() returned non-zero\n");
		errors++;
	}

	/* 3. OTI 反解：F/T 必须与原始参数一致 */
	if (errors == 0) {
		uint64_t F2 = rq_oti_F(oti);
		uint16_t T2 = rq_oti_T(oti);
		if (F2 != F) {
			fprintf(stderr, "FAIL: rq_oti_F()=%llu != %llu\n",
			        (unsigned long long)F2, (unsigned long long)F);
			errors++;
		}
		if (T2 != T) {
			fprintf(stderr, "FAIL: rq_oti_T()=%u != %u\n",
			        (unsigned)T2, (unsigned)T);
			errors++;
		}
	}

	/* 4. 内部参数查询 API（新增消费者用例）：
	 * rq_F/rq_T 应返回构造参数；rq_Z/rq_N/rq_K 应返回 RFC6330 分区的正值。 */
	if (rq_F(rq) != F) {
		fprintf(stderr, "FAIL: rq_F()=%llu != %llu\n",
		        (unsigned long long)rq_F(rq), (unsigned long long)F);
		errors++;
	}
	if (rq_T(rq) != T) {
		fprintf(stderr, "FAIL: rq_T()=%u != %u\n", (unsigned)rq_T(rq), (unsigned)T);
		errors++;
	}
	if (rq_Z(rq) == 0) {
		fprintf(stderr, "FAIL: rq_Z()=0 (expected non-zero source block count)\n");
		errors++;
	}
	if (rq_N(rq) == 0) {
		fprintf(stderr, "FAIL: rq_N()=0 (expected non-zero sub-block count)\n");
		errors++;
	}
	if (rq_K(rq) == 0) {
		fprintf(stderr, "FAIL: rq_K()=0 (expected non-zero source symbol count)\n");
		errors++;
	}

	rq_free(rq);

	if (errors) return 1;
	printf("lcrq consumer test passed: rq_init/rq_oti/rq_oti_F/rq_oti_T/"
	       "rq_F/rq_T/rq_Z/rq_N/rq_K/rq_free OK\n");
	return 0;
}

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "fml.h"

/* 实质消费者测试：构造 120 条 100bp 模拟短读（同一 200bp 随机模板 + 2% 错误 +
 * 随机起点/反向），调用 fermi-lite 组装 API，验证产出非空 unitig
 * （R34：必须实质调用被测包 API；本地验证 n_utg=2、ok=1）。
 *
 * 注意：fml_assemble() 文档约定 seqs 数组 "FREED on return"
 * （内部 fml_seq2fmi 会 free(seq) 与每个 s->seq/s->qual），
 * 因此 seqs 必须堆分配，且返回后不得再访问。 */

static uint32_t g_seed = 7;
static uint32_t rng(void)
{
	g_seed = g_seed * 1664525u + 1013904223u;
	return g_seed;
}

#define TPL_LEN 200
#define RD_LEN  100
#define N_RDS   120

int main(void)
{
	fml_opt_t opt;
	bseq1_t *seqs;
	fml_utg_t *utgs;
	char tpl[TPL_LEN];
	int n_utg = 0, i, j, ok = 0;

	/* 确定性生成 200bp 随机模板 */
	for (i = 0; i < TPL_LEN; ++i)
		tpl[i] = "ACGT"[rng() % 4];

	seqs = (bseq1_t*)calloc(N_RDS, sizeof(bseq1_t));
	if (seqs == 0) return 1;
	for (i = 0; i < N_RDS; ++i) {
		int start = rng() % (TPL_LEN - RD_LEN);
		char *s = (char*)malloc(RD_LEN + 1);
		for (j = 0; j < RD_LEN; ++j) s[j] = tpl[(start + j) % TPL_LEN];
		if (rng() & 1) { /* 随机反向 */
			for (j = 0; j < RD_LEN / 2; ++j) {
				char t = s[j]; s[j] = s[RD_LEN - 1 - j]; s[RD_LEN - 1 - j] = t;
			}
		}
		for (j = 0; j < RD_LEN; ++j) /* 2% 测序错误 */
			if (rng() % 100 < 2) s[j] = "ACGT"[rng() % 4];
		s[RD_LEN] = 0;
		seqs[i].l_seq = RD_LEN;
		seqs[i].seq = s;
		seqs[i].qual = strdup("IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII");
	}

	fml_opt_init(&opt);
	utgs = fml_assemble(&opt, N_RDS, seqs, &n_utg);
	if (utgs == 0) {
		fprintf(stderr, "fml_assemble returned NULL\n");
		return 1;
	}
	for (i = 0; i < n_utg; ++i)
		if (utgs[i].len > 0 && utgs[i].seq != 0) ok = 1;
	fml_utg_destroy(n_utg, utgs);
	if (ok) {
		printf("fermi-lite test_package: assembled %d unitig(s)\n", n_utg);
		return 0;
	}
	fprintf(stderr, "no non-empty unitig produced\n");
	return 1;
}

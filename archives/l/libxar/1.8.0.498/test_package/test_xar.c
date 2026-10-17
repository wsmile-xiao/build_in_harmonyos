/*
 * test_xar.c — libxar 1.8.0.498 consumer test (L0c/R34)
 *
 * 真实调用 libxar API：以 none/gzip/bzip2 三种编码 + sha1/sha256/sha512
 * TOC 校验和创建档案，再读回比对内容并做 xar_verify 校验——覆盖 zlib、
 * bzip2 与 openssl(libcrypto 摘要) 全部依赖链路。
 * （lzma 编码上游 498 默认未启用——lzmaxar.c 依赖 2006 年 LZMA SDK API）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <xar/xar.h>

static const char *CONTENT =
    "hello from libxar HarmonyOS consumer test - "
    "0123456789 abcdefghijklmnopqrstuvwxyz "
    "0123456789 abcdefghijklmnopqrstuvwxyz\n";

static int roundtrip(const char *compression, const char *toc_cksum)
{
	FILE *fp = fopen("probe.txt", "w");
	if (!fp) {
		perror("fopen probe.txt");
		return 10;
	}
	fputs(CONTENT, fp);
	fclose(fp);

	xar_t xw = xar_open("probe.xar", WRITE);
	if (!xw) {
		fprintf(stderr, "xar_open WRITE failed\n");
		return 11;
	}
	if (xar_opt_set(xw, XAR_OPT_COMPRESSION, compression) != 0) {
		fprintf(stderr, "xar_opt_set compression=%s failed\n", compression);
		return 12;
	}
	if (xar_opt_set(xw, XAR_OPT_TOCCKSUM, toc_cksum) != 0) {
		fprintf(stderr, "xar_opt_set toc-cksum=%s failed\n", toc_cksum);
		return 13;
	}
	if (!xar_add(xw, "probe.txt")) {
		fprintf(stderr, "xar_add failed\n");
		return 14;
	}
	if (xar_close(xw) != 0) {
		fprintf(stderr, "xar_close failed\n");
		return 15;
	}

	xar_t xr = xar_open("probe.xar", READ);
	if (!xr) {
		fprintf(stderr, "xar_open READ failed\n");
		return 16;
	}
	xar_iter_t it = xar_iter_new();
	if (!it) {
		fprintf(stderr, "xar_iter_new failed\n");
		return 17;
	}
	xar_file_t rf = xar_file_first(xr, it);
	if (!rf) {
		fprintf(stderr, "archive has no files\n");
		return 18;
	}
	char *buf = NULL;
	if (xar_extract_tobuffer(xr, rf, &buf) != 0) {
		fprintf(stderr, "xar_extract_tobuffer failed\n");
		return 19;
	}
	if (!buf || strncmp(buf, CONTENT, strlen(CONTENT)) != 0) {
		fprintf(stderr, "extracted content mismatch\n");
		return 20;
	}
	free(buf);
	if (xar_verify(xr, rf) != 0) {
		fprintf(stderr, "xar_verify failed\n");
		return 21;
	}
	xar_iter_free(it);
	xar_close(xr);
	unlink("probe.xar");
	return 0;
}

int main(void)
{
	static const struct {
		const char *compression;
		const char *toc_cksum;
	} cases[] = {
		{ XAR_OPT_VAL_NONE, XAR_OPT_VAL_SHA1 },
		{ XAR_OPT_VAL_GZIP, XAR_OPT_VAL_SHA256 },
		{ XAR_OPT_VAL_BZIP, XAR_OPT_VAL_SHA512 },
	};
	for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
		int rc = roundtrip(cases[i].compression, cases[i].toc_cksum);
		if (rc != 0) {
			fprintf(stderr, "FAIL: compression=%s toc=%s rc=%d\n",
				cases[i].compression, cases[i].toc_cksum, rc);
			return rc;
		}
		printf("PASS: compression=%s toc=%s\n",
		       cases[i].compression, cases[i].toc_cksum);
	}
	printf("libxar consumer round-trip OK (3 cases)\n");
	return 0;
}

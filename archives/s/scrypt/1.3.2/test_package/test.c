#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/*
 * scrypt 1.3.2 test_package L1 测试 — 消费者视角验证 CLI 工具。
 *
 * 逐步断言（R02 修复，消除 R01 伪通过 P1/P2/P3）：
 *   1. scrypt --version 输出必须包含 "scrypt 1.3.2"（popen 捕获真实输出）
 *   2. 加解密往返：enc -> dec 后内容与原文一致（cmp 逐步断言，任一失败即退出）
 *   3. 错误口令解密必须失败（popen 捕获真实退出码，非 0 为期望结果）
 * 不使用任何"echo OK"掩码；最终退出码 0 = 全部断言真实通过。
 */

static char g_scrypt[4096] = "scrypt";	/* 默认走 PATH；argv[1] 可指定完整路径 */

/*
 * 执行一条 shell 命令，输出到管道；返回 (rc, 捕获到 stdout 的末行)。
 * rc: system/popen 的退出码（0 成功，非 0 失败）
 */
static int
run_capture(const char * cmd, char * out, size_t outsz)
{
	FILE * fp;
	char * p;

	out[0] = '\0';
	fp = popen(cmd, "r");
	if (fp == NULL)
		return -1;
	if (fgets(out, (int)outsz, fp) == NULL)
		out[0] = '\0';
	p = strrchr(out, '\n');
	if (p != NULL)
		*p = '\0';
	return pclose(fp);
}

/*
 * 创建唯一临时目录：优先 TMPDIR/TMP，其次当前目录（/tmp 在 OHOS 上只读，
 * 且固定路径在并行执行时会互相干扰——R02 P3 修复）。
 */
static char *
make_unique_dir(void)
{
	static char tmpl[4096];
	const char * base;
	char * d;

	base = getenv("TMPDIR");
	if (base == NULL || base[0] == '\0')
		base = getenv("TMP");
	if (base == NULL || base[0] == '\0')
		base = ".";
	snprintf(tmpl, sizeof(tmpl), "%s/scrypt-tp-XXXXXX", base);
	d = mkdtemp(tmpl);
	if (d == NULL) {
		/* 回退：当前目录下再试一次（cwd 通常可写） */
		snprintf(tmpl, sizeof(tmpl), "./scrypt-tp-XXXXXX");
		d = mkdtemp(tmpl);
	}
	return d;
}

int
main(int argc, char * argv[])
{
	char cmd[8192];
	char buf[512];
	char ver[256];
	char * dir;
	int rc, bad_rc;

	/* 可选 argv[1]：scrypt 二进制完整路径（test_package 由 conanfile 传入） */
	if (argc > 1)
		snprintf(g_scrypt, sizeof(g_scrypt), "%s", argv[1]);

	/* 1) 版本核验：捕获真实输出，必须包含 "scrypt 1.3.2" */
	snprintf(cmd, sizeof(cmd), "%s --version 2>&1", g_scrypt);
	rc = run_capture(cmd, ver, sizeof(ver));
	if (rc != 0) {
		fprintf(stderr, "FAIL: scrypt --version exit=%d\n", rc);
		return 1;
	}
	if (strstr(ver, "scrypt 1.3.2") == NULL) {
		fprintf(stderr, "FAIL: version output mismatch: '%s'\n", ver);
		return 1;
	}

	/* 唯一临时目录 */
	dir = make_unique_dir();
	if (dir == NULL) {
		fprintf(stderr, "FAIL: cannot create unique temp dir\n");
		return 1;
	}

	/* 2) 加解密往返：逐步断言，任一命令失败立即退出 1 */
	snprintf(cmd, sizeof(cmd),
	    "printf 'scrypt test_package roundtrip payload\\n' > %.4000s/plain.txt",
	    dir);
	if (system(cmd) != 0) { fprintf(stderr, "FAIL: write plain\n"); goto fail; }

	snprintf(cmd, sizeof(cmd),
	    "PASSPHRASE=tp-pass %.3800s enc --passphrase env:PASSPHRASE "
	    "%.4000s/plain.txt %.4000s/plain.enc", g_scrypt, dir, dir);
	if (system(cmd) != 0) { fprintf(stderr, "FAIL: scrypt enc\n"); goto fail; }

	snprintf(cmd, sizeof(cmd),
	    "PASSPHRASE=tp-pass %.3800s dec --passphrase env:PASSPHRASE "
	    "%.4000s/plain.enc %.4000s/dec.txt", g_scrypt, dir, dir);
	if (system(cmd) != 0) { fprintf(stderr, "FAIL: scrypt dec\n"); goto fail; }

	snprintf(cmd, sizeof(cmd), "cmp -s %.4000s/plain.txt %.4000s/dec.txt", dir, dir);
	if (system(cmd) != 0) {
		fprintf(stderr, "FAIL: decrypted content differs from original\n");
		goto fail;
	}

	/* 3) 错误口令解密必须失败：popen 捕获真实退出码，非 0 为期望结果 */
	snprintf(cmd, sizeof(cmd),
	    "PASSPHRASE=wrong %.3800s dec --passphrase env:PASSPHRASE "
	    "%.4000s/plain.enc %.4000s/bad.txt >/dev/null 2>&1", g_scrypt, dir, dir);
	bad_rc = run_capture(cmd, buf, sizeof(buf));
	if (bad_rc == 0) {
		fprintf(stderr, "FAIL: wrong passphrase decrypt unexpectedly succeeded\n");
		goto fail;
	}

	/* 清理临时目录（尽力而为，不因清理失败判负） */
	snprintf(cmd, sizeof(cmd), "rm -rf %.4000s", dir);
	(void)system(cmd);

	printf("test_package scrypt consumer test PASSED (version=%s)\n", ver);
	return 0;

fail:
	/* 保留临时目录便于诊断；不构成通过 */
	fprintf(stderr, "temp dir kept for diagnosis: %.4000s\n", dir);
	return 1;
}

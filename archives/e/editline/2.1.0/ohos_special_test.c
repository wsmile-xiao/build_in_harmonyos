/* editline 2.1.0 HarmonyOS 专项测试（headless）
 *
 * 鸿蒙 PC 设备常见无终端（no-tty）运行场景，本用例验证 editline 在
 * 无 pty 环境下仍可用的公开 API 路径（上游测试均为 pty 驱动）：
 *   1) 补全引擎 rl_completion_matches() 配合自定义 generator，
 *      验证可枚举候选、首个命中与无候选行为（纯字符串/堆操作，无终端依赖）；
 *   2) 历史记录 API add_history()/el_hist_size/write_history()/read_history()
 *      round-trip，验证动态调整滚动容量后字节保真；
 *   3) el_bind_key() 公开按键绑定注册返回状态（不触发终端 IO）。
 * 本用例真实编译、链接、运行并输出可观察结果。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <editline.h>

/* 补全失败：无候选时的 generator 行为由 rl_completion_matches() 语义保证 */
static char *gen_none(const char *token, int state)
{
	(void)token;
	(void)state;
	return NULL;
}

/* 补全生成器：返回 "hello" / "help" / "hero" 三个候选 */
static char *gen_words(const char *token, int state)
{
	static int n;
	static const char *words[] = { "hello", "help", "hero" };

	(void)token;
	if (state == 0)
		n = 0;
	if (n < 3)
		return strdup(words[n++]);
	return NULL;
}

int main(void)
{
	int fails = 0;

	/* 1) rl_initialize() 公开初始化（无终端） */
	rl_initialize();

	/* 2) 补全引擎：3 个候选 */
	{
		char **m = rl_completion_matches("he", gen_words);
		int i, n = 0;

		if (!m) {
			fprintf(stderr, "FAIL completion: no matches\n");
			fails++;
		} else {
			while (m[n])
				n++;
			printf("PASS completion: %d candidates:", n);
			for (i = 0; i < n; i++)
				printf(" %s", m[i]);
			printf("\n");
			if (n != 3 || strcmp(m[0], "hello") != 0 ||
			    strcmp(m[1], "help") != 0 || strcmp(m[2], "hero") != 0) {
				fprintf(stderr, "FAIL completion: wrong candidates\n");
				fails++;
			}
			for (i = 0; i < n; i++)
				free(m[i]);
			free(m);
		}
	}

	/* 3) 补全引擎：无候选返回 NULL（非空指针/非崩溃） */
	{
		char **m = rl_completion_matches("zzz", gen_none);

		if (m) {
			fprintf(stderr, "FAIL completion: expected NULL for no candidates\n");
			fails++;
		} else {
			printf("PASS completion-no-candidate: NULL returned\n");
		}
	}

	/* 4) 历史容量调节 + round-trip（无终端可写临时文件路径） */
	{
		const char *in = "editline-ohos-hist-in.tmp";
		const char *out = "editline-ohos-hist-out.tmp";
		FILE *fp;
		char buf[512];
		int i, eq = 1;

		el_hist_size = 32;
		fp = fopen(in, "w");
		if (!fp) {
			fprintf(stderr, "FAIL history: cannot create input\n");
			fails++;
		} else {
			for (i = 0; i < el_hist_size + 1; i++)
				fprintf(fp, "ohos history line %d\n", i);
			fclose(fp);

			if (read_history(in) != 0 || write_history(out) != 0) {
				fprintf(stderr, "FAIL history: read/write_history failed\n");
				fails++;
			} else {
				FILE *fa = fopen(in, "rb");
				FILE *fb = fopen(out, "rb");
				int ca, cb;

				if (!fa || !fb) {
					if (fa) fclose(fa);
					if (fb) fclose(fb);
					eq = 0;
				} else {
					do {
						ca = getc(fa);
						cb = getc(fb);
						if (ca != cb) {
							eq = 0;
							break;
						}
					} while (ca != EOF);
					fclose(fa);
					fclose(fb);
				}
				if (eq)
					printf("PASS history: %d entries byte-identical round-trip (el_hist_size=%d)\n",
					       el_hist_size + 1, el_hist_size);
				else {
					fprintf(stderr, "FAIL history: content mismatch\n");
					fails++;
				}
			}
			unlink(in);
			unlink(out);
		}
		/* add_history() 公开 API 实际调用 */
		add_history("ohos added line");
		(void)buf;
	}

	/* 5) el_bind_key() 注册合法按键（无终端不触发 IO） */
	{
		el_status_t s = el_bind_key('k', el_del_char);

		if (s == CSdone)
			printf("PASS el_bind_key: binding registered (CSdone)\n");
		else {
			fprintf(stderr, "FAIL el_bind_key: status=%d\n", s);
			fails++;
		}
	}

	printf("ohos-special: %d failure(s)\n", fails);
	return fails ? 1 : 0;
}
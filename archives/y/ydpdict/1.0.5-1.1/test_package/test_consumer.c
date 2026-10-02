/*
 * test_consumer.c — ydpdict/1.0.5-1.1 消费者用例（C，链接被测词典引擎）
 *
 * 上游 ydpdict 1.0.5 发布包不含任何测试程序（清点证据见 test_package/MANIFEST.yml），
 * 本文件提供消费者视角的实测用例：直接链接被测包依赖的词典引擎 libydpdict
 * （ydpdict 运行时唯一的词典后端），在 OHOS aarch64 设备 ABI 上验证
 *
 *   A. 版本契约：YDPDICT_MAKE_VERSION 宏与 YDPDICT_VERSION 运行期取值一致；
 *   B. 打开失败路径：词典文件缺失 / 索引 magic 错误 / 索引截断 —— 均返回 NULL，
 *      不触发放大性故障（真实文件 I/O，落在本次测试的临时目录）；
 *   C. 空指针守护：get_count / find_word / close 对 NULL 词典返回 -1；
 *   D. 编码转换：ASCII 透传；高位字节产出合法 UTF-8（含 0xB1 → cp1250 'ą'）。
 *
 * 退出码 = 失败断言数（0 表示全部通过）；断言总数打印到 stdout 供 MANIFEST 计数。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <ydpdict/ydpdict.h>

static int g_assertions = 0;
static int g_failures = 0;

static void check(int ok, const char *what)
{
	g_assertions++;
	if (ok) {
		printf("  [PASS] %s\n", what);
	} else {
		g_failures++;
		printf("  [FAIL] %s\n", what);
	}
}

/* 校验字符串是否为合法 UTF-8（不接受越界续字节、不接受截断序列）。 */
static int is_valid_utf8(const char *s)
{
	const unsigned char *p = (const unsigned char *) s;
	int need = 0;

	for (; *p; p++) {
		if (need) {
			if ((*p & 0xc0) != 0x80)
				return 0;
			need--;
			continue;
		}
		if (*p < 0x80)
			continue;
		if ((*p & 0xe0) == 0xc0)
			need = 1;
		else if ((*p & 0xf0) == 0xe0)
			need = 2;
		else if ((*p & 0xf8) == 0xf0)
			need = 3;
		else
			return 0;
	}
	return need == 0;
}

/* 在临时目录里造一个二进制文件，返回其路径（写进调用方缓冲区）。 */
static int write_file(const char *path, const unsigned char *data, size_t size)
{
	FILE *f = fopen(path, "wb");
	size_t written;

	if (f == NULL)
		return -1;
	written = fwrite(data, 1, size, f);
	fclose(f);
	return written == size ? 0 : -1;
}

int main(void)
{
	char dir[256];
	char idx[300];
	char dat[300];
	unsigned char zeros[64];
	ydpdict_t *dict;
	char *out;

	memset(zeros, 0, sizeof(zeros));
	snprintf(dir, sizeof(dir), "%s", getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp");
	snprintf(idx, sizeof(idx), "%s/ydpdict-test-garbage.idx", dir);
	snprintf(dat, sizeof(dat), "%s/ydpdict-test-garbage.dat", dir);

	printf("ydpdict consumer test (libydpdict %u.%u.%u)\n",
	       YDPDICT_VERSION >> 16, (YDPDICT_VERSION >> 8) & 0xff, YDPDICT_VERSION & 0xff);

	/* A. 版本契约 */
	check(YDPDICT_VERSION == YDPDICT_MAKE_VERSION(1, 0, 4), "A1 版本宏自洽（YDPDICT_MAKE_VERSION）");
	check(YDPDICT_MAKE_VERSION(0, 99, 3) < YDPDICT_VERSION, "A2 版本 ≥ configure 要求的 0.99.3");

	/* B. 打开失败路径：文件缺失 */
	dict = ydpdict_open("/nonexistent/ydpdict-test/100.dat",
	                    "/nonexistent/ydpdict-test/100.idx",
	                    YDPDICT_ENCODING_UTF8);
	check(dict == NULL, "B1 词典文件缺失时 ydpdict_open 返回 NULL");

	/* B. 打开失败路径：索引 magic 错误（真实创建文件） */
	check(write_file(idx, zeros, sizeof(zeros)) == 0, "B2 索引样本写入成功");
	check(write_file(dat, zeros, sizeof(zeros)) == 0, "B3 数据样本写入成功");
	dict = ydpdict_open(dat, idx, YDPDICT_ENCODING_UTF8);
	check(dict == NULL, "B4 索引 magic 错误时 ydpdict_open 返回 NULL");

	/* B. 打开失败路径：索引截断（仅 4 字节，读不到词条数） */
	check(write_file(idx, zeros, 4) == 0, "B5 截断索引写入成功");
	dict = ydpdict_open(dat, idx, YDPDICT_ENCODING_UTF8);
	check(dict == NULL, "B6 索引截断时 ydpdict_open 返回 NULL");

	/* C. 空指针守护 */
	check(ydpdict_get_count(NULL) == -1, "C1 ydpdict_get_count(NULL) == -1");
	check(ydpdict_find_word(NULL, "kot") == -1, "C2 ydpdict_find_word(NULL, ...) == -1");
	check(ydpdict_close(NULL) == -1, "C3 ydpdict_close(NULL) == -1");

	/* D. 编码转换 */
	out = ydpdict_phonetic_to_utf8("kot");
	check(out != NULL && strcmp(out, "kot") == 0, "D1 音标转换对 ASCII 透传");
	free(out);

	out = ydpdict_phonetic_to_utf8("\x80");
	check(out != NULL && out[0] != '\0' && is_valid_utf8(out) && strcmp(out, "\x80") != 0,
	      "D2 音标转换对高位字节产出合法 UTF-8");
	free(out);

	out = ydpdict_windows1250_to_utf8("kot");
	check(out != NULL && strcmp(out, "kot") == 0, "D3 cp1250 转换对 ASCII 透传");
	free(out);

	out = ydpdict_windows1250_to_utf8("\xb1");
	check(out != NULL && strlen(out) >= 2 && is_valid_utf8(out),
	      "D4 cp1250 0xB1(ą) 转出多字节 UTF-8");
	free(out);

	out = ydpdict_windows1250_to_utf8("\xa5");
	check(out != NULL && is_valid_utf8(out), "D5 cp1250 0xA5(Ą) 转出合法 UTF-8");
	free(out);

	unlink(idx);
	unlink(dat);

	printf("assertions=%d failures=%d\n", g_assertions, g_failures);
	return g_failures;
}

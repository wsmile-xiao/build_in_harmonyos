/*
 * libydpdict 消费者测试（Conan L1 test_package）
 *
 * 上游发布包不含任何测试（清点证据见 test_package/MANIFEST.yml），因此本测试
 * 同时承担两重校验：
 *   1. 产物可用性——头文件安装路径、库链接、符号可见性；
 *   2. 核心行为——windows-1250 / 音标 / 上标 → UTF-8 的真实转换结果，
 *      以及 NULL 句柄与缺失词典文件的边界行为。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ydpdict/ydpdict.h>

static int failed;

static void check(int cond, const char *msg)
{
	printf("  [%s] %s\n", cond ? "ok" : "FAIL", msg);
	if (!cond)
		failed++;
}

int main(void)
{
	char *p;

	/* 1. 版本宏来自被测头文件 */
	check(YDPDICT_VERSION > 0, "YDPDICT_VERSION defined by ydpdict.h");

	/* 2. windows-1250 → UTF-8：ASCII 直通 */
	p = ydpdict_windows1250_to_utf8("abc");
	check(p != NULL && strcmp(p, "abc") == 0,
	      "windows1250_to_utf8(\"abc\") == \"abc\"");
	free(p);

	/* 3. windows-1250 → UTF-8：高位字节走转换表（0xb3 = ł U+0142） */
	p = ydpdict_windows1250_to_utf8("\xb3");
	check(p != NULL && strcmp(p, "\xc5\x82") == 0,
	      "windows1250_to_utf8(0xb3) == U+0142 (ł)");
	free(p);

	/* 4. 音标 → UTF-8：0x8b 落在音标表 128..159 区间（= ɑ U+0251） */
	p = ydpdict_phonetic_to_utf8("\x8b");
	check(p != NULL && strcmp(p, "\xc9\x91") == 0,
	      "phonetic_to_utf8(0x8b) == U+0251 (ɑ)");
	free(p);

	/* 5. 上标数字 → UTF-8（入参为二进制码 1..9，非 ASCII '0'..'9'） */
	p = ydpdict_windows1250_super_to_utf8("\x02");
	check(p != NULL && strcmp(p, "\xc2\xb2") == 0,
	      "windows1250_super_to_utf8(0x02) == U+00B2 (²)");
	free(p);

	/* 6. 边界：NULL 句柄按文档返回错误值而不是崩溃 */
	check(ydpdict_get_count(NULL) == -1, "get_count(NULL) == -1");
	check(ydpdict_find_word(NULL, "foo") == -1, "find_word(NULL, ...) == -1");
	check(ydpdict_get_word(NULL, 0) == NULL, "get_word(NULL, 0) == NULL");

	/* 7. 边界：词典文件缺失时 open 返回 NULL */
	check(ydpdict_open("/nonexistent-ydpdict.dat", "/nonexistent-ydpdict.idx",
	                   YDPDICT_ENCODING_UTF8) == NULL,
	      "open(missing files) == NULL");

	if (failed) {
		printf("test libydpdict 1.0.4: %d FAILED\n", failed);
		return 1;
	}

	printf("test libydpdict 1.0.4: OK\n");
	return 0;
}

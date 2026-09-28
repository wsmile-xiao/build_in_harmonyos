/*
 * libydpdict 端到端消费者用例（rule12：完整消费者用例，非纯断言）
 *
 * 以消费者身份真实走通词典库的完整生命周期：
 *   1. 在 OHOS 文件系统上生成一对真实的 dict999.dat / dict999.idx
 *      （二进制格式与上游 misc/mkdict.py 完全一致：
 *        idx = 256 字节头 <LLHHLL236s>(magic 0x8d4e11d5, 0, count, 0, 0, 256) +
 *              逐条 <BBHL>(len=word+1, attr=2, idx_offset, dat_offset) + word + '\0'
 *        dat = 逐条 <L>(len) + 释义正文（windows-1250））
 *   2. ydpdict_open(真实文件对, UTF8)
 *   3. get_count / find_word / get_word（词目，UTF8 模式下已转码）/
 *      read_rtf（释义正文，dat 偏移与长度）完整查询流程
 *   4. ydpdict_close 释放并清理临时文件
 *
 * API 语义（依据上游 src/ydpdict.c:400 与 include/ydpdict.h:49-59 实测）：
 *   - ydpdict_get_word(dict, def)  返回**词目**（headword；UTF8 模式下 open 时已由
 *     windows-1250 转码），不是释义正文；
 *   - ydpdict_read_rtf(dict, def)  返回**释义正文**（RTF 原文，不做字符集转换，
 *     调用方负责 free），越界返回 NULL 并置 EINVAL；
 *   - ydpdict_find_word(dict, w)   前缀匹配 + 大小写不敏感，返回词目下标，未命中 -1。
 *
 * 注：本文件的前一版把 get_word() 当成"取释义正文"（期望值写成 dat 里的定义），
 * 且从未被 test() 真实执行过；现版本按上游真实语义断言，并在 test() 中真实运行。
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ydpdict/ydpdict.h>

#define NENTRIES 3

static int failed;

static void check(int cond, const char *msg)
{
	printf("  [%s] %s\n", cond ? "ok" : "FAIL", msg);
	if (!cond)
		failed++;
}

struct idx_header {
	uint32_t magic;
	uint32_t zero;
	uint16_t count;
	uint16_t pad;
	uint32_t first_index;
	uint32_t table_offset;
	char reserved[236];
};

static void write_u32le(FILE *f, uint32_t v)
{
	unsigned char b[4] = { v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff,
		(v >> 24) & 0xff };
	fwrite(b, 1, 4, f);
}

static void write_u16le(FILE *f, uint16_t v)
{
	unsigned char b[2] = { v & 0xff, (v >> 8) & 0xff };
	fwrite(b, 1, 2, f);
}

/*
 * 词目 / 释义：与上游 misc/mkdict.py 同样以 windows-1250 字节写入文件。
 * 0xb3 = ł，其在 UTF-8 中的编码为 0xc5 0x82（U+0142）。
 */
static const char *words[] = {
	"computer",
	"shield",
	"s\xb3owo",		/* windows-1250: s ł o w o */
};
static const char *defs[] = {
	"komputer",
	"tarcza rycerza\xb3",
	"definicja s\xb3owa",
};
/* 同一批词目在 UTF8 编码模式下的期望值（open 时由库转换） */
static const char *words_utf8[] = {
	"computer",
	"shield",
	"s\xc5\x82owo",		/* UTF-8: ł = U+0142 */
};

static int make_dict(const char *dat_path, const char *idx_path)
{
	struct idx_header hdr;
	uint32_t dat_offsets[NENTRIES];
	uint32_t idx_offsets[NENTRIES];
	uint32_t dat_off = 0, idx_off = 256;
	int i;
	FILE *dat = fopen(dat_path, "wb");
	FILE *idx = fopen(idx_path, "wb");

	if (!dat || !idx) {
		if (dat)
			fclose(dat);
		if (idx)
			fclose(idx);
		return -1;
	}

	/* 偏移预先算好：dat 条目 = 4 字节长度 + 正文；idx 条目 = 8 字节固定段 + word + '\0' */
	for (i = 0; i < NENTRIES; i++) {
		dat_offsets[i] = dat_off;
		dat_off += 4 + (uint32_t)strlen(defs[i]);
		idx_offsets[i] = idx_off;
		idx_off += 8 + (uint32_t)strlen(words[i]) + 1;
	}

	for (i = 0; i < NENTRIES; i++) {
		write_u32le(dat, (uint32_t)strlen(defs[i]));
		fwrite(defs[i], 1, strlen(defs[i]), dat);
	}

	memset(&hdr, 0, sizeof(hdr));
	hdr.magic = 0x8d4e11d5;	/* 上游 YDPDICT_IDX_MAGIC */
	hdr.zero = 0;
	hdr.count = NENTRIES;
	hdr.pad = 0;
	hdr.first_index = 0;
	hdr.table_offset = 256;
	fwrite(&hdr, sizeof(hdr), 1, idx);

	for (i = 0; i < NENTRIES; i++) {
		size_t wlen = strlen(words[i]);

		fwrite(&(uint8_t){ (uint8_t)(wlen + 1) }, 1, 1, idx);
		fwrite(&(uint8_t){ 2 }, 1, 1, idx);
		write_u16le(idx, (uint16_t)(idx_offsets[i] & 0xffff));
		write_u32le(idx, dat_offsets[i]);
		fwrite(words[i], 1, wlen, idx);
		fwrite("", 1, 1, idx);
	}

	fclose(dat);
	fclose(idx);
	return 0;
}

int main(void)
{
	const char *tmp = getenv("TMPDIR");
	char dat_path[256], idx_path[256];
	ydpdict_t *dict;
	int n, i, idx;
	const char *word;
	char *rtf;
	FILE *probe;

	/* 本机 /tmp 只读：优先 TMPDIR，其次当前工作目录（test_package 构建目录，必可写） */
	if (!tmp || !tmp[0])
		tmp = ".";
	snprintf(dat_path, sizeof(dat_path), "%s/ydpdict_e2e.dat", tmp);
	snprintf(idx_path, sizeof(idx_path), "%s/ydpdict_e2e.idx", tmp);

	printf("== ydpdict e2e: real dict files -> open -> query -> close ==\n");

	/* 1) 生成真实词典文件对 */
	check(make_dict(dat_path, idx_path) == 0, "生成 dict999.dat/idx 文件对");
	probe = fopen(idx_path, "rb");
	check(probe != NULL, "idx 文件可读（已落盘）");
	if (probe)
		fclose(probe);

	/* 2) 打开真实词典（UTF8 输出编码） */
	dict = ydpdict_open(dat_path, idx_path, YDPDICT_ENCODING_UTF8);
	check(dict != NULL, "ydpdict_open(真实文件对, UTF8) 成功");
	if (!dict) {
		remove(dat_path);
		remove(idx_path);
		printf("e2e: %d FAILED\n", failed);
		return 1;
	}

	/* 3) 词条数 */
	n = ydpdict_get_count(dict);
	check(n == NENTRIES, "get_count() == 3（与生成的词条数一致）");

	/* 4) 词目查询：find_word 返回下标，get_word 取回词目（非释义正文） */
	idx = ydpdict_find_word(dict, "computer");
	check(idx == 0, "find_word(\"computer\") -> 下标 0");
	word = idx >= 0 ? ydpdict_get_word(dict, idx) : NULL;
	check(word != NULL && strcmp(word, words_utf8[0]) == 0,
		"get_word() 取回词目 \"computer\"（API 语义：headword）");

	/* 5) 前缀匹配 + 大小写不敏感（上游 strncasecmp 语义） */
	check(ydpdict_find_word(dict, "COMPU") == 0,
		"find_word(\"COMPU\") 前缀匹配且大小写不敏感");

	/* 6) 高位字节词目：windows-1250 0xb3 在 UTF8 模式下转为 ł(U+0142) */
	idx = ydpdict_find_word(dict, words_utf8[2]);
	check(idx == 2, "find_word(\"słowo\") 命中下标 2（词目已转 UTF-8）");
	word = idx >= 0 ? ydpdict_get_word(dict, idx) : NULL;
	check(word != NULL && strcmp(word, "s\xc5\x82owo") == 0,
		"get_word() 词目高位字节 0xb3 -> UTF-8 ł（0xc5 0x82）");

	/* 7) 释义正文：read_rtf 走 dat 偏移 + 长度，返回 RTF 原文（不做字符集转换） */
	rtf = ydpdict_read_rtf(dict, 0);
	check(rtf != NULL && strcmp(rtf, defs[0]) == 0,
		"read_rtf(0) 取回释义正文且 dat 偏移正确");
	if (rtf)
		free(rtf);

	rtf = ydpdict_read_rtf(dict, 1);
	check(rtf != NULL && strcmp(rtf, defs[1]) == 0,
		"read_rtf(1) 释义含原始 windows-1250 高位字节 0xb3（read_rtf 不转码）");
	if (rtf)
		free(rtf);

	check(ydpdict_read_rtf(dict, NENTRIES) == NULL,
		"read_rtf(越界) 返回 NULL");

	/* 8) 未收录词 */
	check(ydpdict_find_word(dict, "no-such-word") == -1,
		"find_word(未收录词) 返回 -1");

	/* 9) 关闭并清理 */
	check(ydpdict_close(dict) == 0, "ydpdict_close() 正常释放");
	remove(dat_path);
	remove(idx_path);
	(void)i;

	if (failed) {
		printf("e2e: %d FAILED\n", failed);
		return 1;
	}
	printf("e2e: OK\n");
	return 0;
}

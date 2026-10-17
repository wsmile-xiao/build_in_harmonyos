/* libslz 1.2.1 test_package — 消费者 API 断言（每条打印一行 ASSERT_OK/ASSERT_FAIL）
 * 用法: test_slz <输出目录>
 * 输出: <dir>/rt-input.bin, slz-gzip.out, slz-zlib.out, slz-deflate.out
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "slz.h"

static int fails = 0;

static void check(int cond, const char *name)
{
	if (cond) {
		printf("ASSERT_OK %s\n", name);
	} else {
		printf("ASSERT_FAIL %s\n", name);
		fails++;
	}
}

static uint32_t le32(const unsigned char *p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
	       ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t be32(const unsigned char *p)
{
	return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
	       ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static long encode_buf(int fmt, int level, const unsigned char *in, long len,
		       unsigned char *out, long outcap)
{
	struct slz_stream strm;
	long done = 0, n, total = 0, chunk;

	if (slz_init(&strm, level, fmt) != 0)
		return -1;
	while (done < len) {
		chunk = len - done;
		if (chunk > 4096)
			chunk = 4096;
		if (total + chunk + 16 > outcap)
			return -3;
		n = slz_encode(&strm, out + total, in + done, chunk, 1);
		if (n < 0)
			return -2;
		total += n;
		done += chunk;
	}
	if (total + 64 > outcap)
		return -3;
	n = slz_finish(&strm, out + total);
	if (n < 0)
		return -4;
	return total + n;
}

static int write_file(const char *dir, const char *name,
		      const unsigned char *buf, long len)
{
	char path[1024];
	FILE *f;

	snprintf(path, sizeof(path), "%s/%s", dir, name);
	f = fopen(path, "wb");
	if (!f)
		return -1;
	if (len > 0 && fwrite(buf, 1, (size_t)len, f) != (size_t)len) {
		fclose(f);
		return -1;
	}
	return fclose(f) == 0 ? 0 : -1;
}

int main(int argc, char **argv)
{
	const char *dir = argc > 1 ? argv[1] : ".";
	static unsigned char input[65536];
	static unsigned char out[262144];
	static unsigned char out0[262144];
	long len, glen, zlen, dlen, l0;
	size_t i;
	const char *pat = "the quick brown fox jumps over the lazy dog 0123456789\n";
	size_t patlen = strlen(pat);
	struct slz_stream strm;

	for (i = 0; i < sizeof(input); i++)
		input[i] = (unsigned char)pat[i % patlen];
	len = (long)sizeof(input);

	/* 1-3: 三种格式初始化 */
	check(slz_init(&strm, 1, SLZ_FMT_GZIP) == 0, "init_gzip_ok");
	check(slz_init(&strm, 1, SLZ_FMT_ZLIB) == 0, "init_zlib_ok");
	check(slz_init(&strm, 1, SLZ_FMT_DEFLATE) == 0, "init_deflate_ok");

	/* 4-6: gzip 封套（magic / ISIZE / CRC32 trailer） */
	glen = encode_buf(SLZ_FMT_GZIP, 1, input, len, out, (long)sizeof(out));
	check(glen > 20, "gzip_output_nonempty");
	if (glen > 20) {
		check(out[0] == 0x1f && out[1] == 0x8b && out[2] == 8, "gzip_header_magic");
		check(le32(out + glen - 4) == (uint32_t)len, "gzip_isize_trailer");
		check(le32(out + glen - 8) == slz_crc32_by1(0, input, (int)len),
		      "gzip_crc32_trailer");
	} else {
		check(0, "gzip_header_magic");
		check(0, "gzip_isize_trailer");
		check(0, "gzip_crc32_trailer");
	}
	check(write_file(dir, "slz-gzip.out", out, glen) == 0, "write_gzip_out");

	/* 7-9: zlib 封套（CMF/FLG / adler32 trailer / 非空） */
	zlen = encode_buf(SLZ_FMT_ZLIB, 1, input, len, out, (long)sizeof(out));
	check(zlen > 20, "zlib_output_nonempty");
	if (zlen > 20) {
		check((out[0] & 0x0f) == 8 &&
		      (((unsigned)out[0] << 8 | out[1]) % 31) == 0, "zlib_header_cmf_flg");
		/* adler32 初值必须是 1（zlib 约定）；传 0 会少 1 且 b 项错位 */
		check(be32(out + zlen - 4) == slz_adler32_by1(1, input, (int)len),
		      "zlib_adler32_trailer");
	} else {
		check(0, "zlib_header_cmf_flg");
		check(0, "zlib_adler32_trailer");
	}
	check(write_file(dir, "slz-zlib.out", out, zlen) == 0, "write_zlib_out");

	/* 10-11: raw deflate 非空 + 落盘 */
	dlen = encode_buf(SLZ_FMT_DEFLATE, 1, input, len, out, (long)sizeof(out));
	check(dlen > 0, "deflate_output_nonempty");
	check(write_file(dir, "slz-deflate.out", out, dlen) == 0, "write_deflate_out");

	/* 12-13: CRC32 标准测试向量 + by1/by4 一致性 */
	check(slz_crc32_by1(0, (const unsigned char *)"123456789", 9) == 0xCBF43926U,
	      "crc32_vector_123456789");
	check(slz_crc32_by1(0, input, (int)len) ==
	      slz_crc32_by4(0, input, (int)len), "crc32_by1_eq_by4");

	/* 14: Adler32 标准测试向量 */
	check(slz_adler32_by1(1, (const unsigned char *)"123456789", 9) == 0x091E01DEU,
	      "adler32_vector_123456789");

	/* 15-17: level 0（无压缩路径）三种格式仍可编码 */
	l0 = encode_buf(SLZ_FMT_GZIP, 0, input, len, out0, (long)sizeof(out0));
	check(l0 > 0, "level0_gzip_encodable");
	l0 = encode_buf(SLZ_FMT_ZLIB, 0, input, len, out0, (long)sizeof(out0));
	check(l0 > 0, "level0_zlib_encodable");
	l0 = encode_buf(SLZ_FMT_DEFLATE, 0, input, len, out0, (long)sizeof(out0));
	check(l0 > 0, "level0_deflate_encodable");

	/* 18: 供 round-trip 使用的原始输入 */
	check(write_file(dir, "rt-input.bin", input, len) == 0, "write_rt_input");

	printf("ASSERT_SUMMARY fails=%d\n", fails);
	return fails == 0 ? 0 : 1;
}

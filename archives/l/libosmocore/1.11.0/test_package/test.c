/*
 * test_package/test.c — libosmocore 消费者冒烟测试
 *
 * 跨 libosmocore / libosmogsm / libosmocodec 调用真实 API 并断言其语义
 * （R34：测试必须实质依赖被测包，此处没有空壳断言）。
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>

#include <osmocom/core/defs.h>          /* ubit_t */
#include <osmocom/core/utils.h>         /* osmo_hexdump / osmo_str_tolower / osmo_str_toupper / osmo_bcd2str */
#include <osmocom/core/talloc.h>        /* osmo_ctx_init / osmo_ctx（库导出的 TLS 变量） */
#include <osmocom/core/sockaddr_str.h>  /* osmo_sockaddr_str_from_str */
#include <osmocom/gsm/gsm23003.h>       /* osmo_mcc_from_str / osmo_mnc_from_str（libosmogsm） */
#include <osmocom/codec/codec.h>        /* osmo_amr_s_to_d / osmo_amr_d_to_s（libosmocodec） */

/* libosmocore: 十六进制 dump + 大小写转换 */
static void test_utils(void)
{
	const unsigned char buf[] = { 0x00, 0x0a, 0xff };
	char *hex = osmo_hexdump(buf, (int)sizeof(buf));

	/* 上游语义：逐字节 "%02x" 后跟一个分隔空格，故末尾保留空格 */
	assert(strcmp(hex, "00 0a ff ") == 0);
	printf("[libosmocore] osmo_hexdump(00 0a ff) = \"%s\"\n", hex);

	assert(strcmp(osmo_str_tolower("AbC-123"), "abc-123") == 0);
	assert(strcmp(osmo_str_toupper("AbC-123"), "ABC-123") == 0);
	printf("[libosmocore] osmo_str_tolower / osmo_str_toupper OK\n");
}

/* libosmocore: BCD 与数字串互转（GSM 常用） */
static void test_bcd(void)
{
	/* 低半字节在前：0x21 0x43 0x65 → "123456" */
	const uint8_t bcd[3] = { 0x21, 0x43, 0x65 };
	char digits[16] = { 0 };
	int rc = osmo_bcd2str(digits, sizeof(digits), bcd, 0, 6, false);

	assert(rc == 6);
	assert(strcmp(digits, "123456") == 0);
	printf("[libosmocore] osmo_bcd2str(0x21 0x43 0x65) = \"%s\"\n", digits);
}

/* libosmocore: 地址字符串与 sockaddr 结构互转 */
static void test_sockaddr_str(void)
{
	struct osmo_sockaddr_str sa;
	int rc = osmo_sockaddr_str_from_str(&sa, "127.0.0.1", 8080);

	assert(rc == 0);
	assert(sa.af == AF_INET);
	assert(sa.port == 8080);
	assert(strcmp(sa.ip, "127.0.0.1") == 0);
	printf("[libosmocore] osmo_sockaddr_str_from_str = %s:%u (af=%d)\n", sa.ip, sa.port, sa.af);

	/* IPv6 走同一 API */
	rc = osmo_sockaddr_str_from_str(&sa, "::1", 5000);
	assert(rc == 0);
	assert(sa.af == AF_INET6);
	assert(sa.port == 5000);
	printf("[libosmocore] osmo_sockaddr_str_from_str = %s:%u (af=%d)\n", sa.ip, sa.port, sa.af);
}

/* libosmocore: TLS 上下文初始化（osmo_ctx 为库导出的 __thread 变量） */
static void test_context(void)
{
	assert(osmo_ctx_init("test_package") == 0);
	assert(osmo_ctx != NULL);
	printf("[libosmocore] osmo_ctx_init OK, osmo_ctx = %p\n", (void *)osmo_ctx);
}

/* libosmogsm: MCC/MNC 字符串解析 */
static void test_plmn(void)
{
	uint16_t mcc = 0;
	uint16_t mnc = 0;
	bool mnc_3_digits = true;

	assert(osmo_mcc_from_str("262", &mcc) == 0);
	assert(mcc == 262);
	assert(osmo_mnc_from_str("01", &mnc, &mnc_3_digits) == 0);
	assert(mnc == 1);
	assert(mnc_3_digits == false);
	printf("[libosmogsm] PLMN parse OK (mcc=%u, mnc=%u, 3digits=%d)\n",
	       mcc, mnc, (int)mnc_3_digits);
}

/* libosmocodec: AMR 帧 s <-> d 位序重排（往返一致） */
static void test_amr_reorder(void)
{
	ubit_t src[244];
	ubit_t d[244];
	ubit_t back[244];
	int i;

	for (i = 0; i < 244; i++)
		src[i] = (i % 3 == 0) ? 1 : 0;

	assert(osmo_amr_s_to_d(d, src, 244, AMR_12_2) >= 0);
	assert(osmo_amr_d_to_s(back, d, 244, AMR_12_2) >= 0);
	assert(memcmp(back, src, sizeof(src)) == 0);
	printf("[libosmocodec] AMR 12.2 kbit/s 244-bit s<->d round-trip OK\n");
}

int main(void)
{
	test_utils();
	test_bcd();
	test_sockaddr_str();
	test_context();
	test_plmn();
	test_amr_reorder();

	printf("test libosmocore 1.11.0: OK\n");
	return 0;
}

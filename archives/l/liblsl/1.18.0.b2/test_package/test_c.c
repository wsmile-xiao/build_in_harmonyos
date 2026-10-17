/* test_package 消费者测试 —— liblsl C API（R34：必须实质调用被测包的 API）。
 *
 * 覆盖三类真实行为：
 *   1) 库标识：ABI 版本号 / 库信息字符串 / 协议版本 / 本地时钟；
 *   2) 元数据：stream_info 的创建、字段读取、XML 序列化与反序列化往返；
 *   3) 数据通路：本机回环上 outlet→inlet 的真实样本推送/拉取（TCP + LSL 协议）。
 *
 * 断言计数由程序自己打印：`ASSERTIONS: n`，供报告复算。
 */
#include <lsl_c.h>

#include <stdio.h>
#include <string.h>

static int g_checks;
static int g_failed;

static void check(int cond, const char *msg) {
	g_checks++;
	if (cond) {
		printf("ok   - %s\n", msg);
	} else {
		g_failed++;
		printf("FAIL - %s\n", msg);
	}
}

int main(void) {
	const char *source_id = "liblsl-test-uid-0001";

	/* ── 1. 库标识 ── */
	check(lsl_library_version() == 118, "lsl_library_version() == 118 (1.18)");
	const char *info = lsl_library_info();
	check(info != NULL && strstr(info, "1.18.0.b2") != NULL,
	      "lsl_library_info() 含 1.18.0.b2");
	check(lsl_protocol_version() == 110, "lsl_protocol_version() == 110");
	check(lsl_local_clock() > 0.0, "lsl_local_clock() > 0");

	/* ── 2. stream_info 元数据与 XML 往返 ── */
	lsl_streaminfo info_h = lsl_create_streaminfo(
	    "liblsl-consumer", "EEG", 4, LSL_IRREGULAR_RATE, cft_float32, source_id);
	check(info_h != NULL, "lsl_create_streaminfo()");
	if (!info_h) {
		printf("ASSERTIONS: %d FAILED: %d\n", g_checks, g_failed);
		return 1;
	}
	check(lsl_get_channel_count(info_h) == 4, "lsl_get_channel_count() == 4");
	check(lsl_get_channel_format(info_h) == cft_float32, "lsl_get_channel_format() == cft_float32");
	check(lsl_get_nominal_srate(info_h) == 0.0, "lsl_get_nominal_srate() == 0 (irregular)");
	check(strcmp(lsl_get_name(info_h), "liblsl-consumer") == 0, "lsl_get_name()");
	check(strcmp(lsl_get_type(info_h), "EEG") == 0, "lsl_get_type()");
	check(strcmp(lsl_get_source_id(info_h), source_id) == 0, "lsl_get_source_id()");
	check(lsl_get_channel_bytes(info_h) == 4, "lsl_get_channel_bytes() == 4");
	check(lsl_get_sample_bytes(info_h) == 16, "lsl_get_sample_bytes() == 16");

	/* 关键：fresh streaminfo 的 uid 是**空的**（uid 由 liblsl 在 outlet 建立时或
	 * 显式 lsl_reset_uid() 时分配），而空 uid 的 XML 反序列化出来是**无效**
	 * streaminfo —— 之后所有字段读取返回 0 或报
	 * "The UID of the given stream info is empty."。先分配 uid 再做往返。 */
	const char *uid = lsl_reset_uid(info_h);
	check(uid != NULL && uid[0] != '\0', "lsl_reset_uid() 生成非空 uid");

	char *xml = lsl_get_xml(info_h);
	check(xml != NULL && strstr(xml, "liblsl-consumer") != NULL, "lsl_get_xml() 含流名");
	lsl_streaminfo from_xml = xml ? lsl_streaminfo_from_xml(xml) : NULL;
	check(from_xml != NULL, "lsl_streaminfo_from_xml()");
	if (from_xml) {
		check(strcmp(lsl_get_uid(from_xml), uid) == 0,
		      "XML 往返后 uid 一致");
		check(lsl_get_channel_count(from_xml) == 4, "XML 往返后 channel_count 一致");
	}

	/* ── 3. 真实数据通路：outlet → inlet（本机回环）── */
	lsl_outlet outlet = lsl_create_outlet(info_h, 0, 360);
	check(outlet != NULL, "lsl_create_outlet()");

	int32_t ec = -1;
	float sent[4] = {1.5f, 2.5f, 3.5f, 4.5f};
	if (outlet) {
		/* 直接用同一个 streaminfo 建 inlet（含 outlet 已填好的地址），
		 * 跳过发现/解析步骤但仍然走完整的 TCP + LSL 协议数据通路。 */
		lsl_inlet inlet = lsl_create_inlet(info_h, 360, 0, 1);
		check(inlet != NULL, "lsl_create_inlet()");
		if (inlet) {
			lsl_open_stream(inlet, 5.0, &ec);
			check(ec == 0, "lsl_open_stream() ec == 0");
			check(lsl_wait_for_consumers(outlet, 5.0) != 0,
			      "outlet 观测到消费者（lsl_wait_for_consumers）");
			/* 消费者已连接：推两个样本（内容相同），再拉 */
			lsl_push_sample_f(outlet, sent);
			lsl_push_sample_f(outlet, sent);
			float got[4] = {0.0f, 0.0f, 0.0f, 0.0f};
			double ts = lsl_pull_sample_f(inlet, got, 4, 5.0, &ec);
			check(ec == 0 && ts > 0.0, "lsl_pull_sample_f() 收到样本");
			check(got[0] == 1.5f && got[1] == 2.5f && got[2] == 3.5f && got[3] == 4.5f,
			      "拉取到的样本值与推送一致");
			check(lsl_samples_available(inlet) >= 0, "lsl_samples_available() 可调用");
			lsl_close_stream(inlet);
			lsl_destroy_inlet(inlet);
		}
		lsl_destroy_outlet(outlet);
	}

	lsl_destroy_streaminfo(info_h);
	if (from_xml) lsl_destroy_streaminfo(from_xml);

	printf("ASSERTIONS: %d FAILED: %d\n", g_checks, g_failed);
	if (g_failed) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	return 0;
}

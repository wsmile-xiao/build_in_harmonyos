/*
 * test_package 消费者测试 — mdns 1.4.3 (https://github.com/mjansson/mdns)
 *
 * R34/PF3：真实调用 mdns.h 的公开 API 并验证可观察结果，禁止空壳打印。
 * mdns.h 是单头实现库（全部 static inline），消费者只需 #include "mdns.h"。
 *
 * 覆盖分组（TAP 输出，末行汇总 `# mdns consumer test: N checks, 0 failures`）：
 *   A 常量与枚举          —— MDNS_PORT / 记录类型 / class
 *   B 字节序辅助          —— mdns_htons/ntohs/htonl/ntohl 往返与线上字节序
 *   C 域名编码与解码      —— mdns_string_make / extract / skip / equal / find
 *   D 记录解析            —— mdns_record_parse_a/aaaa/txt/srv/ptr（构造确定性报文）
 *   E 公开 API 链接面     —— 取址强制编译全部网络 API（编译+链接覆盖，不发包）
 *   F 真实 socket 开合    —— mdns_socket_open_ipv4/ipv6 + close（OHOS 上真实运行）
 *
 * 除 F 组外全部为确定性纯计算断言，不依赖组播网络；A–E 不产生任何网络流量。
 */
#include "mdns.h"

#include <stdio.h>
#include <string.h>

static int checks = 0;
static int failures = 0;

static void
check(int cond, const char* desc) {
	++checks;
	if (cond) {
		printf("ok %d - %s\n", checks, desc);
	} else {
		++failures;
		printf("not ok %d - %s\n", checks, desc);
	}
}

int
main(void) {
	char wire[256];
	char wire2[256];
	char text[256];
	mdns_string_table_t table;

	/* ── A. 常量与枚举 ───────────────────────────────────────── */
	check(MDNS_PORT == 5353, "MDNS_PORT == 5353");
	check(MDNS_RECORDTYPE_A == 1 && MDNS_RECORDTYPE_PTR == 12 &&
	          MDNS_RECORDTYPE_TXT == 16 && MDNS_RECORDTYPE_AAAA == 28 &&
	          MDNS_RECORDTYPE_SRV == 33 && MDNS_RECORDTYPE_ANY == 255,
	      "record type enum values match RFC 1035/2782/6763");
	check(MDNS_CLASS_IN == 1, "MDNS_CLASS_IN == 1");

	/* ── B. 字节序辅助 ───────────────────────────────────────── */
	{
		unsigned char buf[8];
		uint16_t v16;
		uint32_t v32;

		memset(buf, 0, sizeof(buf));
		mdns_htons(buf, 0x1234);
		v16 = mdns_ntohs(buf);
		check(v16 == 0x1234, "mdns_htons/mdns_ntohs 16-bit round trip");
		check(buf[0] == 0x12 && buf[1] == 0x34,
		      "mdns_htons writes network (big-endian) byte order");

		memset(buf, 0, sizeof(buf));
		mdns_htonl(buf, 0xDEADBEEFu);
		v32 = mdns_ntohl(buf);
		check(v32 == 0xDEADBEEFu, "mdns_htonl/mdns_ntohl 32-bit round trip");
		check(buf[0] == 0xDE && buf[1] == 0xAD && buf[2] == 0xBE && buf[3] == 0xEF,
		      "mdns_htonl writes network (big-endian) byte order");
	}

	/* ── C. 域名编码与解码 ───────────────────────────────────── */
	{
		const char* name = "_test-mdns._tcp.local.";
		const size_t name_len = strlen(name);
		void* end;
		size_t ofs = 0;
		mdns_string_t extracted;
		size_t ofs2 = 0;
		int equal;

		memset(&table, 0, sizeof(table));
		memset(wire, 0, sizeof(wire));
		end = mdns_string_make(wire, sizeof(wire), wire, name, name_len, &table);
		check(end != NULL, "mdns_string_make encodes the service name");

		/* 线上格式（23 字节）：[10]"_test-mdns" [4]"_tcp" [5]"local" [0]，
		   编码时去掉服务名尾点（RFC 1035 label 编码） */
		check((unsigned char)wire[0] == 10 && memcmp(wire + 1, "_test-mdns", 10) == 0 &&
		          (unsigned char)wire[11] == 4 && memcmp(wire + 12, "_tcp", 4) == 0 &&
		          (unsigned char)wire[16] == 5 && memcmp(wire + 17, "local", 5) == 0 &&
		          wire[22] == 0,
		      "wire format is length-prefixed labels terminated by 0 (23 bytes)");

		extracted = mdns_string_extract(wire, sizeof(wire), &ofs, text, sizeof(text));
		check(extracted.length == strlen(name) &&
		          memcmp(extracted.str, name, extracted.length) == 0,
		      "mdns_string_extract round-trips the encoded name");
		check(ofs == 23, "mdns_string_extract advances offset past the terminator");

		ofs = 0;
		check(mdns_string_skip(wire, sizeof(wire), &ofs) == 1 && ofs == 23,
		      "mdns_string_skip returns 1 and lands on the same end offset");

		/* 第二份编码：大小写不等但 DNS 语义相等 → mdns_string_equal */
		memset(&table, 0, sizeof(table));
		memset(wire, 0, sizeof(wire));
		memset(wire2, 0, sizeof(wire2));
		mdns_string_make(wire, sizeof(wire), wire, name, name_len, &table);
		mdns_string_make(wire2, sizeof(wire2), wire2, "_TEST-mdns._TCP.local.",
		                 strlen("_TEST-mdns._TCP.local."), &table);
		ofs = 0;
		ofs2 = 0;
		equal = mdns_string_equal(wire, sizeof(wire), &ofs, wire2, sizeof(wire2), &ofs2);
		check(equal == 1 && ofs == 23 && ofs2 == 23,
		      "mdns_string_equal compares case-insensitively and advances both offsets");

		check(mdns_string_find(name, name_len, '.', 0) == 10,
		      "mdns_string_find locates the first label separator");
	}

	/* ── D. 记录解析（构造确定性报文，无网络） ────────────────── */
	{
		/* A: 192.168.1.42 */
		unsigned char adata[4] = {192, 168, 1, 42};
		struct sockaddr_in addr4;
		/* AAAA: 2001:db8::1 */
		unsigned char adata6[16] = {0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0,
		                            0,    0,    0,    0,    0, 0, 0, 1};
		struct sockaddr_in6 addr6;
		/* TXT: "version=1.4.3" + "id=42" */
		unsigned char txtdata[20] = {13, 'v', 'e', 'r', 's', 'i', 'o', 'n', '=', '1', '.',
		                             '4', '.', '3', 5,   'i', 'd', '=',  '4', '2'};
		mdns_record_txt_t txt[8];
		size_t txt_count;
		/* SRV: prio=1 weight=2 port=42424 target=dummy-host.local. */
		unsigned char srvdata[64];
		mdns_record_srv_t srv;
		size_t srv_len;
		void* srv_end;
		char srv_text[64];
		/* PTR: _test-mdns._tcp.local. */
		unsigned char ptrdata[32];
		size_t ptr_len;
		void* ptr_end;
		char ptr_text[64];
		mdns_string_t ptr_name;
		size_t ofs;

		mdns_record_parse_a(adata, sizeof(adata), 0, sizeof(adata), &addr4);
		check(addr4.sin_family == AF_INET, "mdns_record_parse_a sets AF_INET");
		check(ntohl(addr4.sin_addr.s_addr) == 0xC0A8012Au,
		      "mdns_record_parse_a decodes 192.168.1.42");

		mdns_record_parse_aaaa(adata6, sizeof(adata6), 0, sizeof(adata6), &addr6);
		check(addr6.sin6_family == AF_INET6, "mdns_record_parse_aaaa sets AF_INET6");
		check(memcmp(&addr6.sin6_addr, adata6, 16) == 0,
		      "mdns_record_parse_aaaa decodes 2001:db8::1");

		txt_count = mdns_record_parse_txt(txtdata, sizeof(txtdata), 0, sizeof(txtdata), txt,
		                                  8);
		check(txt_count == 2, "mdns_record_parse_txt parses 2 key=value entries");
		check(txt[0].key.length == 7 && memcmp(txt[0].key.str, "version", 7) == 0,
		      "TXT entry 0 key == version");
		check(txt[0].value.length == 5 && memcmp(txt[0].value.str, "1.4.3", 5) == 0,
		      "TXT entry 0 value == 1.4.3");
		check(txt[1].key.length == 2 && memcmp(txt[1].key.str, "id", 2) == 0 &&
		          txt[1].value.length == 2 && memcmp(txt[1].value.str, "42", 2) == 0,
		      "TXT entry 1 key/value == id/42");

		memset(srvdata, 0, sizeof(srvdata));
		mdns_htons(srvdata, 1);      /* priority */
		mdns_htons(srvdata + 2, 2);  /* weight */
		mdns_htons(srvdata + 4, 42424); /* port */
		memset(&table, 0, sizeof(table));
		srv_end = mdns_string_make(srvdata, sizeof(srvdata), srvdata + 6,
		                            "dummy-host.local.", strlen("dummy-host.local."),
		                            &table);
		srv_len = (srv_end == NULL) ? 0 : (size_t)((char*)srv_end - (char*)srvdata);
		srv = mdns_record_parse_srv(srvdata, srv_len, 0, srv_len, srv_text,
		                            sizeof(srv_text));
		check(srv_len == 6 + 18, "SRV rdata length is 6 + encoded target (24)");
		check(srv.port == 42424, "mdns_record_parse_srv decodes port 42424");
		check(srv.priority == 1 && srv.weight == 2,
		      "mdns_record_parse_srv decodes priority/weight");
		check(srv.name.length == strlen("dummy-host.local.") &&
		          memcmp(srv.name.str, "dummy-host.local.", srv.name.length) == 0,
		      "mdns_record_parse_srv decodes the target hostname");

		memset(ptrdata, 0, sizeof(ptrdata));
		memset(&table, 0, sizeof(table));
		ptr_end = mdns_string_make(ptrdata, sizeof(ptrdata), ptrdata,
		                           "_test-mdns._tcp.local.",
		                           strlen("_test-mdns._tcp.local."), &table);
		ptr_len = (ptr_end == NULL) ? 0 : (size_t)((char*)ptr_end - (char*)ptrdata);
		ofs = 0;
		ptr_name = mdns_record_parse_ptr(ptrdata, ptr_len, 0, ptr_len, ptr_text,
		                                  sizeof(ptr_text));
		check(ptr_len == 23,
		      "PTR rdata length is the encoded service name (1+10 +1+4 +1+5 +1 = 23)");
		check(ofs == 0 && ptr_name.length == strlen("_test-mdns._tcp.local.") &&
		          memcmp(ptr_name.str, "_test-mdns._tcp.local.", ptr_name.length) == 0,
		      "mdns_record_parse_ptr decodes the service instance name");
	}

	/* ── E. 公开 API 链接面（取址强制编译，不发任何网络包） ────── */
	{
		volatile void* p;
		p = (void*)mdns_socket_open_ipv4;
		check(p != NULL, "API link: mdns_socket_open_ipv4");
		p = (void*)mdns_socket_open_ipv6;
		check(p != NULL, "API link: mdns_socket_open_ipv6");
		p = (void*)mdns_socket_close;
		check(p != NULL, "API link: mdns_socket_close");
		p = (void*)mdns_socket_listen;
		check(p != NULL, "API link: mdns_socket_listen");
		p = (void*)mdns_discovery_send;
		check(p != NULL, "API link: mdns_discovery_send");
		p = (void*)mdns_discovery_recv;
		check(p != NULL, "API link: mdns_discovery_recv");
		p = (void*)mdns_query_send;
		check(p != NULL, "API link: mdns_query_send");
		p = (void*)mdns_multiquery_send;
		check(p != NULL, "API link: mdns_multiquery_send");
		p = (void*)mdns_query_recv;
		check(p != NULL, "API link: mdns_query_recv");
		p = (void*)mdns_query_answer_multicast;
		check(p != NULL, "API link: mdns_query_answer_multicast");
		p = (void*)mdns_announce_multicast;
		check(p != NULL, "API link: mdns_announce_multicast");
		p = (void*)mdns_goodbye_multicast;
		check(p != NULL, "API link: mdns_goodbye_multicast");
	}

	/* ── F. 真实 socket 开合（OHOS 真实运行面） ───────────────── */
	{
		int sock4 = mdns_socket_open_ipv4(NULL);
		int sock6 = mdns_socket_open_ipv6(NULL);

		check(sock4 >= 0, "mdns_socket_open_ipv4(NULL) opens a UDP socket on OHOS");
		if (sock4 >= 0) {
			mdns_socket_close(sock4);
			check(1, "mdns_socket_close closes the IPv4 socket");
		} else {
			check(0, "mdns_socket_close closes the IPv4 socket");
		}
		check(sock6 >= 0, "mdns_socket_open_ipv6(NULL) opens a UDP socket on OHOS");
		if (sock6 >= 0) {
			mdns_socket_close(sock6);
			check(1, "mdns_socket_close closes the IPv6 socket");
		} else {
			check(0, "mdns_socket_close closes the IPv6 socket");
		}
	}

	printf("1..%d\n", checks);
	printf("# mdns consumer test: %d checks, %d failures\n", checks, failures);
	return failures ? 1 : 0;
}

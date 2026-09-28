/*
 * kamailio outbound 模块 —— 消费者端到端用例。
 *
 * 口径：本用例是「完整消费者用例」而不是纯断言脚本 —— 它以真实消费者身份
 * 把一个进程内可加载的 kamailio 运行时（core 符号层见 kamailio_core_stub.c）
 * 与被测模块 outbound.so 组起来，走完模块的真实链路：
 *
 *   dlopen(outbound.so)                      ← 真实加载与重定位
 *     → dlsym("exports")                     ← 读模块导出表（名称/命令/参数）
 *       → exports->init_mod_f()               ← mod_init：shm 分配 token 密钥、
 *                                                配置组声明、依赖探测
 *         → bind_ob(&api)                     ← 模块 API 绑定（它给其它模块用的入口）
 *           → api.encode_flow_token()          ← 真实生成 flow-token（HMAC + base64）
 *             → api.decode_flow_token()        ← 真实校验/还原（含 HMAC 负例、长度负例）
 *               → api.use_outbound()           ← 真实调用
 *                 → exports->destroy_mod_f()   ← 真实销毁（校验分配/释放平衡）
 *
 * 断言分两类：
 *   [链路]  模块是否真的被加载、初始化、绑定、执行并可销毁；
 *   [语义]  产物是否符合 flow-token 规范 —— 用例用**独立实现**的 base64
 *           解码器交叉验证模块输出，并逐字节核对
 *           <HMAC-SHA1-80><proto><dst_ip><dst_port><src_ip><src_port> 布局
 *           （src/modules/outbound/outbound_mod.c:149-232）。
 *
 * 退出码：0 = 全部断言通过；1 = 存在失败断言。
 */
#include "kamailio_core_stub.h"

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Linux/musl 的地址族取值（模块内比较的是这两个值）。 */
#define TEST_AF_INET 2
#define TEST_AF_INET6 10

/* IPPROTO_UDP：模块把 rcv->proto 编入 token 的协议字节。 */
#define TEST_PROTO_UDP 17
/* IPPROTO_TCP：同一字节承载协议，用例用 TCP 复核协议矩阵（模块逐字节透传）。 */
#define TEST_PROTO_TCP 6

/* ── 断言框架 ─────────────────────────────────────────────────────────────── */
static int g_pass = 0;
static int g_fail = 0;

static void section(const char *name)
{
	printf("\n== %s ==\n", name);
	fflush(stdout);
}

static void ok(int cond, const char *what)
{
	if(cond) {
		g_pass++;
		printf("  PASS  %s\n", what);
	} else {
		g_fail++;
		printf("  FAIL  %s\n", what);
	}
	fflush(stdout);
}

static void eq_int(long got, long want, const char *what)
{
	if(got == want) {
		g_pass++;
		printf("  PASS  %s (=%ld)\n", what, got);
	} else {
		g_fail++;
		printf("  FAIL  %s: got %ld want %ld\n", what, got, want);
	}
	fflush(stdout);
}

static void eq_str(const char *got, const char *want, const char *what)
{
	if(got != NULL && want != NULL && strcmp(got, want) == 0) {
		g_pass++;
		printf("  PASS  %s (=%s)\n", what, got);
	} else {
		g_fail++;
		printf("  FAIL  %s: got %s want %s\n", what, got != NULL ? got : "(null)",
				want != NULL ? want : "(null)");
	}
	fflush(stdout);
}

static void eq_bytes(const unsigned char *got, const unsigned char *want, size_t n,
		const char *what)
{
	size_t i;
	int same = 1;

	for(i = 0; i < n; i++)
		if(got[i] != want[i]) {
			same = 0;
			break;
		}
	if(same) {
		g_pass++;
		printf("  PASS  %s (%zu bytes)\n", what, n);
	} else {
		g_fail++;
		printf("  FAIL  %s:\n    got ", what);
		for(i = 0; i < n; i++)
			printf("%02x", got[i]);
		printf("\n    want ");
		for(i = 0; i < n; i++)
			printf("%02x", want[i]);
		printf("\n");
	}
	fflush(stdout);
}

/* ── 参考 base64（独立实现，用于交叉验证被测模块的编码产物）───────────────
 * 只用于校验，不参与模块内部计算：模块走的是 core basex.h 的 8K 查表实现。 */
static const char REF_B64_ALPHA[] =
		"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static size_t ref_b64_enc_len(size_t n)
{
	return ((n + 2) / 3) * 4;
}

static int ref_b64_dec_char(char c)
{
	const char *p = strchr(REF_B64_ALPHA, c);

	if(p == NULL || c == '\0')
		return -1;
	return (int)(p - REF_B64_ALPHA);
}

/* 返回解出的字节数；遇到非法字符或长度非法返回 -1；同时拒绝非 4 倍数的输入。 */
static int ref_b64_dec(const char *in, size_t n, unsigned char *out, size_t outsz)
{
	size_t i;
	size_t o = 0;
	unsigned char quad[4];

	if(n == 0 || (n % 4) != 0)
		return -1;
	for(i = 0; i < n; i += 4) {
		int k;
		int pad = 0;

		for(k = 0; k < 4; k++) {
			if(in[i + k] == '=') {
				/* '=' 只允许出现在最后 4 字节组的最多最后两位。 */
				if(i + 4 != n || k < 2)
					return -1;
				pad++;
				quad[k] = 0;
			} else {
				int v = ref_b64_dec_char(in[i + k]);
				if(v < 0)
					return -1;
				quad[k] = (unsigned char)v;
			}
		}
		if(pad > 2 || (pad > 0 && (in[i + 3] != '=' || (pad == 2 && in[i + 2] != '='))))
			return -1;
		{
			unsigned int v = ((unsigned int)quad[0] << 18) | ((unsigned int)quad[1] << 12)
							 | ((unsigned int)quad[2] << 6) | (unsigned int)quad[3];
			int bytes = (pad == 2) ? 1 : (pad == 1 ? 2 : 3);

			if(o + (size_t)bytes > outsz)
				return -1;
			out[o++] = (unsigned char)((v >> 16) & 0xff);
			if(bytes > 1)
				out[o++] = (unsigned char)((v >> 8) & 0xff);
			if(bytes > 2)
				out[o++] = (unsigned char)(v & 0xff);
		}
	}
	return (int)o;
}

/* ── ABI 静态自检：桩里复刻的 core 布局若与本机不符，编译期即失败 ───────────
 * （数值来源：core 头文件与 #3 步探针实测，见 kamailio_core_stub.h 顶部注释）*/
typedef struct e2e_str_ {
	char *s;
	int len;
} e2e_str_t;

_Static_assert(sizeof(e2e_str_t) == 16, "core str 是 {char*,int}（16 字节）");
_Static_assert(sizeof(stub_receive_info_t) == 208, "receive_info 应为 208 字节");
_Static_assert(sizeof(stub_ldv_t) == 224, "sip_msg.ldv 应为 224 字节");
_Static_assert(offsetof(stub_sip_msg_t, ldv) == 1792, "sip_msg.ldv 偏移应为 1792");
_Static_assert(offsetof(stub_ldv_flow_t, rcv) == 8, "ldv.flow.rcv 偏移应为 8");
_Static_assert(sizeof(cmd_export_t) == 48, "cmd_export_t 应为 48 字节");
_Static_assert(sizeof(param_export_t) == 24, "param_export_t 应为 24 字节");
_Static_assert(sizeof(module_exports_t) == 80, "module_exports 应为 80 字节");

/* ── 模块 API（src/modules/outbound/api.h:40 `ob_api_t`）─────────────────
 * { encode_flow_token(str*, receive_info*); decode_flow_token(sip_msg*,
 *   receive_info**, str); use_outbound(sip_msg*); } */
typedef int (*e2e_encode_f)(e2e_str_t *, stub_receive_info_t *);
typedef int (*e2e_decode_f)(stub_sip_msg_t *, stub_receive_info_t **, e2e_str_t);
typedef int (*e2e_use_f)(stub_sip_msg_t *);
typedef int (*e2e_bind_f)(void *);

typedef struct e2e_ob_api_ {
	e2e_encode_f encode_flow_token;
	e2e_decode_f decode_flow_token;
	e2e_use_f use_outbound;
} e2e_ob_api_t;

/* 模块 modparam_t 取值（src/core/sr_module.h 的 param_export 语义）。 */
#define E2E_PARAM_INT 2
#define E2E_PARAM_STR 4

static void fill_ipv4(stub_ip_addr_t *ip, const unsigned char a[4])
{
	int i;

	ip->af = TEST_AF_INET;
	ip->len = 4;
	for(i = 0; i < 4; i++)
		ip->u.addr[i] = a[i];
}

static void fill_ipv6(stub_ip_addr_t *ip, const unsigned char a[16])
{
	int i;

	ip->af = TEST_AF_INET6;
	ip->len = 16;
	for(i = 0; i < 16; i++)
		ip->u.addr[i] = a[i];
}

static int find_cmd_index(cmd_export_t *cmds, const char *name)
{
	int i;

	if(cmds == NULL)
		return -1;
	for(i = 0; cmds[i].name != NULL; i++)
		if(strcmp(cmds[i].name, name) == 0)
			return i;
	return -1;
}

static int find_param_type(param_export_t *params, const char *name, unsigned int *type)
{
	int i;

	if(params == NULL)
		return 0;
	for(i = 0; params[i].name != NULL; i++)
		if(strcmp(params[i].name, name) == 0) {
			if(type != NULL)
				*type = params[i].type;
			return 1;
		}
	return 0;
}

static int report(void)
{
	printf("\nE2E_ASSERTIONS_OK=%d E2E_ASSERTIONS_FAILED=%d\n", g_pass, g_fail);
	printf("RESULT: %d/%d assertions passed\n", g_pass, g_pass + g_fail);
	fflush(stdout);
	return g_fail == 0 ? 0 : 1;
}

int main(void)
{
	const char *module_path = getenv("OUTBOUND_MODULE");
	void *handle;
	module_exports_t *exports;
	cmd_export_t *cmds;
	param_export_t *params;
	unsigned int ptype = 0;
	int bind_idx;
	void (*destroy_f)(void);
	e2e_ob_api_t api;
	stub_receive_info_t ri;
	stub_receive_info_t ri6;
	stub_receive_info_t ri_tcp;
	stub_receive_info_t *dec = NULL;
	stub_receive_info_t *dec_again = NULL;
	stub_receive_info_t *dec_tcp = NULL;
	stub_sip_msg_t msg;
	stub_sip_msg_t fresh;
	stub_sip_msg_t reply;
	e2e_str_t tok = {NULL, 0};
	e2e_str_t tok6 = {NULL, 0};
	e2e_str_t tok_tcp = {NULL, 0};
	int init_before;
	char tamper[128];
	unsigned char raw[128];
	int n;
	const unsigned char src4[4] = {192, 0, 2, 1};
	const unsigned char dst4[4] = {198, 51, 100, 7};
	const unsigned char src6[16] = {0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
			0, 0x99};
	const unsigned char dst6[16] = {0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
			0, 0x01};

	printf("kamailio outbound module — consumer end-to-end test\n");

	section("0. 运行前置");
	ok(module_path != NULL, "OUTBOUND_MODULE 已注入（由 test_package/conanfile.py 提供）");
	if(module_path == NULL) {
		fprintf(stderr, "OUTBOUND_MODULE is not set\n");
		return report();
	}
	printf("  module = %s\n", module_path);

	stub_init();
	stub_init_basex();

	section("1. dlopen：模块真实加载与重定位");
	handle = dlopen(module_path, RTLD_NOW | RTLD_GLOBAL);
	ok(handle != NULL, "dlopen(outbound.so, RTLD_NOW|RTLD_GLOBAL) 成功");
	if(handle == NULL) {
		printf("  dlerror: %s\n", dlerror());
		return report();
	}

	section("2. 导出表：消费者据此识别模块能力");
	exports = (module_exports_t *)dlsym(handle, "exports");
	ok(exports != NULL, "dlsym(\"exports\") 取到 module_exports");
	if(exports == NULL) {
		printf("  dlerror: %s\n", dlerror());
		return report();
	}
	eq_str(exports->name, "outbound", "模块名");
	eq_int((long)exports->dlflags, 0, "dlflags = DEFAULT_DLFLAGS");
	ok(exports->init_mod_f != NULL, "init_mod_f 非空");
	ok(exports->destroy_mod_f != NULL, "destroy_mod_f 非空");

	cmds = exports->cmds;
	params = exports->params;
	bind_idx = find_cmd_index(cmds, "bind_ob");
	ok(bind_idx >= 0, "命令 bind_ob 已导出");
	if(bind_idx >= 0)
		eq_int(cmds[bind_idx].param_no, 1, "bind_ob 参数个数 = 1");

	ok(find_param_type(params, "force_outbound_flag", &ptype), "参数 force_outbound_flag 存在");
	eq_int((long)ptype, E2E_PARAM_INT, "force_outbound_flag 为整型参数");
	ptype = 0;
	ok(find_param_type(params, "force_no_outbound_flag", &ptype),
			"参数 force_no_outbound_flag 存在");
	eq_int((long)ptype, E2E_PARAM_INT, "force_no_outbound_flag 为整型参数");
	ptype = 0;
	ok(find_param_type(params, "flow_token_secret", &ptype), "参数 flow_token_secret 存在");
	eq_int((long)ptype, E2E_PARAM_STR, "flow_token_secret 为字符串参数");

	section("3. 生命周期：mod_init（真实分配 / 配置组 / 依赖探测）");
	eq_int(stub_cfg_declare_calls, 0, "初始化前未声明配置组（基线）");
	eq_int(stub_shm_alloc_calls, 0, "初始化前无 shm 分配（基线）");
	eq_int(((int (*)(void))exports->init_mod_f)(), 0, "mod_init 返回 0");
	ok(stub_shm_alloc_calls >= 1, "mod_init 经 core shm 分配器取得 flow-token 密钥");
	ok(stub_cfg_declare_calls >= 1, "mod_init 声明了配置组");
	eq_str(stub_cfg_group, "outbound", "配置组名");
	ok(stub_cfg_handle_ptr != NULL && stub_cfg_handle_ptr != stub_cfg_default_ptr,
			"cfg_declare 回填了独立配置实例");
	ok(stub_find_module_calls >= 1, "mod_init 探测了 stun 模块（module_loaded 路径）");

	section("4. API 绑定：bind_ob（模块对外入口）");
	ok(bind_idx >= 0, "存在 bind_ob 命令项");
	eq_int(((e2e_bind_f)cmds[bind_idx].function)(&api), 0, "bind_ob(&api) 返回 0");
	ok(api.encode_flow_token != NULL, "api.encode_flow_token 已绑定");
	ok(api.decode_flow_token != NULL, "api.decode_flow_token 已绑定");
	ok(api.use_outbound != NULL, "api.use_outbound 已绑定");
	eq_int(((e2e_bind_f)cmds[bind_idx].function)(NULL), -1, "bind_ob(NULL) 返回 -1（负例）");

	section("5. flow-token 编码：HMAC-SHA1-80 + base64（IPv4/IPv6）");
	memset(&ri, 0, sizeof(ri));
	fill_ipv4(&ri.src_ip, src4);
	fill_ipv4(&ri.dst_ip, dst4);
	ri.src_port = 5060;
	ri.dst_port = 5070;
	ri.proto = TEST_PROTO_UDP;
	ri.bind_address = NULL;

	eq_int(api.encode_flow_token(&tok, &ri), 0, "encode_flow_token(IPv4) 返回 0");
	ok(tok.s != NULL, "返回的 token 缓冲区非空（模块内经 pkg_malloc 分配）");
	eq_int(tok.len, 32, "IPv4 flow-token 为 32 字符 base64（23 字节）");
	n = ref_b64_dec(tok.s, (size_t)tok.len, raw, sizeof(raw));
	eq_int(n, 23, "独立 base64 解码器解出 23 字节（规范长度）");
	if(n == 23) {
		eq_int(raw[10] & 0x80, 0, "IPv4：地址族标志位为 0");
		eq_int(raw[10] & 0x7f, TEST_PROTO_UDP, "协议字节携带 rcv->proto(UDP)");
		eq_bytes(raw + 11, dst4, 4, "目的地址 = rcv->dst_ip");
		eq_int((raw[15] << 8) | raw[16], 5070, "目的端口 = rcv->dst_port（网络序）");
		eq_bytes(raw + 17, src4, 4, "源地址 = rcv->src_ip");
		eq_int((raw[21] << 8) | raw[22], 5060, "源端口 = rcv->src_port（网络序）");
	}

	memset(&ri6, 0, sizeof(ri6));
	fill_ipv6(&ri6.src_ip, src6);
	fill_ipv6(&ri6.dst_ip, dst6);
	ri6.src_port = 5060;
	ri6.dst_port = 5070;
	ri6.proto = TEST_PROTO_UDP;
	ri6.bind_address = NULL;
	eq_int(api.encode_flow_token(&tok6, &ri6), 0, "encode_flow_token(IPv6) 返回 0");
	eq_int(tok6.len, 64, "IPv6 flow-token 为 64 字符 base64（47 字节）");
	n = ref_b64_dec(tok6.s, (size_t)tok6.len, raw, sizeof(raw));
	eq_int(n, 47, "IPv6 token 独立解码为 47 字节");
	if(n == 47) {
		eq_int(raw[10] & 0x80, 0x80, "IPv6：地址族标志位置位");
		eq_bytes(raw + 11, dst6, 16, "IPv6 目的地址 = rcv->dst_ip");
		eq_int((raw[27] << 8) | raw[28], 5070, "IPv6 目的端口 = rcv->dst_port");
		eq_bytes(raw + 29, src6, 16, "IPv6 源地址 = rcv->src_ip");
		eq_int((raw[45] << 8) | raw[46], 5060, "IPv6 源端口 = rcv->src_port");
	}
	eq_int(api.encode_flow_token(NULL, &ri), -1, "encode_flow_token(NULL,...) 返回 -1（负例）");

	section("6. flow-token 解码：真实校验与还原");
	memset(&msg, 0, sizeof(msg));
	eq_int(api.decode_flow_token(&msg, &dec, tok), 0, "decode_flow_token 返回 0");
	ok(dec != NULL, "回填 receive_info 指针");
	ok(dec == &msg.ldv.flow.rcv, "回填的是消息内 ldv.flow.rcv（core 语义）");
	eq_int(msg.ldv.flow.decoded, 1, "msg->ldv.flow.decoded 置位");
	if(dec != NULL) {
		eq_bytes(dec->dst_ip.u.addr, dst4, 4, "还原目的地址");
		eq_int(dec->dst_port, 5070, "还原目的端口");
		eq_bytes(dec->src_ip.u.addr, src4, 4, "还原源地址");
		eq_int(dec->src_port, 5060, "还原源端口");
		eq_int(dec->proto, TEST_PROTO_UDP, "还原协议");
		eq_int(dec->dst_ip.af, TEST_AF_INET, "还原地址族 = AF_INET");
	}
	eq_int(api.decode_flow_token(&msg, &dec_again, tok), 0, "已解码消息再解一次返回 0（decoded 短路）");
	ok(dec_again == dec, "再次解码返回同一 receive_info");

	memset(&fresh, 0, sizeof(fresh));
	eq_int(api.decode_flow_token(&fresh, &dec, (e2e_str_t){NULL, 0}), -2, "token.s == NULL → -2");
	eq_int(api.decode_flow_token(&fresh, &dec, (e2e_str_t){(char *)"", 0}), -2, "token.len == 0 → -2");
	eq_int(api.decode_flow_token(&fresh, &dec, (e2e_str_t){(char *)"AAAA", 4}), -2,
			"base64 合法但长度非法 → -2");
	eq_int(api.decode_flow_token(&fresh, &dec, (e2e_str_t){(char *)"not-base64!!", 12}), -2,
			"非 base64 字符 → -2");

	memset(tamper, 0, sizeof(tamper));
	memcpy(tamper, tok.s, (size_t)tok.len);
	tamper[5] = (tamper[5] == 'A') ? 'B' : 'A';
	eq_int(api.decode_flow_token(&fresh, &dec, (e2e_str_t){tamper, tok.len}), -1,
			"HMAC 校验失败（篡改 token）→ -1");

	section("6b. 协议矩阵：同一消费者流程改用 TCP 复核");
	memset(&ri_tcp, 0, sizeof(ri_tcp));
	fill_ipv4(&ri_tcp.src_ip, src4);
	fill_ipv4(&ri_tcp.dst_ip, dst4);
	ri_tcp.src_port = 5060;
	ri_tcp.dst_port = 5070;
	ri_tcp.proto = TEST_PROTO_TCP;
	ri_tcp.bind_address = NULL;
	eq_int(api.encode_flow_token(&tok_tcp, &ri_tcp), 0, "encode_flow_token(TCP) 返回 0");
	n = ref_b64_dec(tok_tcp.s, (size_t)tok_tcp.len, raw, sizeof(raw));
	eq_int(n, 23, "TCP token 独立 base64 解码为 23 字节");
	if(n == 23) {
		eq_int(raw[10] & 0x80, 0, "TCP：地址族标志位仍为 0");
		eq_int(raw[10] & 0x7f, TEST_PROTO_TCP, "协议字节携带 rcv->proto(TCP)");
	}
	memset(&fresh, 0, sizeof(fresh));
	eq_int(api.decode_flow_token(&fresh, &dec_tcp, tok_tcp), 0, "TCP token 解码返回 0");
	ok(dec_tcp != NULL, "TCP token 回填 receive_info");
	if(dec_tcp != NULL) {
		eq_int(dec_tcp->proto, TEST_PROTO_TCP, "还原协议 = TCP");
		eq_bytes(dec_tcp->dst_ip.u.addr, dst4, 4, "TCP token 还原目的地址");
		eq_int(dec_tcp->dst_port, 5070, "TCP token 还原目的端口");
	}
	stub_pkg_free(tok_tcp.s);
	tok_tcp.s = NULL;

	section("7. use_outbound：真实调用（非 SIP 请求路径）");
	memset(&reply, 0, sizeof(reply));
	eq_int(api.use_outbound(&reply), 0, "非 SIP 请求消息返回 0（首行类型检查）");

	section("8. 销毁与资源平衡");
	destroy_f = (void (*)(void))exports->destroy_mod_f;
	destroy_f();
	eq_int(stub_shm_alloc_calls, stub_shm_free_calls,
			"shm 分配/释放平衡（destroy 释放了 mod_init 分配的密钥）");
	section("8b. 生命周期复跑：destroy 后重新 init（消费者热重载语义）");
	init_before = stub_shm_alloc_calls;
	eq_int(((int (*)(void))exports->init_mod_f)(), 0, "第二次 mod_init 返回 0");
	ok(stub_shm_alloc_calls > init_before, "第二次 mod_init 重新经 shm 取得密钥");
	destroy_f();
	eq_int(stub_shm_alloc_calls, stub_shm_free_calls, "二次 init/destroy 后 shm 分配/释放仍平衡");

	stub_pkg_free(tok.s);
	stub_pkg_free(tok6.s);
	eq_int(stub_pkg_alloc_calls, stub_pkg_free_calls, "pkg 分配/释放平衡（模块内 token 缓冲）");
	ok(dlclose(handle) == 0, "dlclose 成功");

	return report();
}

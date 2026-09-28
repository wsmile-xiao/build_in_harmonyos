/* kamailio_core_stub.c — kamailio core 未定义符号的最小可解析层（测试专用）
 *
 * 符号清单来源：对 kemix.so 执行 `llvm-nm -u`（本地原生编译同源模块实测），共 45 个
 * 未定义符号，其中 12 个由 libc/CRT 提供（__at_fini / __cxa_finalize /
 * __register_frame_info / __deregister_frame_info / fprintf / getenv / memset / sleep /
 * stderr / strlen / strncpy / time），**不在此桩内重复定义**（与 libc 冲突）；
 * 其余 33 个 kamailio core 符号在本文件给出定义。
 *
 * 只有两个符号在 e2e 路径上被真实调用（其余仅需加载期可解析）：
 *   - sr_kemi_modules_add()  — 记录 KEMI 函数表指针并计数（供 e2e 断言注册行为）
 *   - sr_kemi_xval_null()    — 语义与 src/core/kemi.c 一致（NONE 模式 -> SR_KEMIP_NULL）
 */
#include "kamailio_core_stub.h"

#include <string.h>

int kamailio_stub_assertions = 0;

/* 被调用的两个 core 符号：完整语义实现 */
const sr_kemi_t *kamailio_stub_last_kemi_table = NULL;
int kamailio_stub_kemi_add_calls = 0;

int sr_kemi_modules_add(const sr_kemi_t *kt)
{
	kamailio_stub_kemi_add_calls++;
	kamailio_stub_last_kemi_table = kt;
	return 0;
}

void sr_kemi_xval_null(sr_kemi_xval_t *xval, int rmode)
{
	if(xval == NULL)
		return;
	memset(xval, 0, sizeof(*xval));
	switch(rmode)
	{
		case SR_KEMI_XVAL_NULL_PRINT: /* core: 返回 "<null>" 字符串 */
			xval->vtype = SR_KEMIP_STR;
			xval->v.s.s = (char *)"<null>";
			xval->v.s.len = 6;
			return;
		case SR_KEMI_XVAL_NULL_EMPTY: /* core: 返回空字符串 */
			xval->vtype = SR_KEMIP_STR;
			xval->v.s.s = (char *)"";
			xval->v.s.len = 0;
			return;
		case SR_KEMI_XVAL_NULL_ZERO: /* core: 返回整数 0 */
			xval->vtype = SR_KEMIP_INT;
			xval->v.n = 0;
			return;
		default: /* SR_KEMI_XVAL_NULL_NONE */
			xval->vtype = SR_KEMIP_NULL;
			return;
	}
}

/* ------------------------------------------------------------------
 * 其余 core 符号：仅需在 dlopen（RTLD_NOW）时全部可解析。
 * e2e 路径不调用它们（模块无构造器；mod_register 只使用上面两个符号），
 * 因此这里给出最小定义而非完整语义。
 * ------------------------------------------------------------------ */

/* core 全局变量 */
int my_pid = 1;
int process_no = 0;
int log_level_info = 0;
int log_prefix_val = 0;
void *_km_log_func = NULL;
void *_ksr_slog_func = NULL;

/* 调试/日志接口（src/core/dprint.{h,c}） */
int dprint_crit;
int dprint_color;
void dprint_color_reset(void)
{
	return;
}
int log_color;
int log_stderr;

/* 配置/计数器（src/core/cfg/cfg.c、src/core/ut.c、src/core/atomic/*） */
int get_debug_level(void)
{
	return 0;
}
int get_debug_facility(void)
{
	return 0;
}
int _atomic_lock_set(void)
{
	return 0;
}

/* 伪变量缓冲（src/core/pvapi.c） */
char *pv_get_buffer(void)
{
	return NULL;
}
int pv_get_buffer_size(void)
{
	return 0;
}

/* 消息解析（src/core/parser/*） */
int parse_headers(void *msg, int flags, int next)
{
	return -1;
}
int parse_sip_msg_uri(void *msg)
{
	return -1;
}
int parse_from_header(void *msg)
{
	return -1;
}
int parse_from_uri(void *msg)
{
	return -1;
}
int parse_to_header(void *msg)
{
	return -1;
}
int parse_to_uri(void *msg)
{
	return -1;
}
int parse_credentials(void *msg)
{
	return -1;
}
int parse_contact_headers(void *msg)
{
	return -1;
}

/* 网络/传输（src/core/ip_addr.h、src/core/tcp_main.c、src/core/forward.c） */
char *ip_addr2a(void *ip)
{
	return NULL;
}
char *get_src_address_socket(void)
{
	return NULL;
}
int get_src_uri(void)
{
	return 0;
}
char *get_valid_proto_string(void)
{
	return NULL;
}
void *tcpconn_get(int id, void *dst, int dst_port, void *src, int timeout)
{
	(void)id;
	(void)dst;
	(void)dst_port;
	(void)src;
	(void)timeout;
	return NULL;
}

/* 消息体/预处理（src/core/msg_translator.c、src/core/ppcfg.c） */
char *get_body(void *msg)
{
	return NULL;
}
int pp_define_get(int n)
{
	(void)n;
	return 0;
}

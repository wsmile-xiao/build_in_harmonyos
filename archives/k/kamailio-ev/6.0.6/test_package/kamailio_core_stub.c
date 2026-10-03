/* kamailio_core_stub.c — kamailio core 未定义符号的最小可解析层（测试专用）
 *
 * 符号清单来源：对**本次构建产物** evapi.so 执行 `nm -D --undefined-only`
 * （OHOS aarch64 产物实测），共 97 个未定义符号，分四类：
 *
 *   (a) weak CRT 符号（4）：__at_fini / __cxa_finalize / __deregister_frame_info /
 *       __register_frame_info —— 不由本桩定义（libc/CRT 提供）。
 *   (b) libc（33）：accept/atoi/bind/close/exit/fcntl/fprintf/free/freeaddrinfo/
 *       gai_strerror/getaddrinfo/getpid/inet_ntop/listen/malloc/memcpy/memset/ntohs/
 *       perror/read/recv/sched_yield/select/setsockopt/snprintf/socket/socketpair/
 *       stderr/strchr/strlen/strncmp/strncpy/write —— 不由本桩定义（与 libc 冲突）。
 *   (c) libev.so（4）：ev_default_loop / ev_io_start / ev_io_stop / ev_run
 *       —— 由 conan 依赖 libev/4.33 的 libev.so 在运行时解析（e2e 真实调用）。
 *   (d) kamailio core（56）：本文件给出定义。
 *
 * 类型口径严格对齐上游头文件，避免桩层与真实 ABI 错位（gcrypt 先例教训：桩层类型错位
 * 会因日志路径解引用野指针而 SIGSEGV，掩盖真实失败原因）：
 *   my_pid              — src/core/dprint.h:161  `int my_pid(void)`（函数，非变量）
 *   dprint_color        — src/core/dprint.h:217  `void dprint_color(int level)`（函数）
 *   log_level_info      — src/core/dprint.h:203  `struct log_level_info[]`（数组）
 *   log_prefix_val      — src/core/dprint.h:169  `str *log_prefix_val`
 *   _km_log_func        — src/core/dprint.h:175  `km_log_f _km_log_func`
 *   _shm_root           — src/core/mem/shm.h:46   `sr_shm_api_t _shm_root`（对象，非指针）
 *   _atomic_lock_set    — src/core/atomic/atomic_unknown.h:135 `gen_lock_set_t *`
 *   event_rt            — src/core/route.h:94      `struct route_list event_rt`
 *   route_lookup        — src/core/route.h:102     `int route_lookup(struct route_list *rt, char *name)`
 *   sr_kemi_modules_add — src/core/kemi.h:558      `int sr_kemi_modules_add(sr_kemi_t *klist)`
 *
 * 日志路径说明：上游 LOG_FX 宏先判 `dprint_crit == 0` 且
 * `get_debug_level(LOG_MNAME, LOG_MNAME_LEN) >= level`；本桩 get_debug_level() 返回 0
 * 低于所有级别，故模块内 LM_* 全部不落日志。但桩层仍给出**可用的**日志函数指针
 * （指向 sink），以免将来出现日志路径时因空指针崩溃掩盖真实失败原因。
 *
 * e2e 路径上被**真实调用**的 core 符号只有两个：
 *   sr_kemi_modules_add() — 记录 mod_register() 注册进来的 KEMI 函数表（语义与
 *                           src/core/kemi.c:3435 一致）
 *   route_lookup()        — 记录 evapi_init_environment() 解析的事件路由名（恒返回 -1，
 *                           即"未配置"分支，避免读取 event_rt.rlist 未初始化内容）
 * 其余符号仅需在 dlopen（RTLD_NOW）时全部可解析。
 */
#include "kamailio_core_stub.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

/* ---- 头部不完整类型的占位定义（仅用于声明，不参与 e2e 逻辑） ---- */
struct sip_msg;
struct action;
struct run_act_ctx;
struct receiver;
struct cfg_group;
struct cfg_group_inst;
struct cfg_child_cb;
struct pv_param;
struct pv_value;
struct pv_elem;
struct fparam;
struct sr_kemi_eng;

int kamailio_stub_assertions = 0;

/* ---- 被真实调用的 core 符号 1：KEMI 表注册（语义同 src/core/kemi.c:3435） ---- */
const sr_kemi_t *kamailio_stub_last_kemi_table = NULL;
int kamailio_stub_kemi_add_calls = 0;

int sr_kemi_modules_add(sr_kemi_t *klist)
{
	kamailio_stub_kemi_add_calls++;
	kamailio_stub_last_kemi_table = klist;
	return 0;
}

/* ---- 被真实调用的 core 符号 2：事件路由名解析（记录调用，恒返回 -1） ---- */
int kamailio_stub_route_lookup_calls = 0;
char kamailio_stub_route_names[STUB_MAX_ROUTES][64];
void *kamailio_stub_route_rts_arg = NULL;

int route_lookup(struct route_list *rt, char *name)
{
	if(kamailio_stub_route_rts_arg == NULL)
		kamailio_stub_route_rts_arg = (void *)rt;
	if(kamailio_stub_route_lookup_calls < STUB_MAX_ROUTES)
	{
		snprintf(kamailio_stub_route_names[kamailio_stub_route_lookup_calls],
				sizeof(kamailio_stub_route_names[0]), "%s", name ? name : "()");
	}
	kamailio_stub_route_lookup_calls++;
	return -1; /* "route not found" 分支：模块据此把 rts 索引置 -1 */
}

/* event_rt（src/core/route.h:94）：本桩只提供对象本体，因 route_lookup 恒返回 -1，
 * 模块不会读取 event_rt.rlist。 */
struct route_list event_rt;

/* ------------------------------------------------------------------
 * 以下 core 符号：仅需在 dlopen（RTLD_NOW）时全部可解析（e2e 不调用）。
 * ------------------------------------------------------------------ */

/* 内存池根（src/core/mem/shm.h:46，对象类型 sr_shm_api_t，此处给出等尺寸存储） */
struct kamailio_stub_shm_api
{
	void *pool;
	int size;
	int used;
	int dummy[13];
};
struct kamailio_stub_shm_api _shm_root = {0};

/* 原子锁集指针（src/core/atomic/atomic_unknown.h:135） */
void *_atomic_lock_set = NULL;

/* cfg 框架（src/core/cfg/cfg_struct.h:186-196） */
void *cfg_group = NULL;
void *cfg_global = NULL;
void *cfg_local = NULL;
int cfg_block_size = 0;
void *cfg_global_lock = NULL;
void *cfg_child_cb = NULL;
void **cfg_child_cb_first = NULL;
void **cfg_child_cb_last = NULL;
int cfg_ginst_count = 0;

void cfg_move_handle(void *group, void *src_ginst, void *dst_ginst, int mode)
{
	(void)group;
	(void)src_ginst;
	(void)dst_ginst;
	(void)mode;
}

void cfg_register_child(int num)
{
	(void)num;
}

int cfg_child_init(void)
{
	return 0;
}

/* 进程/调试状态（src/core/dprint.h、src/core/pt.h） */
int process_no = 0;
volatile int dprint_crit = 0;
int log_color = 0;
int log_stderr = 0;
int route_type = 0; /* 运行路由时由 core 赋值；e2e 不依赖其值 */

int my_pid(void)
{
	return 1;
}

/* 日志级别表（src/core/dprint.h:181-203）—— 索引口径 level - L_ALERT，
 * 这里给足条目并填上合法名字指针，确保日志路径即使被走到也不会解引用野指针 */
struct log_level_info
{
	char *name;
	int syslog_level;
};
struct log_level_info log_level_info[] = {
	{"ALERT", 0}, {"BUG", 1}, {"CRIT2", 2}, {"CRIT", 3}, {"ERR", 4},
	{"WARN", 5}, {"NOTICE", 6}, {"INFO", 7}, {"DBG", 8}, {"XXXX", 9},
};

str *log_prefix_val = NULL;

/* 日志落点：LOG_FX 在 log_stderr 为真时走 fprintf(stderr,...)，否则调用本指针。
 * 指向 sink 而非 NULL——保证任何日志写入都不会因空指针崩溃。 */
static void kamailio_stub_log_sink(int level, const char *format, ...)
{
	va_list ap;
	(void)level;
	va_start(ap, format);
	fprintf(stderr, "[stub-log] ");
	vfprintf(stderr, format, ap);
	va_end(ap);
}

typedef void (*kamailio_stub_log_f)(int, const char *, ...);
kamailio_stub_log_f _km_log_func = kamailio_stub_log_sink;
kamailio_stub_log_f _ksr_slog_func = kamailio_stub_log_sink;

/* 调试级别（src/core/dprint.h:188-190）：返回 0 = 低于所有级别，模块日志静默 */
int get_debug_level(char *mname, int mnlen)
{
	(void)mname;
	(void)mnlen;
	return 0;
}
int get_debug_facility(char *mname, int mnlen)
{
	(void)mname;
	(void)mnlen;
	return 0;
}

/* 终端配色（src/core/dprint.h:217-218）—— 符号是函数，非变量 */
void dprint_color(int level)
{
	(void)level;
}
void dprint_color_reset(void)
{
	return;
}

/* 伪变量缓冲 / 取值辅助（src/core/pvapi.c、src/core/pvar.h） */
int pv_get_null(struct sip_msg *msg, void *param, void *res)
{
	(void)msg;
	(void)param;
	(void)res;
	return 0;
}
int pv_get_sintval(struct sip_msg *msg, void *param, void *res)
{
	(void)msg;
	(void)param;
	(void)res;
	return 0;
}
int pv_get_strval(struct sip_msg *msg, void *param, void *res)
{
	(void)msg;
	(void)param;
	(void)res;
	return 0;
}
int pv_get_strzval(struct sip_msg *msg, void *param, void *res)
{
	(void)msg;
	(void)param;
	(void)res;
	return 0;
}
int pv_printf_mode(struct sip_msg *msg, void *list, int mode, char *buf, int *len)
{
	(void)msg;
	(void)list;
	(void)mode;
	(void)buf;
	(void)len;
	return 0;
}
int pv_printf_size(struct sip_msg *msg, void *list)
{
	(void)msg;
	(void)list;
	return 0;
}

/* SPVE/vstr 参数 fixup（src/core/mod_fix.c、mod_fix.h） */
int fixup_spve_all(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}
int fixup_free_spve_all(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}
int fixup_spve_null(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}
int fixup_free_spve_null(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}
int fixup_vstr_all(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}
int fixup_free_vstr_all(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}
int get_str_fparam(void *dst, struct sip_msg *msg, void *param)
{
	(void)dst;
	(void)msg;
	(void)param;
	return -1;
}

/* 模块/进程框架（src/core/sr_module.c、pt.c、fmsg.c、receive.c、action.c、kemi.c） */
void *find_export(char *name, int param_no, int flags)
{
	(void)name;
	(void)param_no;
	(void)flags;
	return NULL;
}
int fork_process(int child_id, char *desc, int make_sock)
{
	(void)child_id;
	(void)desc;
	(void)make_sock;
	return -1;
}
int register_procs(int no)
{
	(void)no;
	return 0;
}
int init_child(int rank)
{
	(void)rank;
	return 0;
}
int faked_msg_init(void)
{
	return 0;
}
int faked_msg_get_new(struct sip_msg *fmsg)
{
	(void)fmsg;
	return -1;
}
void free_sip_msg(struct sip_msg *const msg)
{
	(void)msg;
}
void ksr_msg_env_reset(void)
{
	return;
}
int run_top_route(struct action *a, struct sip_msg *msg, struct run_act_ctx *c)
{
	(void)a;
	(void)msg;
	(void)c;
	return 0;
}
struct sr_kemi_eng *sr_kemi_eng_get(void)
{
	return NULL;
}
int sr_kemi_route(struct sr_kemi_eng *keng, struct sip_msg *msg, int rtype,
		str *ename, str *emod, str *efnc, sr_kemi_xval_t *xval)
{
	(void)keng;
	(void)msg;
	(void)rtype;
	(void)ename;
	(void)emod;
	(void)efnc;
	(void)xval;
	return -1;
}

/* 整数转字符串缓冲（src/core/ut.h:317，模块经 ut_buf_int2str 做无锁 itoa） */
#define STUB_INT2STR_MAX_LEN 32
char ut_buf_int2str[STUB_INT2STR_MAX_LEN];

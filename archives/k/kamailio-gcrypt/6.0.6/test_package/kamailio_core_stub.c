/* kamailio_core_stub.c — kamailio core 未定义符号的最小可解析层（测试专用）
 *
 * 符号清单来源：对**本次构建产物** gcrypt.so 执行 `llvm-nm -D --undefined-only`
 * （OHOS aarch64 交叉编译产物实测），共 49 个未定义符号，分三类：
 *
 *   (a) libc/CRT 提供（9）：__at_fini / __cxa_finalize / __register_frame_info /
 *       __deregister_frame_info / fprintf / malloc / free / memset / stderr
 *       —— **不在此桩内重复定义**（与 libc 冲突）。
 *   (b) libgcrypt.so.20 提供（17，符号带 GCRYPT_1.6 版本）：gcry_check_version /
 *       gcry_cipher_{open,close,setkey,setiv,encrypt,decrypt,get_algo_blklen,
 *       get_algo_keylen} / gcry_control / gcry_md_{open,close,write,read} /
 *       gcry_randomize / gcry_strerror / gcry_strsource
 *       —— 由 conan 依赖 libgcrypt/1.12.2 的 libgcrypt.so.20 在运行时解析。
 *   (c) kamailio core 提供（23）：本文件给出定义（gcrypt.so 是 core 插件，
 *       这些符号由 kamailio 主程序提供；OHOS/musl 加载器不做惰性绑定，
 *       独立 dlopen 时须全部可解析）。
 *
 * 类型口径严格对齐上游头文件，避免桩层与真实 ABI 错位：
 *   my_pid              — src/core/dprint.h:161  `int my_pid(void)`（函数，非变量）
 *   dprint_color        — src/core/dprint.h:217  `void dprint_color(int level)`（函数）
 *   log_level_info      — src/core/dprint.h:181  `struct log_level_info[]`（数组）
 *   log_prefix_val      — src/core/dprint.h:169  `str *`
 *   _km_log_func        — src/core/dprint.h:174  `void (*)(int, const char *, ...)`
 *
 * 日志路径说明：上游 LOG_FX 宏先判 `dprint_crit == 0` 且
 * `get_debug_level(LOG_MNAME, LOG_MNAME_LEN) >= level`；本桩 get_debug_level() 返回 0
 * 低于所有级别，故模块内 LM_* 全部不落日志。但桩层仍给出**可用的**日志函数指针
 * （指向 sink），以免将来出现日志路径时因空指针崩溃掩盖真实失败原因。
 * 仅 sr_kemi_modules_add() 在 e2e 路径上被真实调用（mod_register() 注册 KEMI 表），
 * 其语义与 src/core/kemi.c 一致（记录函数表指针并计数）。
 */
#include "kamailio_core_stub.h"

#include <stdarg.h>
#include <stdio.h>

int kamailio_stub_assertions = 0;

/* ---- 被真实调用的 core 符号：完整语义实现（记录 mod_register 的注册行为） ---- */
const sr_kemi_t *kamailio_stub_last_kemi_table = NULL;
int kamailio_stub_kemi_add_calls = 0;

int sr_kemi_modules_add(const sr_kemi_t *kt)
{
	kamailio_stub_kemi_add_calls++;
	kamailio_stub_last_kemi_table = kt;
	return 0;
}

/* ------------------------------------------------------------------
 * 其余 core 符号：仅需在 dlopen（RTLD_NOW）时全部可解析。
 * e2e 路径不调用它们（模块无构造器；mod_register 只用上面的函数），
 * 因此给出最小定义而非完整语义。
 * ------------------------------------------------------------------ */

/* 进程/调试状态（src/core/dprint.h、src/core/pt.h） */
int process_no = 0;
int dprint_crit = 0;
int log_color = 0;
int log_stderr = 0;

int my_pid(void)
{
	return 1;
}

/* 日志级别表（src/core/dprint.h:181）—— 索引口径 level - L_ALERT，
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
int log_prefix_mode = 0;
char *log_prefix_fmt = NULL;

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

typedef void (*kamailio_stub_km_log_f)(int, const char *, ...);
kamailio_stub_km_log_f _km_log_func = kamailio_stub_log_sink;
kamailio_stub_km_log_f _ksr_slog_func = kamailio_stub_log_sink;

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

/* 伪变量缓冲（src/core/pvapi.c） */
char *pv_get_buffer(void)
{
	return NULL;
}
int pv_get_buffer_size(void)
{
	return 0;
}
void *pv_cache_get(int type, void *name)
{
	(void)type;
	(void)name;
	return NULL;
}

/* SPVE 参数 fixup（src/core/mod_fix.c、src/core/route.c） */
int fixup_spve2_pvar(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}
int fixup_free_spve2_pvar(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}
int get_str_fparam(void *target, void *msg, void *fparam)
{
	(void)target;
	(void)msg;
	(void)fparam;
	return -1;
}

/* callid 注册（src/core/parser/parse_from.c 等，仅需可解析） */
int sr_register_callid_func(void *f)
{
	(void)f;
	return 0;
}

/* basex 字符表（core 内 base64url 辅助，仅需可解析；e2e 不调用） */
const char *_bx_b64_12[64];
const char *_bx_ub64[256];

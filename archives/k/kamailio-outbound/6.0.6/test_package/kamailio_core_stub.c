/*
 * kamailio core shim —— 消费者端到端用例的 core 符号层。
 *
 * 用途：outbound.so 是 kamailio 运行时 loadmodule 加载的模块，它自身不定义
 * kamailio core 符号（日志/配置/解析/分配器等一律在 core 里）。本文件为这些
 * 动态未定义符号提供最小可运行实现，使进程内 dlopen(outbound.so) 能完成
 * 加载与重定位，进而让用例真实驱动模块功能（见 test_outbound_e2e.c）。
 *
 * 与 kamailio 6.0.6 core 的对应（行号为核验位置）：
 *   _pkg_root / _shm_root  ← src/core/mem/pkg.h:34 / src/core/mem/shm.h:46
 *     结构体定义           ← src/core/mem/memapi.h:68 / :107
 *     （模块以 `_pkg_root.xmalloc(_pkg_root.mem_block, size)` 形态内联调用分配器，
 *       故必须提供同布局实例，并把 xmalloc/xfree 指向进程堆；mem_block 仅作不透明
 *       句柄，本用例传 NULL。）
 *   cfg_declare            ← src/core/cfg/cfg_ctx.c（模块 mod_init 声明配置组）
 *   flag_in_range          ← src/core/flags.h:44 `flag > MAX_FLAG ? 0 : 1`
 *   find_module_by_name    ← src/core/modules.c（module_loaded("stun") 底层的查找入口）
 *   my_pid / process_no / route_type / log_* ← core 运行期全局量
 *   isflagset / parse_* / check_self / free_params ← 模块其它分支用到的 core 入口，
 *     本用例不会走到（仅需重定位可解析），实现为最小语义。
 *
 * 说明：本文件是「测试替身」，不引入任何平台宏，也不改动被测模块。
 */
#include "kamailio_core_stub.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ── 记录器（用例据此断言模块真的走了对应路径）───────────────────────────── */
int stub_cfg_declare_calls = 0;
char stub_cfg_group[64] = {0};
void *stub_cfg_default_ptr = NULL;
void *stub_cfg_handle_ptr = NULL;
int stub_shm_alloc_calls = 0;
int stub_shm_free_calls = 0;
int stub_pkg_alloc_calls = 0;
int stub_pkg_free_calls = 0;
int stub_find_module_calls = 0;

/* ── 私有内存（pkg）分配器替身：进程堆 + 计数 ────────────────────────────── */
static void *stub_pkg_xmalloc(void *mbp, size_t size)
{
	(void)mbp;
	stub_pkg_alloc_calls++;
	return malloc(size);
}

static void stub_pkg_xfree(void *mbp, void *p)
{
	(void)mbp;
	if(p != NULL)
		stub_pkg_free_calls++;
	free(p);
}

static void *stub_pkg_xrealloc(void *mbp, void *p, size_t size)
{
	(void)mbp;
	return realloc(p, size);
}

/* 供用例释放由 pkg_malloc（= _pkg_root.xmalloc）分配的缓冲区，保持计数闭环。
 * 这里不引用 _pkg_root：替身分配器不依赖 mem_block（签名保留，置 NULL）。 */
void stub_pkg_free(void *p)
{
	stub_pkg_xfree(NULL, p);
}

/* ── 共享内存（shm）分配器替身：进程堆 + 计数 ────────────────────────────── */
static void *stub_shm_xmalloc(void *mbp, size_t size)
{
	(void)mbp;
	stub_shm_alloc_calls++;
	return malloc(size);
}

static void stub_shm_xfree(void *mbp, void *p)
{
	(void)mbp;
	if(p != NULL)
		stub_shm_free_calls++;
	free(p);
}

static void *stub_shm_xrealloc(void *mbp, void *p, size_t size)
{
	(void)mbp;
	return realloc(p, size);
}

/* ── 同布局根实例 ──
 * 字段顺序照 src/core/mem/memapi.h:68（sr_pkg_api_t）与 :107（sr_shm_api_t），
 * 仅 mem_block/xmalloc/xfree 等被模块真正按偏移访问；其余字段以同宽度指针占位
 * （真实类型为函数指针 typedef，见 memapi.h:43-65），保证偏移与 core 一致。 */
typedef struct stub_pkg_api_ {
	char *mname;
	char *mem_pool;
	void *mem_block;
	void *xmalloc;
	void *xmallocxz;
	void *xrealloc;
	void *xreallocxf;
	void *xfree;
	void *xstatus;
	void *xstatus_filter;
	void *xinfo;
	void *xreport;
	void *xavailable;
	void *xsums;
	void *xdestroy;
	void *xmodstats;
	void *xfmodstats;
} stub_pkg_api_t;

typedef struct stub_shm_api_ {
	char *mname;
	void *mem_pool;
	void *mem_block;
	void *xmalloc;
	void *xmallocxz;
	void *xmalloc_unsafe;
	void *xrealloc;
	void *xreallocxf;
	void *xresize;
	void *xfree;
	void *xfree_unsafe;
	void *xstatus;
	void *xstatus_filter;
	void *xinfo;
	void *xreport;
	void *xavailable;
	void *xsums;
	void *xdestroy;
	void *xmodstats;
	void *xfmodstats;
	void *xglock;
	void *xgunlock;
	void *xsetfunc;
} stub_shm_api_t;

stub_pkg_api_t _pkg_root;
stub_shm_api_t _shm_root;

/* 符号层初始化：必须在 dlopen 之前调用（模块 mod_init 即会走 shm_malloc）。 */
void stub_init(void)
{
	memset(&_pkg_root, 0, sizeof(_pkg_root));
	memset(&_shm_root, 0, sizeof(_shm_root));
	_pkg_root.mname = (char *)"shim-pkg";
	_pkg_root.mem_block = NULL; /* 不透明句柄：替身不使用 */
	_pkg_root.xmalloc = (void *)stub_pkg_xmalloc;
	_pkg_root.xrealloc = (void *)stub_pkg_xrealloc;
	_pkg_root.xfree = (void *)stub_pkg_xfree;
	_shm_root.mname = (char *)"shim-shm";
	_shm_root.mem_block = NULL;
	_shm_root.xmalloc = (void *)stub_shm_xmalloc;
	_shm_root.xrealloc = (void *)stub_shm_xrealloc;
	_shm_root.xfree = (void *)stub_shm_xfree;
}

/* ── base64 8K 查找表（core 侧由 basex.c 的 init_basex() 填充，见 basex.c:178-189）──
 * 模块的 base64_enc/base64_dec 是 basex.h 的内联实现，运行时按下标访问这两张表；
 * 本替身按同一公式填充：
 *   小端 _bx_b64_12[r] = b64_enc_char(r >> 6) | (b64_enc_char(r & 0x3f) << 8)
 *   _bx_ub64[r] = b64_dec_char(r)                    （basex.c:179-189） */
unsigned short _bx_b64_12[4096];
unsigned char _bx_ub64[256];

/* 字母表与 core 的 b64_enc_char/b64_dec_char 一致（basex.h，RFC 4648 标准表；
 * 非法字符解码为 0xff，与 core 相同）。 */
static unsigned char stub_b64_enc_char(unsigned char r)
{
	static const char alpha[] =
			"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

	return (unsigned char)alpha[r & 0x3f];
}

static unsigned char stub_b64_dec_char(unsigned char c)
{
	if(c >= 'A' && c <= 'Z')
		return (unsigned char)(c - 'A');
	if(c >= 'a' && c <= 'z')
		return (unsigned char)(c - 'a' + 26);
	if(c >= '0' && c <= '9')
		return (unsigned char)(c - '0' + 52);
	if(c == '+')
		return 62;
	if(c == '/')
		return 63;
	return 0xff;
}

void stub_init_basex(void)
{
	int r;

	for(r = 0; r < 4096; r++)
		_bx_b64_12[r] =
				(unsigned short)(stub_b64_enc_char((unsigned char)(r >> 6))
								| (stub_b64_enc_char((unsigned char)(r & 0x3f)) << 8));
	for(r = 0; r < 256; r++)
		_bx_ub64[r] = stub_b64_dec_char((unsigned char)r);
}

/* ── core 运行期全局量（dprint.h 侧同名符号）──
 * 用例把 get_debug_level() 压到 L_ALERT 之下，模块日志路径整体短路，故这些量只
 * 承担「可解析 + 类型足够安全」的职责，不参与日志语义。 */
typedef struct stub_str_ {
	char *s;
	int len;
} stub_str_t;

/* core dprint.h:181 `struct log_level_info`：模块经 LOG_LEVEL2NAME /
 * LOG2SYSLOG_LEVEL 访问 .name 与 .syslog_level，故按同偏移给出该结构。 */
struct log_level_info {
	char *name;
	int syslog_level;
};

int process_no = 0;
int log_stderr = 0;
int log_color = 0;
struct log_level_info log_level_info[32];
volatile int dprint_crit = 0;
stub_str_t *log_prefix_val = NULL; /* dprint.h:169 `extern str *log_prefix_val;` */

/* ── 日志函数指针（core 侧是变量而非函数：dprint.h:155 `_ksr_slog_func`、
 * dprint.h:175 `_km_log_func`）—— 置为安全空实现，保证宏内 `if(_ksr_slog_func)`
 * 之类判空成立且调用不落地。 */
typedef void (*stub_km_log_f)(int level, const char *fmt, ...);
typedef void (*stub_ksr_slog_f)(void *ld, const char *fmt, ...);

static void stub_km_log(int level, const char *fmt, ...)
{
	(void)level;
	(void)fmt;
}

static void stub_ksr_slog(void *ld, const char *fmt, ...)
{
	(void)ld;
	(void)fmt;
}

stub_km_log_f _km_log_func = stub_km_log;
stub_ksr_slog_f _ksr_slog_func = stub_ksr_slog;

/* ── core 入口替身 ── */
int my_pid(void)
{
	return 1;
}

/* dprint.h:188/190：签名带模块名（mname/mnlen）；返回低于 L_ALERT 的等级，使
 * 模块所有 LM_* 日志短路，用例只观察功能行为。 */
int get_debug_level(char *mname, int mnlen)
{
	(void)mname;
	(void)mnlen;
	return -2;
}

int get_debug_facility(char *mname, int mnlen)
{
	(void)mname;
	(void)mnlen;
	return 0;
}

void dprint_color(int level)
{
	(void)level;
}

void dprint_color_reset(void)
{
}

/* flags.h:53 `MAX_FLAG = sizeof(flag_t)*CHAR_BIT - 1`（flag_t = unsigned int → 31），
 * flags.c 语义：超出合法区间的 flag 返回 0。 */
int flag_in_range(unsigned int flag)
{
	return (flag > (unsigned int)(sizeof(unsigned int) * 8 - 1)) ? 0 : 1;
}

/* module_loaded("stun") 的底层入口（core/modules.c）：用例进程中无模块注册表，
 * 返回 NULL 即「未加载 stun」，模块按设计继续初始化。 */
void *find_module_by_name(char *name)
{
	(void)name;
	stub_find_module_calls++;
	return NULL;
}

/* cfg_declare（core/cfg/cfg.h:75）——模块 mod_init 用它声明 outbound 配置组。
 * 替身按 core 语义：按 def_size 分配配置实例、拷入模块声明的默认值，并把实例
 * 指针回填 *handle（模块后续 cfg_get 读到的是真实默认值，而不是野指针）。 */
int cfg_declare(char *group_name, void *def, void *values, int def_size, void **handle)
{
	void *inst;

	(void)def;
	stub_cfg_declare_calls++;
	if(group_name != NULL) {
		size_t n = strlen(group_name);
		if(n >= sizeof(stub_cfg_group))
			n = sizeof(stub_cfg_group) - 1;
		memcpy(stub_cfg_group, group_name, n);
		stub_cfg_group[n] = '\0';
	}
	stub_cfg_default_ptr = values;
	inst = calloc(1, (size_t)(def_size > 0 ? def_size : 1));
	if(inst != NULL && values != NULL && def_size > 0)
		memcpy(inst, values, (size_t)def_size);
	stub_cfg_handle_ptr = inst;
	if(handle != NULL)
		*handle = inst;
	return 0;
}

/* 以下 core 入口本用例不会走到（outbound 的 REGISTER 路径），仅为重定位可解析
 * 而存在：签名用 (void*, ...) 形式，保证任何调用形态下 ABI 都不越界。 */
int isflagset(void *msg, ...)
{
	(void)msg;
	return 0;
}

int check_self(void *host, ...)
{
	(void)host;
	return 0;
}

int parse_contact(void *msg, ...)
{
	(void)msg;
	return -1;
}

int parse_headers(void *msg, ...)
{
	(void)msg;
	return -1;
}

int parse_params(void *msg, ...)
{
	(void)msg;
	return -1;
}

int parse_rr(void *msg, ...)
{
	(void)msg;
	return -1;
}

int parse_supported(void *msg, ...)
{
	(void)msg;
	return -1;
}

int parse_uri(void *msg, ...)
{
	(void)msg;
	return -1;
}

void free_params(void *p, ...)
{
	(void)p;
}

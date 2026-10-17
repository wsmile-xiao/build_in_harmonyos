/*
 * kamailio core 符号 shim —— 仅供 test_package 的 rule12 端到端消费者用例使用。
 *
 * 背景：lrkproxy.so 是 kamailio 的 **core 插件**，它把 core 提供的 API 与全局量
 * 当作「未定义符号」引用（SIP 消息解析、dprint 日志机制、_pkg_root/_shm_root、
 * pkg/shm 内存分配器等）。真实部署时这些符号由 kamailio 主程序导出
 * （-Wl,--export-dynamic）。
 *
 * OHOS 使用 musl libc，其动态链接器不做惰性绑定：dlopen(RTLD_LAZY) 等价于
 * RTLD_NOW，库内所有未定义符号必须在加载时解析完。因此独立加载该模块时，消费者
 * 进程必须提供这些符号 —— 本文件即该最小符号层。它与 test_lrkproxy_e2e.c 链接成
 * 同一个测试可执行文件，并依靠 -Wl,--export-dynamic 把符号导出到动态符号表。
 *
 * 取舍原则（与 kamailio-unixodbc e2e 的 core-stub 同一方法论）：
 *   - 本用例真实调用路径上的符号给真实/语义实现（pkg/shm 分配器、参数存储）；
 *   - 其余仅需可解析的符号给最小实现（空函数 / 返回安全值）；
 *   - core 全局量给零值存储（ELF 解析只看符号名）。
 */
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lrkproxy_core_stub.h"

/* ─────── 1) 真实语义实现：pkg/shm 分配器 API 表（本用例真实调用） ───────
 * 模块内 pkg_malloc/shm_malloc 是宏（src/core/mem/pkg.h:60）：
 *   pkg_malloc(s) = _pkg_root.xmalloc(_pkg_root.mem_block, s)
 * 即模块只解引用 _pkg_root/_shm_root 两个结构体（sr_pkg_api_t/sr_shm_api_t），
 * 经其中的函数指针分配内存。stub 必须填充**完整的函数指针表**（malloc/calloc
 * 语义实现），使参数写入与 set-list 初始化真实发生。
 * 字段布局与 src/core/mem/memapi.h 的 sr_pkg_api_t/sr_shm_api_t 逐字段对齐。 */
typedef void *(*sr_malloc_f)(void *mbp, size_t size);
typedef void (*sr_free_f)(void *mbp, void *p);
typedef void *(*sr_realloc_f)(void *mbp, void *p, size_t size);
typedef void (*sr_mem_status_f)(void *mbp);
typedef void (*sr_mem_sums_f)(void *mbp);
typedef void (*sr_mem_destroy_f)(void);

static void *stub_malloc(void *mbp, size_t size) { (void)mbp; return malloc(size); }
static void *stub_mallocz(void *mbp, size_t size) { (void)mbp; return calloc(1, size); }
static void *stub_realloc(void *mbp, void *p, size_t size) { (void)mbp; return realloc(p, size); }
static void *stub_reallocxf(void *mbp, void *p, size_t size) { (void)mbp; (void)p; return malloc(size); }
static void stub_free(void *mbp, void *p) { (void)mbp; free(p); }
static void stub_mem_status(void *mbp) { (void)mbp; }
static void stub_mem_sums(void *mbp) { (void)mbp; }
static void stub_mem_destroy(void) { }

typedef struct {
	char *mname;
	char *mem_pool;
	void *mem_block;
	sr_malloc_f xmalloc;
	sr_malloc_f xmallocxz;
	sr_realloc_f xrealloc;
	sr_realloc_f xreallocxf;
	sr_free_f xfree;
	sr_mem_status_f xstatus;
	sr_mem_status_f xstatus_filter;
	void *xinfo;
	void *xreport;
	unsigned long (*xavailable)(void *mbp);
	sr_mem_sums_f xsums;
	sr_mem_destroy_f xdestroy;
	void *xmodstats;
	void *xfmodstats;
} sr_pkg_api_stub_t;

typedef struct {
	char *mname;
	void *mem_pool;
	void *mem_block;
	sr_malloc_f xmalloc;        /* memory chunk allocation */
	sr_malloc_f xmallocxz;      /* allocation with 0 filling */
	sr_malloc_f xmalloc_unsafe; /* allocation without locking shm */
	sr_realloc_f xrealloc;      /* reallocation */
	sr_realloc_f xreallocxf;    /* realloc with always free of old buffer */
	sr_realloc_f xresize;       /* resizing - free+malloc in same locking */
	sr_free_f xfree;            /* memory chunk free */
	sr_free_f xfree_unsafe;     /* free without locking shm */
	sr_mem_status_f xstatus;
	sr_mem_status_f xstatus_filter;
	void *xinfo;
	void *xreport;
	unsigned long (*xavailable)(void *mbp);
	sr_mem_sums_f xsums;
	sr_mem_destroy_f xdestroy;
	void *xmodstats;
	void *xfmodstats;
	void *xglock;   /* sr_shm_glock_f: memory managing global lock */
	void *xgunlock; /* sr_shm_gunlock_f */
	void *xsetfunc; /* sr_setfunc_f: chunk set func pointer */
} sr_shm_api_stub_t;

static sr_pkg_api_stub_t pkg_api = {
	"stub-pkg", 0, 0,
	stub_malloc, stub_mallocz, stub_realloc, stub_reallocxf, stub_free,
	stub_mem_status, stub_mem_status, 0, 0, 0, stub_mem_sums,
	stub_mem_destroy, 0, 0,
};

/* 字段序与 src/core/mem/memapi.h 的 sr_shm_api_t 逐字段对齐 */
static sr_shm_api_stub_t shm_api = {
	"stub-shm", 0, 0,
	stub_malloc, stub_mallocz, stub_malloc, stub_realloc, stub_reallocxf,
	stub_reallocxf, stub_free, stub_free,
	stub_mem_status, stub_mem_status, 0, 0, 0, stub_mem_sums,
	stub_mem_destroy, 0, 0,
	0, 0, 0,
};

sr_pkg_api_stub_t _pkg_root;
sr_shm_api_stub_t _shm_root;

__attribute__((constructor)) static void stub_mem_init(void)
{
	_pkg_root = pkg_api;
	_shm_root = shm_api;
}

/* ─────── 2) SIP 消息解析层（本用例调用路径不触达，仅需可解析） ───────
 * 这些函数操作 kamailio 的 sip_msg 结构树；e2e 不构造 SIP 消息，模块的
 * lrkproxy_manage 系列命令在没有 set/节点时直接返回 -2（无可用代理节点），
 * 不会下探到解析层。给返回失败值的最小实现。 */
int parse_headers(void) { return -1; }
int parse_from_header(void) { return -1; }
int parse_to_header(void) { return -1; }
int parse_contact(void) { return -1; }
int parse_uri(void) { return -1; }
int parse_sdp(void) { return -1; }
int parse_via_header(void) { return -1; }
int get_body(void) { return -1; }
int get_sdp_stream(void) { return -1; }
int get_sdp_session(void) { return -1; }
int get_sdp_hdr_field(void) { return -1; }
int get_mixed_part_delimiter(void) { return -1; }
int find_sdp_line_delimiter(void) { return -1; }
int find_next_sdp_line_delimiter(void) { return -1; }
int decode_mime_type(void) { return -1; }
char *eat_line(char *buffer, unsigned int len) { (void)buffer; (void)len; return buffer; }
char *ip_addr2a(void *ip) { (void)ip; return ""; }
int insert_new_lump_after(void) { return -1; }
int del_lump(void) { return -1; }

/* ─────── 2b) 杂项 core 助手（探针逐个暴露，逐个补齐） ─────── */
unsigned int fastrand(void) { return 0; }
ticks_t get_ticks(void) { return 0; }
char *ut_buf_int2str(char *buf, int len, int val) { (void)buf; (void)len; (void)val; return 0; }

/* ─────── 3) fixup 框架（模块命令的参数修正回调，e2e 不调用） ─────── */
int fixup_spve_null(void) { return 0; }
int fixup_spve_spve(void) { return 0; }
int fixup_free_spve_null(void) { return 0; }
int fixup_free_spve_spve(void) { return 0; }

/* ─────── 4) 伪变量（PV）框架（模块未导出 PV，仅链接期需要符号） ─────── */
void *pv_cache_get(void) { return 0; }
int pv_parse_spec2(void) { return -1; }
int pv_get_spec_value(void) { return -1; }
int pv_locate_name(void) { return -1; }
int get_str_fparam(void) { return -1; }
int find_export(void) { return 0; }

/* ─────── 5) core 日志机制（本用例不下探，直接抑制） ───────
 * get_debug_level 返回 -1：模块内 LM_* 宏的阈值检查不通过，日志全部短路。 */
int get_debug_level(void) { return -1; }
int get_debug_facility(void) { return 0; }
void _km_log_func(int level, const char *fmt, ...) { (void)level; (void)fmt; }
void _ksr_slog_func(int level, const char *fmt, ...) { (void)level; (void)fmt; }
void dprint_crit(void *log_info, const char *fmt, ...) { (void)log_info; (void)fmt; }
char log_color[8];
char dprint_color[64];
char dprint_color_reset[16];
char log_level_info[256];
char log_prefix_val[128];
char log_stderr[8];

/* ─────── 6) 其余 core 全局量：零值存储（可读可写，本用例不依赖其值） ─────── */
char my_pid[16];     /* core: pid_t my_pid */
char process_no[8];  /* core: int process_no */

int route_type = 0;
int dont_fork = 0;

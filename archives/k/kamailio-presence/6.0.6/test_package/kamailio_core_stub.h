/* kamailio_core_stub.h — kamailio core 类型/符号最小层（测试专用）
 *
 * 用途：OHOS/musl 的加载器不做惰性绑定（dlopen 等价 RTLD_NOW），core 插件模块
 * （18 个 presence 模块引用 sr_kemi_modules_add / dprint / fixup_* 等 core 符号）独立
 * dlopen 时**全部**未定义符号都必须可解析。故端到端消费者用例把本桩层 +
 * gen_core_stub.py 自动生成的补充桩一起编译进测试可执行文件，并以
 * -Wl,--export-dynamic 导出符号供 dlopen 解析。
 *
 * 类型布局逐字段对齐上游头文件（E-sink 教训：桩层类型错位会导致日志路径解引用
 * 野指针 SIGSEGV，掩盖真实失败原因）：
 *   str                  — src/core/str.h
 *   sr_kemi_t            — src/core/kemi.h（ptypes[SR_KEMI_PARAMS_MAX=6]）
 *   sr_kemi_xval_t       — src/core/kemi.h
 *   cmd_export_t         — src/core/sr_module.h:206-216
 *   param_export_t       — src/core/sr_module.h:234-239
 *   module_exports 前缀  — src/core/sr_module.h:288-310（name/dlflags/cmds/params）
 */
#ifndef KAMAILIO_CORE_STUB_H
#define KAMAILIO_CORE_STUB_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define KAMAILIO_STUB_VERSION "1.0"

/* ---- 基础类型（布局对齐上游头文件） ---- */
typedef struct _str
{
	char *s;
	int len;
} str;

/* KEMI 参数/返回类型（src/core/kemi.h 常量原值） */
#define SR_KEMIP_NONE (0)
#define SR_KEMIP_INT (1 << 0)
#define SR_KEMIP_STR (1 << 1)
#define SR_KEMIP_BOOL (1 << 2)
#define SR_KEMIP_LONG (1 << 3)
#define SR_KEMIP_XVAL (1 << 4)
#define SR_KEMIP_NULL (1 << 5)

#define SR_KEMI_PARAMS_MAX 6

typedef struct sr_kemi_xval
{
	int vtype;
	union
	{
		int n;
		long l;
		str s;
		void *dict;
	} v;
} sr_kemi_xval_t;

typedef struct sr_kemi
{
	str mname;                      /* 子模块名 */
	str fname;                      /* 函数名（KSR.<mname>.<fname>） */
	int rtype;                      /* 返回类型 */
	void *func;                     /* C 函数指针 */
	int ptypes[SR_KEMI_PARAMS_MAX]; /* 参数类型 */
} sr_kemi_t;

/* ---- 模块导出结构（src/core/sr_module.h，逐字段镜像） ---- */
typedef int (*kam_cmd_function)(void *msg, char *p1, char *p2);
typedef int (*kam_fixup_function)(void **param, int param_no);
typedef int (*kam_free_fixup_function)(void **param, int param_no);
typedef unsigned int kam_modparam_t;

typedef struct kam_cmd_export
{
	char *name;
	kam_cmd_function function;
	int param_no;
	kam_fixup_function fixup;
	kam_free_fixup_function free_fixup;
	unsigned int flags;
} kam_cmd_export_t;

typedef struct kam_param_export
{
	char *name;
	kam_modparam_t type;
	void *param_pointer;
} kam_param_export_t;

/* module_exports 前四字段（e2e 只消费到 params；后继字段用占位对齐总长度，
 * 避免误读后即用——镜像自上游同名结构） */
typedef struct kam_module_exports
{
	char *name;
	unsigned int dlflags;
	kam_cmd_export_t *cmds;
	kam_param_export_t *params;
	void *rpc_methods;
	void *pv_items;
	void *response_f;
	void *init_mod_f;
	void *init_child_f;
	void *destroy_mod_f;
} kam_module_exports_t;

/* KEMI/cfg 表以全零项结尾（上游写法定式） */
static inline int kamailio_stub_cmd_is_end(const kam_cmd_export_t *e)
{
	return e->name == NULL;
}
static inline int kamailio_stub_param_is_end(const kam_param_export_t *e)
{
	return e->name == NULL;
}
static inline int kamailio_stub_kemi_is_end(const sr_kemi_t *e)
{
	return e->mname.s == NULL && e->fname.s == NULL && e->rtype == 0 && e->func == NULL;
}

/* ---- 由桩层记录 mod_register() 注册进来的 KEMI 函数表，供 e2e 断言 ---- */
extern const sr_kemi_t *kamailio_stub_last_kemi_table;
extern int kamailio_stub_kemi_add_calls;
/* 每次 mod_register 采集：调用次数 + 最近一次的表条目数 + 首项子模块名
 * （按模块逐个 dlopen 并复位采集状态，故为 1:1） */
extern int kamailio_stub_last_kemi_table_count;
extern char kamailio_stub_last_kemi_mname[64];

/* ---- e2e 与桩层共用的断言计数工具 ---- */
extern int kamailio_stub_assertions;

#define KAM_STUB_CHECK(cond, fmt, ...)                                          \
	do                                                                          \
	{                                                                           \
		kamailio_stub_assertions++;                                             \
		if (!(cond))                                                            \
		{                                                                       \
			fprintf(stderr, "ASSERT FAILED [%d]: " fmt "\n",                    \
					kamailio_stub_assertions, ##__VA_ARGS__);                   \
			return 1;                                                           \
		}                                                                       \
	} while (0)

/* 阶段进度标记：崩溃定位用（失败时 stderr 上能看出死在哪个阶段） */
#define KAM_STUB_STEP(fmt, ...)                                                 \
	do                                                                          \
	{                                                                           \
		fprintf(stderr, "  ... " fmt "\n", ##__VA_ARGS__);                      \
		fflush(stderr);                                                         \
	} while (0)

/* 内存：模块真实代码经 `_shm_root` 函数表分配（memapi.h），故测试
 * 进程必须提供 `_shm_root`/`_pkg_root` 两个全局对象——否则通用桩的全零占位会让
 * 函数指针为 NULL，模块内首次分配即 SIGSEGV（实测：spi_add 内 blr x8，x8=[_shm_root+24]）。
 *
 * 布局逐字段镜像上游 src/core/mem/memapi.h（shm 与 pkg 字段顺序不同）；
 * 被测模块以 DBG_SR_MEMORY 构建（6 参调试变体：file/func/line/mname），故取 6 参签名——
 * 对非 DBG 构建同样安全（前导参数一致，调试参数不读取）。 */
typedef void *(*kam_shm_malloc_f)(void *mbp, size_t size, const char *file,
		const char *func, unsigned int line, const char *mname);
typedef void *(*kam_shm_realloc_f)(void *mbp, void *p, size_t size,
		const char *file, const char *func, unsigned int line, const char *mname);
typedef void (*kam_shm_free_f)(void *mbp, void *p, const char *file,
		const char *func, unsigned int line, const char *mname);

typedef struct kam_shm_api
{
	char *mname;
	void *mem_pool;
	void *mem_block;
	kam_shm_malloc_f xmalloc;
	kam_shm_malloc_f xmallocxz;
	kam_shm_malloc_f xmalloc_unsafe;
	kam_shm_realloc_f xrealloc;
	kam_shm_realloc_f xreallocxf;
	kam_shm_realloc_f xresize;
	kam_shm_free_f xfree;
	kam_shm_free_f xfree_unsafe;
	/* 以下字段被测路径不触发，占位对齐结构总长度 */
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
} kam_shm_api_t;

typedef struct kam_pkg_api
{
	char *mname;
	char *mem_pool;
	void *mem_block;
	kam_shm_malloc_f xmalloc;
	kam_shm_malloc_f xmallocxz;
	kam_shm_realloc_f xrealloc;
	kam_shm_realloc_f xreallocxf;
	kam_shm_free_f xfree;
	void *xstatus;
	void *xstatus_filter;
	void *xinfo;
	void *xreport;
	void *xavailable;
	void *xsums;
	void *xdestroy;
	void *xmodstats;
	void *xfmodstats;
} kam_pkg_api_t;

extern kam_shm_api_t _shm_root;
extern kam_pkg_api_t _pkg_root;

/* 兼容旧式直接调用（部分模块可能直接引用 shm_malloc 符号而非宏）：同一后端，同计数 */
void *shm_malloc(size_t size);
void shm_free(void *ptr);
void *shm_realloc(void *ptr, size_t size);
extern long kamailio_stub_shm_alloc_calls;
extern long kamailio_stub_shm_free_calls;

#endif /* KAMAILIO_CORE_STUB_H */

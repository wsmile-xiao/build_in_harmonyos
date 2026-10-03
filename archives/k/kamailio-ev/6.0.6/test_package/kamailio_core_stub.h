/* kamailio_core_stub.h — 最小 kamailio core 符号/类型层（测试专用）
 *
 * 用途：OHOS/musl 的加载器不做惰性绑定（dlopen 等价 RTLD_NOW），core 插件模块
 * （evapi.so 引用 sr_kemi_modules_add / route_lookup / dprint 等 core 符号）独立
 * dlopen 时**全部**未定义符号都必须可解析。故端到端消费者用例把本桩层一并编译进
 * 测试可执行文件，并以 -Wl,--export-dynamic 导出符号供 dlopen 解析。
 *
 * 类型布局与上游一致（src/core/str.h、src/core/kemi.h、src/core/route.h、src/core/pvar.h 6.0.6）：
 *   str            — src/core/str.h
 *   sr_kemi_t      — src/core/kemi.h（ptypes[SR_KEMI_PARAMS_MAX=6]）
 *   sr_kemi_xval_t — src/core/kemi.h
 *   route_list     — src/core/route.h
 *   pv_export_t    — src/core/pvar.h（str name; pv_type_t type; getf; setf; parse_name; parse_index; init_param; int iparam）
 */
#ifndef KAMAILIO_CORE_STUB_H
#define KAMAILIO_CORE_STUB_H

#include <stddef.h>
#include <stdio.h>

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
	str mname;                      /* 子模块名，evapi 全部为 "evapi" */
	str fname;                      /* 函数名（KSR.evapi.<fname>） */
	int rtype;                      /* 返回类型 */
	void *func;                     /* C 函数指针 */
	int ptypes[SR_KEMI_PARAMS_MAX]; /* 参数类型 */
} sr_kemi_t;

/* KEMI 函数表以全零项结尾（上游写法定式） */
static inline int kamailio_stub_is_table_end(const sr_kemi_t *e)
{
	return e->mname.s == NULL && e->fname.s == NULL && e->rtype == 0 && e->func == NULL;
}

/* ---- route_list（src/core/route.h:87-93），event_rt 的类型 ---- */
struct str_hash_entry;
struct str_hash_table
{
	struct str_hash_entry **table;
	int size;
	struct str_hash_entry *first;
	int num_elems;
};

struct route_list
{
	struct action **rlist;
	int idx;					 /* first empty entry */
	int entries;				 /* total number of entries */
	struct str_hash_table names; /* name to route index mappings */
};

/* ---- pv_export_t（src/core/pvar.h，mod_pvs 表元素类型） ---- */
typedef struct _pv_export
{
	str name;		  /*!< class name of PV */
	int type;		  /*!< pv_type_t，evapi 为 PVT_OTHER */
	void *getf;
	void *setf;
	void *parse_name;
	void *parse_index;
	void *init_param;
	int iparam;
} pv_export_t;

/* PVT_OTHER = 22（src/core/pvar.h:80-103 枚举顺序） */
#define STUB_PVT_OTHER 22

/* ---- 由桩层记录的行为，供 e2e 断言 ---- */
extern const sr_kemi_t *kamailio_stub_last_kemi_table;
extern int kamailio_stub_kemi_add_calls;

/* route_lookup(&event_rt, name) 调用记录：evapi_init_environment() 会按名解析三个事件路由 */
#define STUB_MAX_ROUTES 8
extern int kamailio_stub_route_lookup_calls;
extern char kamailio_stub_route_names[STUB_MAX_ROUTES][64];
extern void *kamailio_stub_route_rts_arg; /* 首次调用传入的 route_list 指针 */

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

#endif /* KAMAILIO_CORE_STUB_H */

/* kamailio_core_stub.h — 最小 kamailio core 符号/类型层（测试专用）
 *
 * 用途：OHOS/musl 的加载器不做惰性绑定（dlopen 等价 RTLD_NOW），core 插件模块
 * （gcrypt.so 引用 sr_kemi_modules_add / fixup_spve2_pvar / dprint 等 core 符号）
 * 独立 dlopen 时**全部**未定义符号都必须可解析。故端到端消费者用例把本桩层一并编译
 * 进测试可执行文件，并以 -Wl,--export-dynamic 导出符号供 dlopen 解析。
 *
 * 类型布局与上游一致（src/core/str.h、src/core/kemi.h 6.0.6）：
 *   str            — src/core/str.h
 *   sr_kemi_t      — src/core/kemi.h（ptypes[SR_KEMI_PARAMS_MAX=6]）
 *   sr_kemi_xval_t — src/core/kemi.h
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
	str mname;                      /* 子模块名，gcrypt 全部为 "gcrypt" */
	str fname;                      /* 函数名（KSR.gcrypt.<fname>） */
	int rtype;                      /* 返回类型 */
	void *func;                     /* C 函数指针 */
	int ptypes[SR_KEMI_PARAMS_MAX]; /* 参数类型 */
} sr_kemi_t;

/* KEMI 函数表以全零项结尾（上游写法定式） */
static inline int kamailio_stub_is_table_end(const sr_kemi_t *e)
{
	return e->mname.s == NULL && e->fname.s == NULL && e->rtype == 0 && e->func == NULL;
}

/* ---- 由桩层记录 mod_register() 注册进来的 KEMI 函数表，供 e2e 断言 ---- */
extern const sr_kemi_t *kamailio_stub_last_kemi_table;
extern int kamailio_stub_kemi_add_calls;

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

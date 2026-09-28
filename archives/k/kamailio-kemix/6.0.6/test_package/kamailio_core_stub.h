/* kamailio_core_stub.h — 最小 kamailio core 符号/类型层（测试专用）
 *
 * 用途：OHOS/musl 的加载器不做惰性绑定（dlopen 等价 RTLD_NOW），core 插件模块
 * （kemix.so 引用 get_debug_level / sr_kemi_xval_null / SIP 解析器等 core 符号）
 * 独立 dlopen 时**全部**未定义符号都必须可解析。故端到端消费者用例把本桩层一并编译
 * 进测试可执行文件，并以 -Wl,--export-dynamic 导出符号供 dlopen 解析。
 *
 * 类型布局与上游一致：
 *   str            — src/core/str.h
 *   sr_kemi_t      — src/core/kemi.h（6.0.6，ptypes[SR_KEMI_PARAMS_MAX=6]）
 *   sr_kemi_xval_t — src/core/kemi.h
 */
#ifndef KAMAILIO_CORE_STUB_H
#define KAMAILIO_CORE_STUB_H

#include <stddef.h>

/* ---- 基础类型（布局对齐上游头文件） ---- */
typedef struct _str
{
	char *s;
	int len;
} str;

/* KEMI 返回/参数类型（src/core/kemi.h 常量原值） */
#define SR_KEMIP_NONE (0)
#define SR_KEMIP_INT (1 << 0)
#define SR_KEMIP_STR (1 << 1)
#define SR_KEMIP_BOOL (1 << 2)
#define SR_KEMIP_LONG (1 << 3)
#define SR_KEMIP_XVAL (1 << 4)
#define SR_KEMIP_NULL (1 << 5)

#define SR_KEMI_PARAMS_MAX 6

/* sr_kemi_xval_null() 的 rmode（src/core/kemi.h） */
#define SR_KEMI_XVAL_NULL_NONE 0
#define SR_KEMI_XVAL_NULL_PRINT 1
#define SR_KEMI_XVAL_NULL_EMPTY 2
#define SR_KEMI_XVAL_NULL_ZERO 3

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
	str mname;                     /* 子模块名，kemix 全部为 "kx" */
	str fname;                     /* 函数名（KSR.kx.<fname>） */
	int rtype;                     /* 返回类型 */
	void *func;                    /* C 函数指针 */
	int ptypes[SR_KEMI_PARAMS_MAX];/* 参数类型 */
} sr_kemi_t;

/* KEMI 函数表以全零项结尾（上游写法定式） */
static inline int kamailio_stub_is_table_end(const sr_kemi_t *e)
{
	return e->mname.s == NULL && e->fname.s == NULL && e->rtype == 0 && e->func == NULL;
}

/* ---- 由桩层记录 mod_register() 注册进来的 KEMI 函数表，供 e2e 断言 ---- */
extern const sr_kemi_t *kamailio_stub_last_kemi_table;
extern int kamailio_stub_kemi_add_calls;

/* ---- e2e 与桩层共用的计数工具 ---- */
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

/* 断言计数器与所需标准库头（供 e2e 使用） */
#include <stdio.h>
extern int kamailio_stub_assertions;

#endif /* KAMAILIO_CORE_STUB_H */

/* kamailio_core_stub.c — kamailio core 符号的**真实语义**子集（测试专用）
 *
 * 只实现「e2e 实际执行到的路径」所需的 core 语义，其余 core 符号由
 * gen_core_stub.py 在测试时按被测 .so 的未定义符号面自动生成弱桩补齐
 * （弱定义 vs 本文件强定义：强定义胜出，二者可共存不冲突）。
 *
 * 真实语义项（被调用则必须正确，否则用例失败无意义）：
 *   - sr_kemi_modules_add : 记录 KEMI 表指针 + 条目数（e2e 断言 18 模块的
 *                           mod_register 注册行为 + 表结构）
 *   - shm_malloc/free/realloc : 模块真实代码行为用例的内存后端
 *   - _km_log_func / log_level_info / my_pid / dprint* : 日志路径（等级全 0 →
 *                           静默，故不污染测试输出，也不会因 NULL 指针崩溃）
 */

#include "kamailio_core_stub.h"

#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* ---- e2e 断言/观测出口 ---- */
const sr_kemi_t *kamailio_stub_last_kemi_table = NULL;
int kamailio_stub_kemi_add_calls = 0;
int kamailio_stub_last_kemi_table_count = -1;
char kamailio_stub_last_kemi_mname[64] = {0};
int kamailio_stub_assertions = 0;

/* ---- 共享内存（模块真实代码依赖；以 malloc 实现真实语义） ----
 *
 * kamailio 6.x 的分配入口是**函数表全局**：core/mem/shm.h 把 shm_malloc 定义为
 * `_shm_root.xmalloc(_shm_root.mem_block, ...)`，模块自身不含分配器实现。
 * 故此处提供 `_shm_root`/`_pkg_root` 两个对象（布局见 kamailio_core_stub.h），
 * 后端为 libc malloc/free，并累计计数供 e2e 断言真实调用次数。
 * DBG_SR_MEMORY 变体的 file/func/line/mname 参数仅作调试信息，后端忽略。 */
long kamailio_stub_shm_alloc_calls = 0;
long kamailio_stub_shm_free_calls = 0;

static void *kam_stub_xmalloc(void *mbp, size_t size, const char *file,
		const char *func, unsigned int line, const char *mname)
{
	(void)mbp;
	(void)file;
	(void)func;
	(void)line;
	(void)mname;
	kamailio_stub_shm_alloc_calls++;
	/* 返回清零内存（calloc 语义）：上游 xcap_client/xcap_functions.c:193-207 的
	 * 命名空间节点未给 next 赋值，若后端返回未清零内存，ns_list 链尾即为堆垃圾，
	 * 遍历 ns_list 的用例（含 get_node_selector）会读野指针、崩溃点随 ASLR 漂移。
	 * 清零使被测路径确定可复现；上游该未初始化字段已记入 notes.md。 */
	return calloc(1, size ? size : 1);
}

static void *kam_stub_xmallocxz(void *mbp, size_t size, const char *file,
		const char *func, unsigned int line, const char *mname)
{
	(void)mbp;
	(void)file;
	(void)func;
	(void)line;
	(void)mname;
	kamailio_stub_shm_alloc_calls++;
	return calloc(1, size ? size : 1);
}

static void *kam_stub_xrealloc(void *mbp, void *p, size_t size, const char *file,
		const char *func, unsigned int line, const char *mname)
{
	(void)mbp;
	(void)file;
	(void)func;
	(void)line;
	(void)mname;
	return realloc(p, size ? size : 1);
}

static void kam_stub_xfree(void *mbp, void *p, const char *file, const char *func,
		unsigned int line, const char *mname)
{
	(void)mbp;
	(void)file;
	(void)func;
	(void)line;
	(void)mname;
	if (p)
		kamailio_stub_shm_free_calls++;
	free(p);
}

kam_shm_api_t _shm_root = {
		.mname = "stub-shm",
		.mem_pool = NULL,
		.mem_block = (void *)1, /* 非 NULL 占位：后端忽略该句柄 */
		.xmalloc = kam_stub_xmalloc,
		.xmallocxz = kam_stub_xmallocxz,
		.xmalloc_unsafe = kam_stub_xmalloc,
		.xrealloc = kam_stub_xrealloc,
		.xreallocxf = kam_stub_xrealloc,
		.xresize = kam_stub_xrealloc,
		.xfree = kam_stub_xfree,
		.xfree_unsafe = kam_stub_xfree,
};

kam_pkg_api_t _pkg_root = {
		.mname = "stub-pkg",
		.mem_pool = NULL,
		.mem_block = (void *)1,
		.xmalloc = kam_stub_xmalloc,
		.xmallocxz = kam_stub_xmallocxz,
		.xrealloc = kam_stub_xrealloc,
		.xreallocxf = kam_stub_xrealloc,
		.xfree = kam_stub_xfree,
};

/* 兼容直接引用 shm_malloc 符号的老式调用点（与函数表同一后端） */
void *shm_malloc(size_t size)
{
	kamailio_stub_shm_alloc_calls++;
	return malloc(size ? size : 1);
}

void shm_free(void *ptr)
{
	if (ptr)
		kamailio_stub_shm_free_calls++;
	free(ptr);
}

void *shm_realloc(void *ptr, size_t size)
{
	return realloc(ptr, size ? size : 1);
}

/* ---- KEMI 模块注册：kamailio core 收编模块 KEMI 表的唯一入口 ---- */
void sr_kemi_modules_add(const sr_kemi_t *kemi)
{
	int n = 0;

	if (!kemi)
		return;
	kamailio_stub_kemi_add_calls++;
	kamailio_stub_last_kemi_table = kemi;
	/* 表以全零项结尾：条目数与首项子模块名一并采集，供 e2e 交叉断言 */
	while (!kamailio_stub_kemi_is_end(&kemi[n]) && n < 4096)
		n++;
	kamailio_stub_last_kemi_table_count = n;
	if (n > 0 && kemi[0].mname.s)
	{
		int l = kemi[0].mname.len < (int)sizeof(kamailio_stub_last_kemi_mname) - 1
						? kemi[0].mname.len
						: (int)sizeof(kamailio_stub_last_kemi_mname) - 1;
		memcpy(kamailio_stub_last_kemi_mname, kemi[0].mname.s, l);
		kamailio_stub_last_kemi_mname[l] = '\0';
	}
}

/* ---- 日志路径（等级表置 0 → 静默；函数指针指向 sink → 不空指针调用） ---- */
int log_level_info[64] = {0};

static void kamailio_stub_log_sink(int level, const char *fmt, ...)
{
	(void)level;
	(void)fmt; /* 静默：测试输出只保留断言结果 */
}

void (*_km_log_func)(int, const char *, ...) = kamailio_stub_log_sink;

void dprint(const char *fmt, ...)
{
	(void)fmt;
}

void dprint_color(int level, const char *fmt, ...)
{
	(void)level;
	(void)fmt;
}

int my_pid(void)
{
	return (int)getpid();
}

/* ---- PV 缓冲区（模块导出 cfg 命令时会写日志细节，保持可调用且不为 NULL） ---- */
char *pv_get_buffer(void)
{
	static char buf[16384];
	return buf;
}

int pv_get_buffer_len(void)
{
	return 16384;
}

/*
 * kamailio core 符号 shim —— 仅供 test_package 的 rule12 端到端消费者用例使用。
 *
 * 背景：db_unixodbc.so 是 kamailio 的 **core 插件**，它把 core 提供的 API 与全局量
 * 当作「未定义符号」引用（lib/srdb1 的 db_* 助手、dprint 日志机制、_pkg_root/
 * _shm_root 等）。真实部署时这些符号由 kamailio 主程序导出（-Wl,--export-dynamic）。
 *
 * OHOS 使用 musl libc，其动态链接器**不做惰性绑定**：dlopen(RTLD_LAZY) 等价于
 * RTLD_NOW，库内所有未定义符号必须在加载时就解析完。因此独立加载该模块时，消费者
 * 进程必须提供这些符号 —— 本文件即该最小符号层（相当于把模块依赖的那部分 core ABI
 * 以最小实现提供出来）。它与 test_db_unixodbc_e2e.c 链接成同一个测试可执行文件，
 * 并依靠 -Wl,--export-dynamic 把符号导出到动态符号表供 dlopen 解析。
 *
 * 逐符号取舍（core 语义 + 本用例是否调用）：
 *   1) db_use_table        —— 唯一的真实实现。模块 db_unixodbc_use_table
 *                             (src/modules/db_unixodbc/dbase.c:629) 直接转发到它。
 *   2) db_do_init/do_close —— 模块 init/close 的 core 依赖 (dbase.c:236/248)。
 *   3) 其余 db_* 助手、日志函数 —— 仅需可被解析；本用例路径上不存在这些调用点。
 *   4) core 全局量         —— 零值存储（可读可写，本用例不依赖其值）。
 */
#include <stdio.h>

#include "kamailio_core_stub.h"

/* ─────── 1) 真实实现：core db_use_table（本用例会真实调用） ───────
 * core src/lib/srdb1/db.c:488
 *   if(!_h)                 return -1;   // 连接句柄为空
 *   if(!_t || !_t->s)       return -1;   // 表名无效
 *   CON_TABLE(_h) = _t;     return 0;    // 把表名指针写入连接句柄
 * CON_TABLE(_h) 即 _h->table（core src/lib/srdb1/db_con.h:50），写入的是表名结构体
 * 的指针本身 —— e2e 用例据此断言「模块确实把表名写进了连接句柄」，而非空转。 */
int db_use_table(db1_con_t *_h, const str *_t)
{
	if(!_h) {
		fprintf(stderr, "[core-stub] db_use_table: invalid connection parameter\n");
		return -1;
	}
	if(!_t || !_t->s) {
		fprintf(stderr, "[core-stub] db_use_table: invalid table parameter value\n");
		return -1;
	}
	_h->table = _t;
	return 0;
}

/* ─────── 2) 模块 init/close 的 core 依赖 ─────── */

/* core: db1_con_t *db_do_init(const str *url, void *(*new_connection)(const str *))
 * 语义：解析 URL、经回调建连接、登记到 core 连接池。本用例既无可用 ODBC DSN，
 * 也没有 core 连接池，故返回 NULL —— 模块 db_unixodbc_init 因此返回 NULL
 * （dbase.c:236 对返回值先判空再解引用，NULL 安全），用例据此走 SKIP 分支。 */
void *db_do_init(const str *_url, void *new_connection)
{
	(void)_url;
	(void)new_connection;
	return 0;
}

/* core: void db_do_close(db1_con_t *, void (*free_connection)(db1_con_t *))。
 * 本用例不调用 close（无已建立的连接）。 */
void db_do_close(void *_h, void *free_connection)
{
	(void)_h;
	(void)free_connection;
}

/* ─────── 3) 仅需可解析的 core 助手（本用例不调用） ─────── */

int db_api_init(void) { return 0; }           /* core: 校验 db API 版本（mod_register 调用） */
void *db_new_result(void) { return 0; }       /* core: 分配 db1_res_t */
void *db_allocate_columns(void) { return 0; } /* core: 分配列描述数组 */
void *db_allocate_rows(void) { return 0; }    /* core: 分配行数组 */
void *db_allocate_row(void) { return 0; }     /* core: 分配单个行 */
void db_free_columns(void) { }                /* core: 释放列描述数组 */
void db_free_rows(void) { }                   /* core: 释放行数组 */
void db_free_row(void) { }                    /* core: 释放单个行 */
void db_free_result(void) { }                 /* core: 释放结果集 */
int db_str2val(void) { return -1; }           /* core: 字符串 → db_val_t */
int db_val2str(void) { return -1; }           /* core: db_val_t → 字符串 */
void *db_do_query(void) { return 0; }         /* core: 通用查询助手 */
void *db_do_raw_query(void) { return 0; }     /* core: 通用裸查询助手 */
void *db_do_insert(void) { return 0; }        /* core: 通用插入助手 */
void *db_do_delete(void) { return 0; }        /* core: 通用删除助手 */
void *db_do_update(void) { return 0; }        /* core: 通用更新助手 */
void *db_do_replace(void) { return 0; }       /* core: 通用替换助手 */
int async_task_push(void *task)               /* core: 异步任务入队 */
{
	(void)task;
	return -1;
}

/* ─────── 4) core 日志机制（本用例不下探，直接抑制） ─────── */

int get_debug_level(void) { return -1; }   /* core: 当前调试级别；-1 使阈值检查不通过 */
int get_debug_facility(void) { return 0; } /* core: 日志 facility */
void _km_log_func(int level, const char *fmt, ...)
{
	(void)level;
	(void)fmt;
}
void _ksr_slog_func(int level, const char *fmt, ...)
{
	(void)level;
	(void)fmt;
}
void dprint_crit(void *log_info, const char *fmt, ...)
{
	(void)log_info;
	(void)fmt;
}
int escape_common(char *dst, const char *src, int src_len)
{
	(void)dst;
	(void)src;
	(void)src_len;
	return 0;
}

/* ─────── 5) core 全局量：零值存储（可读可写，本用例不依赖其值） ───────
 * 用字节数组而非精确类型：ELF 解析只看符号名，本用例既不读也不写它们。 */

char _pkg_root[64];          /* core: struct sr_pkg_root *_pkg_root（私有内存根） */
char _shm_root[64];          /* core: struct sr_shm_root *_shm_root（共享内存根） */
char log_stderr[8];          /* core: int log_stderr（日志是否输出到 stderr） */
char log_color[8];           /* core: int log_color（日志是否彩色） */
char my_pid[16];             /* core: pid_t my_pid（进程 pid） */
char process_no[8];          /* core: int process_no（进程编号） */
char log_level_info[256];    /* core: 日志级别名表 */
char log_prefix_val[128];    /* core: char *log_prefix_val（日志前缀） */
char dprint_color[64];       /* core: 颜色转义表 */
char dprint_color_reset[16]; /* core: 颜色复位转义 */

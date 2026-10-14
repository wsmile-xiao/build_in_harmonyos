/* test_db_postgres_consumer.c —— kamailio-postgres 打包产物的消费者端 E2E（真实执行）。
 *
 * 角色：扮演 kamailio core 的模块加载器（宿主），按 loadmodule 的真实次序消费
 * db_postgres.so，与同族 kamailio-* 用例（archives/k/kamailio-slack 的 e2e_consumer.c）
 * 同一形态：
 *
 *   1. dlopen(RTLD_NOW)                 —— loadmodule 第一步：库内所有未定义符号必须在
 *                                          加载时解析完（OHOS/musl 无惰性绑定，模块自身亦
 *                                          为 BIND_NOW）；core 符号由宿主 shim
 *                                          （kamailio_core_stub.c + --export-dynamic）提供，
 *                                          libpq 由依赖包提供。
 *   2. dlsym("kam_exports")             —— 取模块声明的 module_exports（装载入口）。
 *   3. 遍历 cmds[]/params[] 完成注册      —— 等价 core 的模块命令/参数注册（走到 NULL 哨兵）。
 *   4. 在注册表里查 "db_bind_api" 并调用   —— 走模块导出的命令表（而不是直接 dlsym 函数），
 *                                          等价 config 里 core 调用 db_bind_api。
 *   5. 驱动返回的 db_func_t              —— use_table 正例 + 负例（模块转发到 core
 *                                          db_use_table，真实写入连接句柄的 CON_TABLE）。
 *   6. init(url)                        —— 模块的连接建立路径（无 core 连接池/PostgreSQL
 *                                          服务端时安全返回 NULL，打印 SKIP 与原因）。
 *
 * 产出：确定性报告（固定顺序逐行输出），末行汇总为
 *   "== 结果：<n> passed, <m> failed =="
 *
 * 独立交叉校验：命令表里 "db_bind_api" 的函数指针必须等于模块动态符号表里
 * db_postgres_bind_api 的地址 —— 两条独立来源（模块声明的导出表 vs ELF 动态符号表）
 * 必须一致，用以证伪"命令表空转/占位"。
 *
 * 用法：test_db_postgres_consumer <db_postgres.so 绝对路径>
 * 退出码：0 = 全部通过；1 = 存在失败项。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#include "kamailio_core_stub.h" /* str / db1_con_t（与 core 定义同构） */

/* ───────────────────────── core 结构（与核心头文件逐字段同构） ─────────────────────────
 * core src/core/sr_module.h（kamailio 6.0.6）：
 *   typedef struct cmd_export { char *name; cmd_function function; int param_no;
 *                               fixup_function fixup; free_fixup_function free_fixup;
 *                               unsigned int flags; } cmd_export_t;
 *   typedef struct param_export { char *name; modparam_t type; void *param_pointer; } param_export_t;
 *   typedef struct module_exports { char *name; unsigned int dlflags; cmd_export_t *cmds;
 *       param_export_t *params; rpc_export_t *rpc_methods; pv_export_t *pv_items;
 *       response_function response_f; init_function init_mod_f; child_init_function init_child_f;
 *       destroy_function destroy_mod_f; } module_exports_t;
 * 函数指针字段在 ABI 上与 void* 同宽，这里以 void* 承接即可（仅存取不调用）。 */
typedef struct
{
	char *name;
	void *function;
	int param_no;
	void *fixup;
	void *free_fixup;
	unsigned int flags;
} cmd_export_t;

typedef struct
{
	char *name;
	int type;
	void *param_pointer;
} param_export_t;

typedef struct
{
	char *name;
	unsigned int dlflags;
	cmd_export_t *cmds;
	param_export_t *params;
	void *rpc_methods;
	void *pv_items;
	void *response_f;
	void *init_mod_f;
	void *init_child_f;
	void *destroy_mod_f;
} module_exports_t;

/* ─────────────────────── db_func_t（core src/lib/srdb1/db.h:408） ───────────────────────
 * 与模块 db_bind_api 内部 memset 的 sizeof(db_func_t) 必须一致（否则越界写坏调用方栈）。 */
typedef int (*db_use_table_f)(db1_con_t *, const str *);
typedef db1_con_t *(*db_init_f)(const str *);
typedef void (*db_close_f)(db1_con_t *);
typedef void *db_any_f;

struct db_func {
	unsigned int cap;
	db_use_table_f use_table;
	db_init_f init;
	db_any_f init2;
	db_close_f close;
	db_any_f query;
	db_any_f fetch_result;
	db_any_f raw_query;
	db_any_f free_result;
	db_any_f insert;
	db_any_f delete_;
	db_any_f update;
	db_any_f replace;
	db_any_f last_inserted_id;
	db_any_f insert_update;
	db_any_f insert_delayed;
	db_any_f insert_async;
	db_any_f affected_rows;
	db_any_f start_transaction;
	db_any_f end_transaction;
	db_any_f abort_transaction;
	db_any_f query_lock;
	db_any_f raw_query_async;
};

/* cap(4B) + 对齐(4B) + 22 个函数指针 */
_Static_assert(sizeof(struct db_func) == 8 + 22 * sizeof(void *),
			   "db_func 布局应与 core src/lib/srdb1/db.h:408 一致");

typedef int (*db_bind_api_f)(struct db_func *);

static int passes = 0;
static int failures = 0;

static void check(int cond, const char *label)
{
	printf("[%s] %s\n", cond ? "PASS" : "FAIL", label);
	if (cond)
		passes++;
	else
		failures++;
}

int main(int argc, char **argv)
{
	if (argc < 2) {
		fprintf(stderr, "usage: %s <path/to/db_postgres.so>\n", argv[0]);
		return 2;
	}
	const char *module_path = argv[1];

	printf("kamailio-postgres consumer E2E (host = kamailio core module loader)\n");
	printf("module: %s\n", module_path);

	/* ── 1) loadmodule 第一步：加载并解析全部未定义符号 ── */
	void *h = dlopen(module_path, RTLD_NOW | RTLD_LOCAL);
	if (!h) {
		fprintf(stderr, "dlopen failed: %s\n", dlerror());
		return 1;
	}
	check(1, "dlopen(RTLD_NOW) 装载模块成功（core 符号由宿主 shim 解析，libpq 由依赖包提供）");

	/* ── 2) 取模块声明的装载入口 module_exports ── */
	dlerror();
	module_exports_t *me = (module_exports_t *)dlsym(h, "kam_exports");
	if (me == NULL)
		me = (module_exports_t *)dlsym(h, "exports");
	check(dlerror() == NULL && me != NULL,
		  "module_exports 装载入口符号存在（kam_exports/exports）");

	if (me == NULL) {
		dlclose(h);
		printf("\n== 结果：%d passed, %d failed ==\n", passes, failures);
		return failures ? 1 : 0;
	}

	/* ── 3) 读取模块名 + 遍历注册导出的命令/参数表（走到 NULL 哨兵） ── */
	printf("module_name: %s\n", me->name ? me->name : "()");
	check(me->name != NULL && strcmp(me->name, "db_postgres") == 0,
		  "模块声明名称为 \"db_postgres\"");

	int ncmds = 0;
	int bind_api_idx = -1;
	if (me->cmds != NULL) {
		for (int i = 0; me->cmds[i].name != NULL; i++) {
			printf("registered_cmd: %s (param_no=%d)\n", me->cmds[i].name,
				   me->cmds[i].param_no);
			if (strcmp(me->cmds[i].name, "db_bind_api") == 0)
				bind_api_idx = i;
			ncmds++;
		}
	}
	printf("cmds_count: %d\n", ncmds);
	check(ncmds >= 1, "已注册至少 1 个导出命令（cmds[] 遍历到 NULL 哨兵）");
	check(bind_api_idx >= 0, "导出命令表中存在 \"db_bind_api\"（core 的 DB 驱动绑定入口）");

	int nparams = 0;
	if (me->params != NULL) {
		for (int i = 0; me->params[i].name != NULL; i++)
			nparams++;
	}
	printf("params_count: %d\n", nparams);

	/* ── 4) 通过注册表调用 db_bind_api（而非直接 dlsym 取函数） ── */
	if (bind_api_idx >= 0) {
		void *sym = dlsym(h, "db_postgres_bind_api");
		check(sym != NULL && sym == me->cmds[bind_api_idx].function,
			  "命令表 db_bind_api 的函数指针 == 模块 ELF 符号 db_postgres_bind_api"
			  "（导出表 vs 动态符号表，独立来源一致）");

		struct db_func dbf;
		memset(&dbf, 0, sizeof(dbf)); /* 先清零：bind 写入后以下 != NULL 断言才具判别力 */
		int rc = ((db_bind_api_f)me->cmds[bind_api_idx].function)(&dbf);
		check(rc == 0, "经注册表调用 db_bind_api(&dbf) 返回 0（API 绑定成功）");

		int bound = 0;
		bound += dbf.use_table != NULL;
		bound += dbf.init != NULL;
		bound += dbf.init2 != NULL;
		bound += dbf.close != NULL;
		bound += dbf.query != NULL;
		bound += dbf.fetch_result != NULL;
		bound += dbf.raw_query != NULL;
		bound += dbf.free_result != NULL;
		bound += dbf.insert != NULL;
		bound += dbf.update != NULL;
		bound += dbf.delete_ != NULL;
		bound += dbf.start_transaction != NULL;
		bound += dbf.end_transaction != NULL;
		bound += dbf.abort_transaction != NULL;
		printf("bound_callbacks: %d\n", bound);
		check(bound >= 14, "db_func_t 回调已批量绑定（use_table/init/close/query/… >= 14 项）");
		check(dbf.use_table != NULL, "use_table 回调已绑定");

		/* ── 5) 驱动 db_func_t：use_table 正例 + 负例（core CON_TABLE 语义） ── */
		str table = { (char *)"subscriber", 10 };
		db1_con_t con;
		memset(&con, 0, sizeof(con));
		int urc = dbf.use_table(&con, &table);
		check(urc == 0, "use_table(&con, \"subscriber\") 返回 0（模块转发到 core db_use_table）");
		check(con.table == &table,
			  "连接句柄的 CON_TABLE 被真实写入表名指针（非空转）");
		check(dbf.use_table(NULL, &table) == -1, "use_table(NULL 连接) 返回 -1（真实校验）");
		check(dbf.use_table(&con, NULL) == -1, "use_table(NULL 表名) 返回 -1（真实校验）");
		check(con.table == &table, "负例未破坏已写入的表名");

		/* ── 6) init 联库段：无 core 连接池 + 无 PostgreSQL 服务端 → 安全返回 NULL ── */
		str url = { (char *)"postgres://kamailio:kamailio@localhost:5432/kamailio", 52 };
		db1_con_t *conn = dbf.init(&url);
		if (conn != NULL) {
			printf("init_result: connected\n");
			check(1, "db_postgres_init 返回连接句柄（本环境存在可用 PostgreSQL 服务端），关闭之");
			dbf.close(conn);
		} else {
			printf("init_result: no-connection\n");
			printf("[SKIP] dbf.init 未建立连接（本包不含 kamailio core 连接池/PostgreSQL 服务端），"
				   "加载→注册→绑定→use_table（含负例）已完整走通\n");
		}
	}

	dlclose(h);

	printf("\n== 结果：%d passed, %d failed ==\n", passes, failures);
	return failures ? 1 : 0;
}

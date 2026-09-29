// HarmonyOS PC 端到端消费者用例（rule12）：
// 以 kamailio core loadmodule 的同一条路径消费 db_unixodbc.so ——
//   dlopen → dlsym("db_bind_api") → db_bind_api(&dbf) 绑定回调
//   → dbf.use_table(&con, &table) 经模块转发到 core db_use_table，真实写入表名
// 并附负例，确认绑定到的是真实实现而非空壳。
//
// 上游对应：
//   src/modules/db_unixodbc/db_unixodbc.c:75  db_unixodbc_bind_api（memset + 逐项赋值）
//   src/modules/db_unixodbc/dbase.c:629        db_unixodbc_use_table → db_use_table
//   src/lib/srdb1/db.c:488                     core db_use_table（校验 + CON_TABLE 赋值）
//   src/lib/srdb1/db_con.h:50                  CON_TABLE(cn) == (cn)->table
//
// 依赖说明：db_unixodbc.so 是 core 插件，引用 core 助手与全局量；OHOS/musl 的加载器
// 不做惰性绑定，因此由 kamailio_core_stub.c 提供最小 core 符号层，并在 conanfile.py
// 里以 -Wl,--export-dynamic 导出符号供 dlopen 解析。
//
// init/query 联库段：core 的 db_do_init 需要 core 连接池与可用 ODBC DSN，两者都不在
// 本包可自动化范围（shim 对此明确返回 NULL），故本用例只验证 init 可被真实调用且安全
// 返回，打印 SKIP 与原因，不计失败。
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#include "kamailio_core_stub.h" // str / db1_con_t（与 core 定义同构）

// 与上游 src/lib/srdb1/db.h:408 struct db_func 同构：字段顺序与数量必须一致 ——
// 模块 db_bind_api 会对整个结构体 memset 并按偏移逐项赋值，布局不符会写坏调用方栈。
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

// cap(4B) + 对齐(4B) + 22 个函数指针
_Static_assert(sizeof(struct db_func) == 8 + 22 * sizeof(void *),
		"db_func 布局应与 core src/lib/srdb1/db.h:408 一致");

typedef int (*db_bind_api_f)(struct db_func *dbb);

static int failures = 0;

static void check(int cond, const char *label)
{
	printf("[%s] %s\n", cond ? "PASS" : "FAIL", label);
	if (!cond)
		failures++;
}

int main(int argc, char **argv)
{
	if (argc < 2) {
		fprintf(stderr, "usage: %s <path/to/db_unixodbc.so>\n", argv[0]);
		return 2;
	}
	const char *module_path = argv[1];

	// 1) 加载：与 kamailio core 的 loadmodule 同路径
	void *h = dlopen(module_path, RTLD_NOW | RTLD_LOCAL);
	if (!h) {
		fprintf(stderr, "dlopen failed: %s\n", dlerror());
		return 1;
	}
	printf("artifact: %s loaded\n", module_path);
	check(1, "dlopen 加载模块成功（core 未定义符号由 kamailio_core_stub.c 解析）");

	// 模块的 core 装载描述符（db_unixodbc.c:64 struct module_exports exports）
	check(dlsym(h, "exports") != NULL, "模块导出描述符 exports 符号存在（core 装载入口）");

	// 2) 模块 API 入口：core 按 exports.cmds 里的 "db_bind_api" 条目
	//    （db_unixodbc.c:50 {"db_bind_api", (cmd_function)db_unixodbc_bind_api}）解析并调用
	//    db_unixodbc_bind_api —— 本用例直接取其 ELF 符号地址（同一函数）。
	dlerror();
	db_bind_api_f bind_api = (db_bind_api_f)dlsym(h, "db_unixodbc_bind_api");
	const char *sym_err = dlerror();
	check(sym_err == NULL && bind_api != NULL,
			"dlsym db_unixodbc_bind_api（exports.cmds 的 db_bind_api 入口）");
	if (!bind_api) {
		dlclose(h);
		return 1;
	}

	// 3) 绑定：db_unixodbc_bind_api 对 db_func_t memset 后逐项赋值并返回 0
	struct db_func dbf;
	memset(&dbf, 0xAA, sizeof(dbf)); // 预填脏值，验证 bind 真实写入
	check(bind_api(&dbf) == 0, "db_bind_api 返回 0（API 绑定成功）");
	check(dbf.use_table != NULL, "use_table 回调已绑定");
	check(dbf.init != NULL, "init 回调已绑定");
	check(dbf.close != NULL, "close 回调已绑定");
	check(dbf.query != NULL, "query 回调已绑定");
	check(dbf.insert != NULL, "insert 回调已绑定");
	check(dbf.raw_query != NULL, "raw_query 回调已绑定");

	// 4) use_table 端到端调用：模块 db_unixodbc_use_table 转发给 core db_use_table，
	//    后者把「表名结构体指针」写入连接句柄的 table 字段（CON_TABLE）。
	str table = { (char *)"subscriber", 10 };
	db1_con_t con;
	memset(&con, 0, sizeof(con));
	int rc = dbf.use_table(&con, &table);
	check(rc == 0, "use_table(&con, \"subscriber\") 返回 0");
	check(con.table == &table, "连接 table 字段被真实写入（core CON_TABLE 语义）");

	// 5) 负例：确认链路上跑的是 core 的真实校验，而非恒返回 0 的空壳
	check(dbf.use_table(NULL, &table) == -1, "use_table(NULL 连接) 返回 -1（真实校验）");
	check(dbf.use_table(&con, NULL) == -1, "use_table(NULL 表名) 返回 -1（真实校验）");
	check(con.table == &table, "负例未破坏已写入的表名");

	// 6) init 联库段：core db_do_init 需要 core 连接池 + 可用 ODBC DSN，均不在本包
	//    可自动化范围，shim 明确返回 NULL；此处验证 init 被真实调用且安全返回。
	str url = { (char *)"unixodbc://kamailio", 19 };
	db1_con_t *conn = dbf.init(&url);
	if (conn) {
		printf("[PASS] dbf.init 返回连接句柄（本环境存在可用 ODBC 数据源），关闭之\n");
		dbf.close(conn);
	} else {
		printf("[SKIP] dbf.init 未建立连接（本包不含 kamailio core 连接池/ODBC 数据源）；"
				"dlopen→bind_api→回调绑定→use_table（含负例）已完成端到端验证\n");
	}

	dlclose(h);
	if (failures) {
		printf("\nE2E FAILED: %d 项\n", failures);
		return 1;
	}
	printf("\nE2E OK: 绑定+调用链全部通过\n");
	return 0;
}

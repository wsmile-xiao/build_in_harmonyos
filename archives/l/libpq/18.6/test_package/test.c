/* libpq 18.6 消费者测试。
 *
 * 三个层面验证真实链接的 libpq：
 *   1. 版本契约：PQlibVersion() == PG_VERSION_NUM(18.6) == 180006；
 *   2. 连接信息解析：镜像上游 src/interfaces/libpq/test/libpq_uri_regress.c
 *      与 t/001_uri.pl 的 URI → conninfo 字段解析（纯库内逻辑，无网络）；
 *   3. 失败路径不崩：对 127.0.0.1:1 发起 PQconnectdb 应干净返回
 *      CONNECTION_BAD（无需真实 PostgreSQL 服务端）。
 *
 * 任一检查失败即打印 not ok 并返回非零，令 conan test_package 失败。
 */
#include <libpq-fe.h>
#include <stdio.h>
#include <string.h>

static int checks_passed = 0;
static int checks_failed = 0;

#define CHECK(cond, desc)                                        \
	do {                                                         \
		if (cond) {                                              \
			checks_passed++;                                     \
			printf("ok - %s\n", desc);                           \
		} else {                                                 \
			checks_failed++;                                     \
			printf("not ok - %s\n", desc);                       \
		}                                                        \
	} while (0)

static const char *conninfo_value(const PQconninfoOption *options,
                                  const char *keyword)
{
	for (const PQconninfoOption *opt = options; opt && opt->keyword; opt++) {
		if (strcmp(opt->keyword, keyword) == 0)
			return opt->val;
	}
	return NULL;
}

static const char *null_to_empty(const char *value)
{
	return value == NULL ? "" : value;
}

int main(void)
{
	printf("libpq consumer probe (PQlibVersion=%d)\n", PQlibVersion());

	/* 1. 版本契约：18.6 -> 180006（psycopg-c 3.3 等消费方按此编译）。 */
	CHECK(PQlibVersion() == 180006, "PQlibVersion() == 180006 (18.6)");

	/* 2. URI 连接串解析，字段对齐上游 t/001_uri.pl。 */
	const char *uri =
		"postgresql://uri-user:secret@host.example.com:12345/dbname?sslmode=disable";
	char *errmsg = NULL;
	PQconninfoOption *options = PQconninfoParse(uri, &errmsg);
	CHECK(options != NULL && errmsg == NULL, "PQconninfoParse accepts URI");

	if (options != NULL) {
		CHECK(strcmp(null_to_empty(conninfo_value(options, "user")),
		             "uri-user") == 0,
		      "conninfo user == 'uri-user'");
		CHECK(strcmp(null_to_empty(conninfo_value(options, "password")),
		             "secret") == 0,
		      "conninfo password == 'secret'");
		CHECK(strcmp(null_to_empty(conninfo_value(options, "host")),
		             "host.example.com") == 0,
		      "conninfo host == 'host.example.com'");
		CHECK(strcmp(null_to_empty(conninfo_value(options, "port")),
		             "12345") == 0,
		      "conninfo port == '12345'");
		CHECK(strcmp(null_to_empty(conninfo_value(options, "dbname")),
		             "dbname") == 0,
		      "conninfo dbname == 'dbname'");
		CHECK(strcmp(null_to_empty(conninfo_value(options, "sslmode")),
		             "disable") == 0,
		      "conninfo sslmode == 'disable'");
		PQconninfoFree(options);
	} else {
		checks_failed += 6;
		printf("not ok - conninfo field checks (parse failed)\n");
	}
	PQfreemem(errmsg);

	/* 3. 连接失败路径：无需服务端，127.0.0.1:1 应干净返回 CONNECTION_BAD。 */
	PGconn *conn = PQconnectdb("host=127.0.0.1 port=1 connect_timeout=2");
	CHECK(conn != NULL, "PQconnectdb returns a PGconn object");
	if (conn != NULL) {
		CHECK(PQstatus(conn) == CONNECTION_BAD,
		      "connection to closed port 1 is CONNECTION_BAD");
		CHECK(strlen(PQerrorMessage(conn)) > 0,
		      "PQerrorMessage is populated");
		PQfinish(conn);
	} else {
		checks_failed += 2;
		printf("not ok - connection checks (PQconnectdb returned NULL)\n");
	}

	printf("%d checks passed, %d checks failed\n", checks_passed,
	       checks_failed);
	return checks_failed == 0 ? 0 : 1;
}

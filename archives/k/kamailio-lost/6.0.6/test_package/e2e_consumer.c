/* e2e_consumer.c — kamailio-lost 打包产物的消费者端 E2E（层 2，真实执行）。
 *
 * 角色：扮演 kamailio 核心（最小桩实现），按 kamailio 真实加载次序消费 lost.so：
 *
 *   1. dlopen(RTLD_NOW)          —— 等价 loadmodule 第一步：所有未定义符号必须可解析
 *                                    （含 libxml2.so.16 / libcurl.so 两个 DT_NEEDED，
 *                                     这是本包"双原生依赖"在运行期被真正解析的证据）
 *   2. dlsym("exports")          —— 校验 module_exports 描述符与 cmds/params 表内容
 *   3. exports.init_mod_f()      —— 等价 mod_init：绑定 http_client API（bind_http_client）
 *   4. cmds[2] 全链路            —— lost_held_dereference() 真实执行：
 *                                   get_str_fparam → lost_held_post_request（libxml2 组包）
 *                                   → http_client_query_c（桩）→ xmlReadMemory +
 *                                   xmlNodeGetNodeContentByName（libxml2 解析）
 *                                   → pv setf 回写；覆盖 LocByVal / LocByRef /
 *                                   非法根元素 / HTTP 非 2xx 四条分支
 *
 * 桩符号集来自实测 readelf --dyn-syms lost.so 的 UND 集（28 个 kamailio 核心符号），
 * 逐项见 test_package/MANIFEST.yml。libxml2 与 libc 的符号不在此桩内：
 * 它们由 DT_NEEDED 里的 libxml2.so.16 / libc.so 解析（经 LD_LIBRARY_PATH）。
 *
 * 私有内存管理器桩必须与 lost.so 编译时的 sr_pkg_api_t 字段序一致：
 *   mname, mem_pool, mem_block, xmalloc, xmallocxz, xrealloc, xreallocxf, xfree, ...
 * （本包的 config.mak 带 -DDBG_SR_MEMORY，故 pkg_malloc 展开为
 *   _pkg_root.xmalloc(_pkg_root.mem_block, size, file, func, line) —— 第 3..5 参
 *   本桩不再解引用，仅靠 AArch64 ABI 的 x2..x5 承载。）
 *
 * 用法：e2e_consumer <lost.so 绝对路径>
 * 退出码：0 = 全部通过；1 = 存在失败项。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ────────────── kamailio 核心结构（布局对齐 lost.so 编译期头文件） ────────────── */

typedef struct
{
	char *s;
	int len;
} str_t;

typedef struct
{
	char *name;
	unsigned int dlflags;
	void *cmds;
	void *params;
	void *rpc_methods;
	void *pv_items;
	void *response_f;
	int (*init_mod_f)(void);
	void *init_child_f;
	void (*destroy_mod_f)(void);
} module_exports_t;

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
	unsigned int type;
	void *param_pointer;
} param_export_t;

/* pv_spec_t 前缀（core/pvar.h）: type / getf / setf / pvp / trans。
 * 本测试只触及 setf（偏移 16）与 &pvp（偏移 24），故 pvp 用足够大的字节数组占位。 */
typedef struct
{
	int type;
	void *getf;
	int (*setf)(void *msg, void *pvp, int op, void *val);
	unsigned char pvp_pad[64];
} pv_spec_t;

typedef struct
{
	str_t rs;
	long ri;
	int flags;
} pv_value_t;

/* http_client 模块导出的 API（modules/http_client/curl_api.h） */
typedef struct
{
	void *http_connect;
	int (*http_client_query)(void *msg, char *url, str_t *dst, char *post, char *hdrs);
	int (*http_client_query_c)(
			void *msg, char *url, str_t *dst, char *post, char *ctype, char *hdrs);
	void *http_connection_exists;
	void *http_get_content_type;
} httpc_api_t;

#define PARAM_STRING (1U << 0)
#define PARAM_INT (1U << 1)
#define PARAM_STR (1U << 2)
#define PARAM_USE_FUNC (1U << (8 * sizeof(int) - 1))

/* ────────────── 私有内存管理器桩（_pkg_root） ──────────────
 * 本包 config.mak 带 -DDBG_SR_MEMORY，调用形态为 5 参
 * (mem_block, size, file, func, line)；此处声明 6 参以同时兼容非 DBG 的 2 参形态
 * （多出的参数在 AArch64 ABI 下位于 x2..x5，被忽略）。 */
typedef void *(*mem_alloc_f)(void *, unsigned long, void *, void *, int, void *);
typedef void (*mem_free_f)(void *, void *, void *, void *, int, void *);

static void *stub_alloc(void *mbp, unsigned long size, void *a, void *b, int c, void *d)
{
	(void)mbp;
	(void)a;
	(void)b;
	(void)c;
	(void)d;
	return malloc(size);
}

static void *stub_alloc0(void *mbp, unsigned long size, void *a, void *b, int c, void *d)
{
	void *p = stub_alloc(mbp, size, a, b, c, d);
	if(p)
		memset(p, 0, size);
	return p;
}

static void stub_free(void *mbp, void *p, void *a, void *b, int c, void *d)
{
	(void)mbp;
	(void)a;
	(void)b;
	(void)c;
	(void)d;
	free(p);
}

static void *stub_realloc(void *mbp, void *p, unsigned long size, void *b, int c, void *d)
{
	(void)mbp;
	(void)b;
	(void)c;
	(void)d;
	return realloc(p, size);
}

typedef struct
{
	char *mname;
	char *mem_pool;
	void *mem_block;
	mem_alloc_f xmalloc;
	mem_alloc_f xmallocxz;
	void *xrealloc;
	void *xreallocxf;
	mem_free_f xfree;
	void *tail[9]; /* xstatus..xfmodstats（本测试不触及） */
} pkg_api_t;

pkg_api_t _pkg_root;

/* ────────────── 核心日志/全局变量桩（lost.so 的未定义数据符号） ──────────────
 * 严格对齐 core/dprint.h 的声明形态：
 *   km_log_f _km_log_func（函数指针变量，非函数）、ksr_slog_f _ksr_slog_func、
 *   int my_pid(void)（函数）、void dprint_color(int)（函数）、
 *   str *log_prefix_val、struct log_level_info log_level_info[]、int process_no 等。
 * 形态写错（如把指针变量当函数）→ 模块按数据取指针再间接调用 → PC 对齐异常(SIGBUS)。 */
typedef void (*km_log_f)(int, const char *, ...);
typedef struct
{
	int v_facility;
	int v_level;
	char *v_lname;
	const char *v_fname;
	int v_fline;
	const char *v_mname;
	const char *v_func;
	const char *v_locinfo;
	int v_pid;
	int v_pidx;
} ksr_logdata_t;
typedef void (*ksr_slog_f)(ksr_logdata_t *, const char *, ...);

/* 统计模块输出的日志条数。core/dprint.h 的 LOG 宏先看 _ksr_slog_func：
 * 非空则走结构化日志、否则走 _km_log_func，故两条路径都要计数。 */
static int g_log_msgs = 0;

static void stub_km_log(int level, const char *fmt, ...)
{
	(void)level;
	(void)fmt;
	g_log_msgs++;
}

static void stub_ksr_slog(ksr_logdata_t *ld, const char *fmt, ...)
{
	(void)ld;
	(void)fmt;
	g_log_msgs++;
}

km_log_f _km_log_func = stub_km_log;
ksr_slog_f _ksr_slog_func = stub_ksr_slog;

int process_no = 0;
int log_stderr = 0;
int log_color = 0;
char *log_prefix_fmt = NULL;
str_t _e2e_log_prefix = {NULL, 0};
str_t *log_prefix_val = &_e2e_log_prefix;
int log_prefix_mode = 0;
char *log_name = NULL;
char *log_fqdn = NULL;
volatile int dprint_crit = 0;

struct log_level_info
{
	char *name;
	int syslog_level;
};
struct log_level_info log_level_info[24];

int my_pid(void)
{
	return 1;
}

void dprint_color(int level)
{
	(void)level;
}

void dprint_color_reset(void)
{
}

int get_debug_level(char *mname, int mnlen)
{
	(void)mname;
	(void)mnlen;
	return 2; /* L_INFO：让模块的 LM_INFO/LM_ERR 路径也真实走到桩 */
}

int get_debug_facility(char *mname, int mnlen)
{
	(void)mname;
	(void)mnlen;
	return 0;
}

/* ────────────── 未在本次执行路径中调用、但 RTLD_NOW 必须能解析的核心符号桩 ──────────────
 * 均为解析占位：签名只需保证返回值类型宽度正确（调用点在模块内的消息处理分支，
 * 本测试不进入）。 */
int parse_uri(char *buf, int len, void *uri)
{
	(void)buf;
	(void)len;
	(void)uri;
	return -1;
}

int parse_headers(void *msg, int flags, int next)
{
	(void)msg;
	(void)flags;
	(void)next;
	return -1;
}

void *parse_from_header(void *msg)
{
	(void)msg;
	return NULL;
}

void *parse_pai_header(void *msg)
{
	(void)msg;
	return NULL;
}

void *get_body_part_by_filter(void *msg, void *a, unsigned int b, void *c, void *d, int e)
{
	(void)msg;
	(void)a;
	(void)b;
	(void)c;
	(void)d;
	(void)e;
	return NULL;
}

void free_rdata_list(void *list)
{
	(void)list;
}

int reg_replace(char *m, char *r, char *s, char *p, char *i, int fl)
{
	(void)m;
	(void)r;
	(void)s;
	(void)p;
	(void)i;
	(void)fl;
	return -1;
}

void *get_record(void)
{
	return NULL;
}

int fixup_spve_null(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}

int fixup_free_spve_null(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}

int fixup_pvar_null(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}

int fixup_free_pvar_null(void **param, int param_no)
{
	(void)param;
	(void)param_no;
	return 0;
}

/* ────────────── http_client 侧桩：记录模块投递的 URL / 正文 / 头部 / 返回码 ────────────── */

static int g_query_calls = 0;
static int g_query_status = 200;
static char g_uri[512];
static char g_post[4096];
static char g_ctype[256];
static char g_hdrs[512];
static const char *g_response = "";

static int fake_httpc_query_c(void *msg, char *url, str_t *dst, char *post,
		char *ctype, char *hdrs)
{
	(void)msg;
	g_query_calls++;
	snprintf(g_uri, sizeof(g_uri), "%s", url ? url : "");
	snprintf(g_post, sizeof(g_post), "%s", post ? post : "");
	snprintf(g_ctype, sizeof(g_ctype), "%s", ctype ? ctype : "");
	snprintf(g_hdrs, sizeof(g_hdrs), "%s", hdrs ? hdrs : "");
	if(dst) {
		/* http_client 的响应体由被调方按 pkg 内存分配、调用方 pkg_free；
		 * 故此处必须经同一管理器分配，否则 lost_free_string 会 free 静态串而崩溃。 */
		size_t n = strlen(g_response);
		char *body = (char *)malloc(n + 1);
		if(body == NULL)
			return -1;
		memcpy(body, g_response, n + 1);
		dst->s = body;
		dst->len = (int)n;
	}
	return g_query_status;
}

static int fake_httpc_query(void *msg, char *url, str_t *dst, char *post, char *hdrs)
{
	return fake_httpc_query_c(msg, url, dst, post, NULL, hdrs);
}

/* find_export("bind_http_client") 返回的绑定函数：把桩 API 灌进模块的 httpc_api_t */
static httpc_api_t *g_bound_api = NULL;

static int fake_bind_httpc(httpc_api_t *api)
{
	api->http_connect = NULL;
	api->http_client_query = fake_httpc_query;
	api->http_client_query_c = fake_httpc_query_c;
	api->http_connection_exists = NULL;
	api->http_get_content_type = NULL;
	g_bound_api = api;
	return 0;
}

void *find_export(char *name, int param_no, int flags)
{
	(void)param_no;
	(void)flags;
	if(name && strcmp(name, "bind_http_client") == 0)
		return (void *)fake_bind_httpc;
	return NULL;
}

/* ────────────── 脚本参数取值桩：get_str_fparam ──────────────
 * lost_held_dereference() 依次取 url / response-time / response-type 三个参数。 */
static const char *g_fparam_vals[3] = {
		"https://lis.example.com/held",
		"5",
		"geodetic locationURI"};
static int g_fparam_idx = 0;

int get_str_fparam(str_t *dst, void *msg, void *param)
{
	(void)msg;
	(void)param;
	if(dst == NULL || g_fparam_idx >= 3)
		return -1;
	dst->s = (char *)g_fparam_vals[g_fparam_idx];
	dst->len = (int)strlen(g_fparam_vals[g_fparam_idx]);
	g_fparam_idx++;
	return 0;
}

/* ────────────── pv（伪变量）侧桩：捕获模块回写的 pidf / err 结果 ────────────── */

static char g_pv_pidf[4096];
static int g_pv_pidf_calls = 0;
static char g_pv_err[1024];
static int g_pv_err_calls = 0;

/* 两个可写伪变量各挂一个记录器：模块按 pspidf/pserr 两个不同 pv_spec_t 回写，
 * 用同一个函数会让先写者遮住后写者。 */
static int record_pv(char *buf, size_t bufsz, int *calls, void *val)
{
	pv_value_t *v = (pv_value_t *)val;
	if(v == NULL)
		return -1;
	if(v->rs.s != NULL && v->rs.len > 0)
		snprintf(buf, bufsz, "%.*s", v->rs.len, v->rs.s);
	else
		buf[0] = '\0';
	(*calls)++;
	return 0;
}

static int fake_pv_setf_pidf(void *msg, void *pvp, int op, void *val)
{
	(void)msg;
	(void)pvp;
	(void)op;
	return record_pv(g_pv_pidf, sizeof(g_pv_pidf), &g_pv_pidf_calls, val);
}

static int fake_pv_setf_err(void *msg, void *pvp, int op, void *val)
{
	(void)msg;
	(void)pvp;
	(void)op;
	return record_pv(g_pv_err, sizeof(g_pv_err), &g_pv_err_calls, val);
}

/* ────────────── 断言框架 ────────────── */

static int g_pass = 0;
static int g_fail = 0;

static void check(int cond, const char *what)
{
	if(cond) {
		g_pass++;
		printf("[ok]   %s\n", what);
	} else {
		g_fail++;
		printf("[FAIL] %s\n", what);
	}
}

static void checkf(int cond, const char *what, const char *detail)
{
	if(cond) {
		g_pass++;
		printf("[ok]   %s（%s）\n", what, detail);
	} else {
		g_fail++;
		printf("[FAIL] %s（%s）\n", what, detail);
	}
}

/* ────────────── HELD/PIDF 语料 ────────────── */

/* LocByVal：presence 根 + location-info → lost_check_HeldResponse() 返回 2 */
static const char PIDF_VALUE_RESPONSE[] =
		"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
		"<presence xmlns=\"urn:ietf:params:xml:ns:pidf\"\n"
		"          xmlns:gp=\"urn:ietf:params:xml:ns:pidf:geopriv10\"\n"
		"          entity=\"pres:looser@example.com\">\n"
		"  <tuple id=\"t1\">\n"
		"    <status>\n"
		"      <gp:geopriv>\n"
		"        <gp:location-info>\n"
		"          <gs:Circle xmlns:gs=\"http://www.opengis.net/pidflo/1.0\">\n"
		"            <gs:radius uom=\"urn:ogc:def:uom:OGC::m\">30</gs:radius>\n"
		"          </gs:Circle>\n"
		"        </gp:location-info>\n"
		"      </gp:geopriv>\n"
		"    </status>\n"
		"    <timestamp>2026-09-28T00:00:00Z</timestamp>\n"
		"  </tuple>\n"
		"</presence>\n";

/* LocByRef：presence 根 + locationURI → 返回 1 */
static const char PIDF_REFERENCE_RESPONSE[] =
		"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
		"<presence xmlns=\"urn:ietf:params:xml:ns:pidf\"\n"
		"          xmlns:gp=\"urn:ietf:params:xml:ns:pidf:geopriv10\"\n"
		"          entity=\"pres:looser@example.com\">\n"
		"  <tuple id=\"t1\">\n"
		"    <status>\n"
		"      <gp:geopriv>\n"
		"        <gp:locationURI>https://lis.example.com/ref/1</gp:locationURI>\n"
		"      </gp:geopriv>\n"
		"    </status>\n"
		"  </tuple>\n"
		"</presence>\n";

/* 域名合法的 XML，但根元素不在 HELD 允许集合内 → err 分支（400） */
static const char XML_BAD_ROOT[] = "<?xml version=\"1.0\"?><notHeld><x/></notHeld>\n";

#define LOST_SUCCESS 200
#define LOST_CLIENT_ERROR 400

int main(int argc, char **argv)
{
	void *handle;
	module_exports_t *exports;
	cmd_export_t *cmds;
	param_export_t *params;
	char *module_version = NULL;
	char *module_flags = NULL;
	unsigned int *module_interface_ver = NULL;
	pv_spec_t pidf_spec;
	pv_spec_t err_spec;
	int (*deref_fn)(void *, char *, char *, char *, void *, void *);
	int rc;

	if(argc < 2) {
		printf("[FAIL] 用法: e2e_consumer <lost.so>\n");
		return 1;
	}
	setbuf(stdout, NULL); /* 逐行输出：崩溃时也能定位到具体检查项 */

	/* 私有内存管理器：模块的 pkg_malloc/pkg_free 直接作用于该结构 */
	_pkg_root.mname = (char *)"e2e-stub";
	_pkg_root.mem_block = NULL;
	_pkg_root.xmalloc = stub_alloc;
	_pkg_root.xmallocxz = stub_alloc0;
	_pkg_root.xrealloc = stub_realloc;
	_pkg_root.xfree = stub_free;

	memset(&pidf_spec, 0, sizeof(pidf_spec));
	memset(&err_spec, 0, sizeof(err_spec));
	pidf_spec.setf = fake_pv_setf_pidf;
	err_spec.setf = fake_pv_setf_err;

	printf("== kamailio-lost 消费者 E2E（dlopen 真实加载） ==\n");
	printf("module: %s\n\n", argv[1]);

	/* 1) 等价 loadmodule 第一步：加载并解析全部未定义符号（含 libxml2/libcurl） */
	handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
	if(handle == NULL) {
		printf("[FAIL] dlopen(RTLD_NOW) 失败：%s\n", dlerror());
		g_fail++;
		printf("\n== 结果：%d passed, %d failed ==\n", g_pass, g_fail);
		printf("== CHECKS FAILED ==\n");
		return 1;
	}
	check(1, "dlopen(RTLD_NOW) 成功（28 个核心桩 + libxml2/libcurl 全部可解析，等价 loadmodule）");

	/* 2) dlsym：核心按名解析的入口符号 */
	exports = (module_exports_t *)dlsym(handle, "exports");
	check(exports != NULL, "dlsym(\"exports\") 解析模块描述符");
	module_version = (char *)dlsym(handle, "module_version");
	check(module_version != NULL, "dlsym(\"module_version\") 解析模块版本符号");
	module_flags = (char *)dlsym(handle, "module_flags");
	check(module_flags != NULL, "dlsym(\"module_flags\") 解析编译标志符号");
	module_interface_ver = (unsigned int *)dlsym(handle, "module_interface_ver");
	check(module_interface_ver != NULL && *module_interface_ver == 4,
			"dlsym(\"module_interface_ver\") == 4（接口版本校验）");
	check(dlsym(handle, "mod_register") == NULL,
			"无 KEMI 入口 mod_register（lost 未导出 KEMI，负断言）");
	if(exports == NULL)
		return 1;

	checkf(exports->name != NULL && strcmp(exports->name, "lost") == 0,
			"module_exports.name == \"lost\"",
			exports->name ? exports->name : "(null)");

	/* 3) cmds 表：5 个脚本侧入口（lost_held_query ×2 / lost_held_dereference / lost_query ×2） */
	cmds = (cmd_export_t *)exports->cmds;
	check(cmds != NULL, "exports.cmds 非空");
	check(cmds != NULL && cmds[0].name != NULL
					&& strcmp(cmds[0].name, "lost_held_query") == 0
					&& cmds[0].param_no == 4,
			"cmds[0] == lost_held_query(4)（脚本侧无 id 变体）");
	check(cmds != NULL && cmds[1].name != NULL
					&& strcmp(cmds[1].name, "lost_held_query") == 0
					&& cmds[1].param_no == 5,
			"cmds[1] == lost_held_query(5)（带 id 变体，同名不同元数）");
	check(cmds != NULL && cmds[2].name != NULL
					&& strcmp(cmds[2].name, "lost_held_dereference") == 0
					&& cmds[2].param_no == 5,
			"cmds[2] == lost_held_dereference(5)");
	check(cmds != NULL && cmds[3].name != NULL
					&& strcmp(cmds[3].name, "lost_query") == 0
					&& cmds[3].param_no == 4,
			"cmds[3] == lost_query(4)");
	check(cmds != NULL && cmds[4].name != NULL
					&& strcmp(cmds[4].name, "lost_query") == 0
					&& cmds[4].param_no == 6,
			"cmds[4] == lost_query(6)");
	check(cmds != NULL && cmds[5].name == NULL, "cmds 表以零条目终止");
	{
		int i, bound = 1;
		for(i = 0; i < 5; i++) {
			if(cmds[i].function == NULL || cmds[i].fixup == NULL
					|| cmds[i].free_fixup == NULL)
				bound = 0;
		}
		check(cmds != NULL && bound,
				"cmds[0..4] 的 function/fixup/free_fixup 均已绑定");
	}
	deref_fn = cmds ? (int (*)(void *, char *, char *, char *, void *, void *))cmds[2].function
					: NULL;
	if(deref_fn == NULL)
		return 1;

	/* 4) params 表：10 个模块参数（modparam 面） */
	params = (param_export_t *)exports->params;
	check(params != NULL && params[0].name != NULL
					&& strcmp(params[0].name, "exact_type") == 0
					&& params[0].type == PARAM_INT && *(int *)params[0].param_pointer == 0,
			"params[0] == exact_type（PARAM_INT，默认 0）");
	check(params != NULL && params[1].name != NULL
					&& strcmp(params[1].name, "response_time") == 0
					&& params[1].type == PARAM_INT && *(int *)params[1].param_pointer == 0,
			"params[1] == response_time（PARAM_INT，默认 0=emergencyRouting）");
	check(params != NULL && params[2].name != NULL
					&& strcmp(params[2].name, "post_request") == 0
					&& params[2].type == PARAM_INT && *(int *)params[2].param_pointer == 0,
			"params[2] == post_request（PARAM_INT，默认 0）");
	check(params != NULL && params[3].name != NULL
					&& strcmp(params[3].name, "location_type") == 0
					&& params[3].type == PARAM_STR && params[3].param_pointer != NULL
					&& ((str_t *)params[3].param_pointer)->len == 0,
			"params[3] == location_type（PARAM_STR，默认空=mod_init 不归一化）");
	check(params != NULL && params[4].name != NULL
					&& strcmp(params[4].name, "recursion") == 0
					&& params[4].type == PARAM_INT && *(int *)params[4].param_pointer == 1,
			"params[4] == recursion（PARAM_INT，默认 1=允许递归）");
	check(params != NULL && params[5].name != NULL
					&& strcmp(params[5].name, "location_profile") == 0
					&& params[5].type == PARAM_INT,
			"params[5] == location_profile（PARAM_INT）");
	check(params != NULL && params[6].name != NULL
					&& strcmp(params[6].name, "location_3d") == 0
					&& params[6].type == PARAM_INT,
			"params[6] == location_3d（PARAM_INT）");
	check(params != NULL && params[7].name != NULL
					&& strcmp(params[7].name, "verbose") == 0
					&& params[7].type == PARAM_INT,
			"params[7] == verbose（PARAM_INT）");
	check(params != NULL && params[8].name != NULL
					&& strcmp(params[8].name, "geoheader_type") == 0
					&& params[8].type == PARAM_INT,
			"params[8] == geoheader_type（PARAM_INT）");
	check(params != NULL && params[9].name != NULL
					&& strcmp(params[9].name, "geoheader_order") == 0
					&& params[9].type == PARAM_INT,
			"params[9] == geoheader_order（PARAM_INT）");
	check(params != NULL && params[10].name == NULL, "params 表以零条目终止");

	/* 5) mod_init：绑定 http_client API */
	check(exports->init_mod_f != NULL && exports->destroy_mod_f != NULL,
			"init_mod_f / destroy_mod_f 非空（mod_init/destroy）");
	if(exports->init_mod_f != NULL) {
		rc = exports->init_mod_f();
		checkf(rc == 0, "mod_init() 成功（httpc_load_api → bind_http_client → 填充 httpapi）",
				rc == 0 ? "http_client API 已绑定" : "返回非 0");
		check(g_bound_api != NULL && g_bound_api->http_client_query_c == fake_httpc_query_c,
				"模块保存的 httpc_api_t 即消费者提供的绑定函数（指针逐字段比对）");
	}

	/* 6) LocByVal：lost_held_dereference() 全链路（libxml2 组包 + 解析 + pv 回写） */
	g_fparam_idx = 0;
	g_query_calls = 0;
	g_query_status = 200;
	g_response = PIDF_VALUE_RESPONSE;
	g_pv_pidf[0] = '\0';
	g_pv_err[0] = '\0';

	rc = deref_fn(NULL, "url", "rtime", "rtype", &pidf_spec, &err_spec);
	checkf(rc == LOST_SUCCESS + 2,
			"LocByVal：返回值 == 202（200 + HELD_RESPONSE_VALUE=2）", "实际 rc");
	printf("       rc=%d（期望 202）\n", rc);
	checkf(g_query_calls == 1, "经 http_client_query_c 投递一次", "投递计数");
	checkf(strcmp(g_uri, "https://lis.example.com/held") == 0,
			"投递 URL == get_str_fparam 提供的 dereference url", g_uri);
	checkf(strcmp(g_ctype, "application/held+xml;charset=utf-8") == 0,
			"Content-Type == application/held+xml;charset=utf-8（模块内 mtheld）", g_ctype);
	check(strstr(g_hdrs, "application/pidf+xml") != NULL,
			"Accept 头含 application/pidf+xml（模块内 ACCEPT_HDR）");
	check(strstr(g_post, "<locationRequest") != NULL,
			"POST 正文为 HELD locationRequest（libxml2 组包产物）");
	check(strstr(g_post, "urn:ietf:params:xml:ns:geopriv:held") != NULL,
			"locationRequest 带 held 命名空间");
	check(strstr(g_post, "responseTime=\"5\"") != NULL,
			"POST 正文带 responseTime=\"5\"（取自第 2 个脚本参数的毫秒数）");
	check(strstr(g_post, ">geodetic locationURI</locationType>") != NULL,
			"locationType 内容为归一化后的 geodetic locationURI");
	check(g_pv_pidf_calls == 1 && strstr(g_pv_pidf, "<presence") != NULL,
			"pidf 伪变量收到原始 HELD/PIDF 响应体");
	check(g_pv_err_calls == 1 && g_pv_err[0] == '\0',
			"err 伪变量收到空串（无错误码）");

	/* 7) LocByRef：presence + locationURI → 201 */
	g_fparam_idx = 0;
	g_query_calls = 0;
	g_response = PIDF_REFERENCE_RESPONSE;
	rc = deref_fn(NULL, "url", "rtime", "rtype", &pidf_spec, &err_spec);
	checkf(rc == LOST_SUCCESS + 1,
			"LocByRef：返回值 == 201（200 + HELD_RESPONSE_REFERENCE=1）", "实际 rc");
	printf("       rc=%d（期望 201）\n", rc);

	/* 8) 非法根元素：presence/locationResponse/error 三者皆非 → 400 */
	g_fparam_idx = 0;
	g_response = XML_BAD_ROOT;
	rc = deref_fn(NULL, "url", "rtime", "rtype", &pidf_spec, &err_spec);
	checkf(rc == LOST_CLIENT_ERROR, "根元素不在 HELD 允许集合内时返回 400", "实际 rc");
	printf("       rc=%d（期望 400）\n", rc);

	/* 9) HTTP 非 2xx：解析前即拒绝 → 400 */
	g_fparam_idx = 0;
	g_response = PIDF_VALUE_RESPONSE;
	g_query_status = 404;
	rc = deref_fn(NULL, "url", "rtime", "rtype", &pidf_spec, &err_spec);
	checkf(rc == LOST_CLIENT_ERROR, "http_client 返回 404 时返回 400（解析前拒绝）",
			"实际 rc");
	printf("       rc=%d（期望 400）\n", rc);

	/* 10) 空响应体：dereferencing location failed → 400 */
	g_fparam_idx = 0;
	g_query_status = 200;
	g_response = "";
	rc = deref_fn(NULL, "url", "rtime", "rtype", &pidf_spec, &err_spec);
	checkf(rc == LOST_CLIENT_ERROR, "响应体为空时返回 400", "实际 rc");

	check(g_log_msgs > 0, "日志桩被真实调用（模块的 LM_ERR/LM_WARN 路径已执行）");

	if(exports->destroy_mod_f != NULL)
		exports->destroy_mod_f();
	dlclose(handle);

	printf("\n== 结果：%d passed, %d failed ==\n", g_pass, g_fail);
	printf("== %s ==\n", g_fail == 0 ? "ALL E2E CHECKS PASSED" : "E2E CHECKS FAILED");
	return g_fail == 0 ? 0 : 1;
}
/* e2e_consumer.c — kamailio-slack 打包产物的消费者端 E2E（层 2，真实执行）。
 *
 * 角色：扮演 kamailio 核心（最小桩实现），按 kamailio 真实加载次序消费 slack.so：
 *
 *   1. dlopen(RTLD_NOW)          —— 等价 loadmodule 第一步：所有未定义符号必须可解析
 *   2. dlsym("exports")          —— 校验 module_exports 描述符与 cmds/params 表内容
 *   3. mod_register()            —— 等价 KEMI 注册：校验 slack.slack_send 条目
 *   4. exports.init_mod_f()      —— 等价 mod_init：绑定 http_client API（bind_http_client）
 *                                  + 申请私有内存（pkg_malloc）
 *   5. params[0] 回调            —— modparam("slack","slack_url",...) 的 URL 校验分支
 *   6. cmds[0] 全链路            —— fixup → pv 渲染 → BODY_FMT 组包 → http_client_query
 *                                  → 校验投递 URI/正文/返回码（成功与失败两分支）
 *
 * 桩符号集来自实测 UI 列表：nm -D -u slack.so（见 MANIFEST.yml 的说明）。
 * 私有内存管理器桩必须与 sag.so 编译时的 sr_pkg_api_t 字段序一致：
 *   mname, mem_pool, mem_block, xmalloc, xmallocxz, xrealloc, xreallocxf, xfree, ...
 * （slack.so 的 pkg_malloc 展开为 _pkg_root.xmalloc(_pkg_root.mem_block, size)）
 *
 * 用法：e2e_consumer <slack.so 绝对路径>
 * 退出码：0 = 全部通过；1 = 存在失败项。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ────────────── kamailio 核心结构（布局对齐 slack.so 编译期头文件） ────────────── */

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

typedef struct
{
	str_t mname;
	str_t fname;
	int rtype;
	void *func;
	int ptypes[6];
} sr_kemi_t;

/* http_client 模块导出的 API（modules/http_client/curl_api.h） */
typedef struct
{
	void *http_connect;
	int (*http_client_query)(void *msg, char *url, str_t *dst, char *post, char *hdrs);
	void *http_client_query_c;
	void *http_connection_exists;
	void *http_get_content_type;
} httpc_api_t;

#define PARAM_USE_FUNC (1U << (8 * sizeof(int) - 1))

/* ────────────── 私有内存管理器桩（_pkg_root） ──────────────
 * 非 DBG 构建下调用形态为 2 参：(mem_block, size)；此处声明 6 参以兼容
 * DBG_SR_MEMORY 形态（多出的参数在 AArch64 ABI 下位于 x2..x5，被忽略）。 */
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

/* 核心日志/全局变量桩（slack.so 的数据符号，必须由消费者提供）。
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

static void stub_km_log(int level, const char *fmt, ...)
{
	(void)level;
	(void)fmt;
}

static void stub_ksr_slog(ksr_logdata_t *ld, const char *fmt, ...)
{
	(void)ld;
	(void)fmt;
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
/* 数组留出前置保护：核心可能以 level（L_ERR=-1 等）直接索引 */
struct log_level_info _e2e_log_level_pad[8];
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

/* ────────────── http_client 侧桩：记录模块投递的 URI/正文/返回码 ────────────── */

static int g_query_calls = 0;
static int g_query_status = 200;
static char g_uri[512];
static char g_body[2048];

static int fake_httpc_query(
		void *msg, char *url, str_t *dst, char *post, char *hdrs)
{
	(void)msg;
	(void)hdrs;
	g_query_calls++;
	snprintf(g_uri, sizeof(g_uri), "%s", url ? url : "");
	snprintf(g_body, sizeof(g_body), "%s", post ? post : "");
	if(dst) {
		/* http_client 的响应体由被调方按 pkg 内存分配，调用方 pkg_free；
		 * 故此处必须经同一管理器分配，否则 slack_free_str 会 free 静态串而崩溃。 */
		char *body = (char *)malloc(3);
		if(body == NULL)
			return -1;
		memcpy(body, "ok", 3);
		dst->s = body;
		dst->len = 2;
	}
	return g_query_status;
}

/* find_export("bind_http_client") 返回的绑定函数：把桩 API 灌进模块的 httpc_api_t */
static int fake_bind_httpc(httpc_api_t *api)
{
	api->http_connect = NULL;
	api->http_client_query = fake_httpc_query;
	api->http_client_query_c = NULL;
	api->http_connection_exists = NULL;
	api->http_get_content_type = NULL;
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

/* ────────────── pv（伪变量）侧桩：把待发送文本渲染进 _slmsg_buf ────────────── */

#define E2E_TEXT "e2e-consumer-message"

int pv_parse_format(str_t *in, void **out)
{
	if(!in || !in->s || in->len <= 0)
		return -1;
	*out = (void *)in->s;
	return 0;
}

int pv_printf(void *msg, void *list, char *buf, int *len)
{
	(void)msg;
	(void)list;
	snprintf(buf, *len, "%s", E2E_TEXT);
	*len = (int)strlen(buf);
	return 0;
}

int pv_printf_s(void *msg, void *list, str_t *out)
{
	(void)msg;
	(void)list;
	if(out) {
		out->s = (char *)E2E_TEXT;
		out->len = (int)strlen(E2E_TEXT);
	}
	return 0;
}

void pv_elem_free_all(void *p)
{
	(void)p;
}

/* ────────────── KEMI 注册桩：捕获 mod_register 提交的导出表 ────────────── */

static sr_kemi_t *g_kemi = NULL;

int sr_kemi_modules_add(sr_kemi_t *klist)
{
	g_kemi = klist;
	return 0;
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

/* ────────────── 消费场景 ────────────── */

#define WEBHOOK_OK "https://hooks.slack.com/services/T00000000/B00000000/e2eXXXX"
#define WEBHOOK_BAD_HOST "https://example.com/services/hook"
/* 前缀合法但总长 > SLACK_URL_MAX_SIZE(128)，用于命中超长拒绝分支 */
#define WEBHOOK_TOO_LONG \
	"https://hooks.slack.com/services/T00000000/B00000000/" \
	"0123456789012345678901234567890123456789012345678901234567890123456789" \
	"0123456789012345678901234567890123456789012345678901234567890123456789"

int main(int argc, char **argv)
{
	void *handle;
	module_exports_t *exports;
	cmd_export_t *cmds;
	param_export_t *params;
	int (*mod_register)(char *, int *, void *, void *);
	int dlflags = 0;
	char *module_version = NULL;
	int (*url_param)(unsigned int, void *);
	char *arg;
	void *fixed = NULL;
	int rc;
	int (*send_fn)(void *, char *, char *);
	int (*fixup_fn)(void **, int);
	int (*fixup_free_fn)(void **, int);

	if(argc < 2) {
		printf("[FAIL] 用法: e2e_consumer <slack.so>\n");
		return 1;
	}
	setbuf(stdout, NULL); /* 逐行输出：崩溃时也能定位到具体检查项 */

	/* 私有内存管理器：模块的 pkg_malloc/pkg_free 直接作用于该结构 */
	_pkg_root.mname = (char *)"e2e-stub";
	_pkg_root.mem_block = NULL;
	_pkg_root.xmalloc = stub_alloc;
	_pkg_root.xmallocxz = stub_alloc0;
	_pkg_root.xfree = stub_free;

	printf("== kamailio-slack 消费者 E2E（dlopen 真实加载） ==\n");
	printf("module: %s\n\n", argv[1]);

	/* 1) 等价 loadmodule 第一步：加载并解析全部未定义符号 */
	handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
	if(handle == NULL) {
		printf("[FAIL] dlopen(RTLD_NOW) 失败：%s\n", dlerror());
		g_fail++;
		printf("\n== 结果：%d passed, %d failed ==\n", g_pass, g_fail);
		printf("== CHECKS FAILED ==\n");
		return 1;
	}
	check(1, "dlopen(RTLD_NOW) 成功（未定义符号全部可解析，等价 loadmodule）");

	/* 2) dlsym：核心按名解析的入口符号 */
	exports = (module_exports_t *)dlsym(handle, "exports");
	check(exports != NULL, "dlsym(\"exports\") 解析模块描述符");
	mod_register = (int (*)(char *, int *, void *, void *))dlsym(
			handle, "mod_register");
	check(mod_register != NULL, "dlsym(\"mod_register\") 解析 KEMI 注册入口");
	module_version = (char *)dlsym(handle, "module_version");
	check(module_version != NULL, "dlsym(\"module_version\") 解析模块版本符号");
	if(exports == NULL)
		return 1;

	checkf(exports->name != NULL && strcmp(exports->name, "slack") == 0,
			"module_exports.name == \"slack\"",
			exports->name ? exports->name : "(null)");

	/* 3) cmds 表：脚本侧 slack_send() */
	cmds = (cmd_export_t *)exports->cmds;
	check(cmds != NULL && cmds[0].name != NULL
					&& strcmp(cmds[0].name, "slack_send") == 0,
			"cmds[0].name == \"slack_send\"（脚本侧入口）");
	checkf(cmds != NULL && cmds[0].param_no == 1,
			"cmds[0].param_no == 1（单参数 text）",
			cmds ? "实测见左侧 cmds[0]" : "cmds 为空");
	check(cmds != NULL && cmds[0].function != NULL && cmds[0].fixup != NULL
					&& cmds[0].free_fixup != NULL,
			"cmds[0] 的 function/fixup/free_fixup 均已绑定");
	check(cmds != NULL && cmds[1].name == NULL, "cmds 表以零条目终止");
	send_fn = cmds ? (int (*)(void *, char *, char *))cmds[0].function : NULL;
	fixup_fn = cmds ? (int (*)(void **, int))cmds[0].fixup : NULL;
	fixup_free_fn = cmds ? (int (*)(void **, int))cmds[0].free_fixup : NULL;
	if(send_fn == NULL || fixup_fn == NULL || fixup_free_fn == NULL)
		return 1;

	/* 4) params 表：slack_url / channel / username / icon_emoji
	 * PARAM_STRING 型参数的 param_pointer 指向模块内的 char* 变量（char**），
	 * 与脚本侧 modparam 赋值语义一致；此处解引用取当前值。 */
	params = (param_export_t *)exports->params;
	check(params != NULL && params[0].name != NULL
					&& strcmp(params[0].name, "slack_url") == 0
					&& (params[0].type & PARAM_USE_FUNC) != 0,
			"params[0] == slack_url（PARAM_USE_FUNC 回调型）");
	check(params != NULL && params[1].name != NULL
					&& strcmp(params[1].name, "channel") == 0
					&& params[1].param_pointer != NULL
					&& *(char **)params[1].param_pointer != NULL
					&& strcmp(*(char **)params[1].param_pointer, "#webtest") == 0,
			"params[1] == channel（默认值 #webtest 可解析）");
	check(params != NULL && params[2].name != NULL
					&& strcmp(params[2].name, "username") == 0
					&& params[2].param_pointer != NULL
					&& *(char **)params[2].param_pointer != NULL
					&& strcmp(*(char **)params[2].param_pointer, "webhookbot") == 0,
			"params[2] == username（默认值 webhookbot 可解析）");
	check(params != NULL && params[3].name != NULL
					&& strcmp(params[3].name, "icon_emoji") == 0
					&& params[3].param_pointer != NULL
					&& *(char **)params[3].param_pointer != NULL
					&& strcmp(*(char **)params[3].param_pointer, ":ghost:") == 0,
			"params[3] == icon_emoji（默认值 :ghost: 可解析）");
	check(params != NULL && params[4].name == NULL, "params 表以零条目终止");
	url_param = params ? (int (*)(unsigned int, void *))params[0].param_pointer
					   : NULL;

	/* 5) mod_register：KEMI slack.slack_send 条目 */
	if(mod_register != NULL) {
		int krc = mod_register(NULL, &dlflags, NULL, NULL);
		checkf(krc == 0, "mod_register() 返回 0", "已提交 KEMI 导出表");
		check(g_kemi != NULL && g_kemi->mname.s != NULL
					  && strcmp(g_kemi->mname.s, "slack") == 0
					  && strcmp(g_kemi->fname.s, "slack_send") == 0,
				"KEMI 条目 slack.slack_send 已注册");
		check(g_kemi != NULL && g_kemi->rtype == 1 /* SR_KEMIP_INT */
					  && g_kemi->ptypes[0] == 2 /* SR_KEMIP_STR */
					  && g_kemi->ptypes[1] == 0 && g_kemi->func != NULL,
				"KEMI 条目签名 rtype=INT / ptypes[0]=STR / 函数指针非空");
		check(g_kemi != NULL && g_kemi[1].fname.s == NULL,
				"KEMI 导出表以零条目终止");
	}

	/* 6) mod_init：绑定 http_client API + 申请私有内存 */
	check(exports->init_mod_f != NULL && exports->destroy_mod_f != NULL,
			"init_mod_f / destroy_mod_f 非空（mod_init/mod_destroy）");
	if(exports->init_mod_f != NULL) {
		rc = exports->init_mod_f();
		checkf(rc == 0, "mod_init() 成功（bind_http_client 绑定 + pkg_malloc）",
				rc == 0 ? "http_client API 已绑定" : "返回非 0");
	}

	/* 7) slack_url 参数校验：正例 + 两个反例 */
	if(url_param != NULL) {
		rc = url_param(PARAM_USE_FUNC, (void *)WEBHOOK_OK);
		checkf(rc == 0, "modparam slack_url 接受合法 webhook URL", WEBHOOK_OK);
		rc = url_param(PARAM_USE_FUNC, (void *)WEBHOOK_BAD_HOST);
		check(rc != 0, "modparam slack_url 拒绝非 hooks.slack.com 域名");
		rc = url_param(PARAM_USE_FUNC, (void *)WEBHOOK_TOO_LONG);
		check(rc != 0, "modparam slack_url 拒绝超长 URL（>128 字节）");
	}

	/* 8) slack_send() 全链路：fixup → pv 渲染 → http_client_query */
	arg = strdup(E2E_TEXT);
	fixed = arg;
	rc = fixup_fn(&fixed, 1);
	checkf(rc == 0 && fixed != NULL && fixed != (void *)arg,
			"cmds[0].fixup 解析参数并转为 sl_msg_t", "fixup 返回 0");

	g_query_status = 200;
	rc = send_fn(NULL, (char *)fixed, NULL);
	checkf(rc == 0 && g_query_calls == 1,
			"slack_send() 走通 http_client_query 并返回 0（HTTP 200）",
			g_query_status == 200 ? "投递成功" : "状态异常");
	checkf(strcmp(g_uri, WEBHOOK_OK) == 0,
			"投递 URI == modparam 配置的 slack_url", g_uri);
	check(strstr(g_body, "\"channel\": \"#webtest\"") != NULL,
			"BODY_FMT 组包含 channel 默认值 #webtest");
	check(strstr(g_body, "\"username\": \"webhookbot\"") != NULL,
			"BODY_FMT 组包含 username 默认值 webhookbot");
	check(strstr(g_body, "\"text\": \"" E2E_TEXT "\"") != NULL,
			"BODY_FMT 组包含 pv 渲染出的待发送文本");
	check(strstr(g_body, "\"icon_emoji\": \":ghost:\"") != NULL,
			"BODY_FMT 组包含 icon_emoji 默认值 :ghost:");

	g_query_status = 404;
	rc = send_fn(NULL, (char *)fixed, NULL);
	checkf(rc != 0, "http_client 返回 404 时 slack_send() 返回错误",
			"失败分支被正确识别");

	rc = fixup_free_fn(&fixed, 1);
	check(rc == 0, "cmds[0].free_fixup 释放在途参数");

	if(exports->destroy_mod_f != NULL)
		exports->destroy_mod_f();
	dlclose(handle);

	printf("\n== 结果：%d passed, %d failed ==\n", g_pass, g_fail);
	printf("== %s ==\n", g_fail == 0 ? "ALL E2E CHECKS PASSED" : "E2E CHECKS FAILED");
	return g_fail == 0 ? 0 : 1;
}

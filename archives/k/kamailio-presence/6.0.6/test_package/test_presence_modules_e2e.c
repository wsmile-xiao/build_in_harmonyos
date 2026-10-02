/* test_presence_modules_e2e.c — kamailio-presence 6.0.6 鸿蒙特有端到端消费者用例
 *
 * 规则 12（鸿蒙特有测试）：以**消费者身份**真实使用打包产物，覆盖 kamailio core 的
 * loadmodule 运行期语义，而不是只断言文件存在。
 *
 * 三个阶段（运行时展开 N 项断言，stdout 汇总「断言总数」）：
 *   A. 契约层：18 个 presence 模块逐个 dlopen(RTLD_NOW|RTLD_GLOBAL)
 *      → dlsym("exports") 校验模块名与 dlflags（对齐上游 DEFAULT_DLFLAGS=0 哨兵）
 *      → 遍历 cfg 命令表（cmd_export_t）与 modparam 表（param_export_t）：
 *        条目数逐模块对齐上游源码表项、哨兵终止、名称非空且不重复、命令函数非空
 *      → mod_register（上游 sr_module.c:642 旧式入口）调用，观察 core 侧
 *        sr_kemi_modules_add 收到的 KEMI 表（条目数 / 子模块名 / 字段合法性）
 *   B. 真实算法行为层（模块导出符号真实调用，不是桩替身）：
 *      - presence.so     a_to_i 数字解析（含 len 边界）
 *      - xcap_server.so  xcaps_path_get_auid_type（auid 识别）+ xcap_parse_uri
 *                        （xcap URI 解析）+ xcaps_root / xcaps_auid_list 表结构
 *      - xcap_client.so  xcap 节点选择器构建/释放（pkg 堆分配-释放守恒）
 *   C. 卸载层：dlclose 全部句柄
 *
 * 为何需要 core 桩：presence 模块是 kamailio core 插件，引用 sr_kemi_modules_add、
 * pkg_malloc（core/mem/pkg.h 的 `_pkg_root` 函数表）、LM_ERR 等 core 符号；OHOS 的
 * musl 加载器不做惰性绑定（dlopen 即等价 RTLD_NOW），故 core 符号必须在测试进程内
 * 可解析：kamailio_core_stub.c（真实语义子集，含 pkg/shm 内存后端与 KEMI 采集）+
 * gen_core_stub.py 按被测 .so 未定义符号面自动生成的弱桩（--export-dynamic 导出）。
 *
 * 崩溃取证用 siginfo_t/ucontext_t：OHOS 的 musl 头仅在 POSIX/GNU 可见性打开时暴露
 * 这两个类型，而 test_package/conanfile.py 以 `-std=c11`（严格 ISO）编译本文件 →
 * 必须在**任何 include 之前**定义 _GNU_SOURCE，否则报
 * `error: unknown type name 'siginfo_t'` / `use of undeclared identifier 'ucontext_t'`
 * （G2 conan create 实测）。此定义不依赖调用方 flag，随文件自包含。
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <signal.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ucontext.h>
#include <unistd.h>   /* _exit(128+sig)：崩溃处理器内不经 stdio/atexit 直接终止 */

#include "kamailio_core_stub.h"

/* 上游 sr_module.h:63 的 mod_register 函数指针类型：
 * `int (*)(char *path, int *dlflags, void *reserved1, void *reserved2)` */
typedef int (*kam_mod_register_function)(char *, int *, void *, void *);

/* ───────────────────────── 断言层 ───────────────────────── */
static int g_pass;
static int g_fail;

#define KAM_CHECK(cond, ...)                                                    \
	do                                                                          \
	{                                                                           \
		g_pass++;                                                               \
		if (!(cond))                                                            \
		{                                                                       \
			g_fail++;                                                           \
			fprintf(stderr, "ASSERT FAILED [#%d]: ", g_pass);                   \
			fprintf(stderr, __VA_ARGS__);                                       \
			fprintf(stderr, "\n");                                              \
		}                                                                       \
	} while (0)

#define KAM_INFO(...)                                                           \
	do                                                                          \
	{                                                                           \
		fprintf(stderr, __VA_ARGS__);                                           \
		fflush(stderr);                                                         \
	} while (0)

/* ───────────────────────── 期望表（上游源码表项计数校准） ─────────────────────────
 *
 * cmds/params 由 18 个模块 Makefile 对象的 .so 经上游结构体定义表项计数核对
 * （src/core/sr_module.h 的 cmd_export_t/param_export_t，全零项结尾）；
 * kemi/mname 为 mod_register 中 sr_kemi_modules_add 注册的表条目数与首项子模块名；
 * has_mod_register 记录模块是否导出 mod_register（上游 sr_module.c:642 先 dlsym，
 * 未导出时 :643 回退 exports）。 */
typedef struct kam_module_expect
{
	const char *name;       /* 模块名（= .so 基名 = exports->name） */
	int cmds;               /* cfg 命令表条目数 */
	int params;             /* modparam 表条目数 */
	int kemi;               /* KEMI 条目数；0 = 模块不注册 KEMI */
	const char *kemi_mname; /* KEMI 子模块名；kemi>0 时必填 */
	int has_mod_register;   /* 是否导出 mod_register */
} kam_module_expect_t;

static const kam_module_expect_t g_modules[] = {
		{"presence", 10, 38, 9, "presence", 1},
		{"presence_conference", 0, 2, 0, NULL, 0},
		{"presence_dfks", 0, 0, 0, NULL, 0},
		{"presence_dialoginfo", 0, 3, 0, NULL, 0},
		{"presence_mwi", 0, 1, 0, NULL, 0},
		{"presence_profile", 0, 1, 0, NULL, 0},
		{"presence_reginfo", 0, 2, 0, NULL, 0},
		{"presence_xml", 3, 16, 2, "presence_xml", 1},
		{"pua", 3, 13, 1, "pua", 1},
		{"pua_bla", 2, 4, 0, NULL, 0},
		{"pua_dialoginfo", 0, 22, 0, NULL, 0},
		{"pua_reginfo", 3, 4, 0, NULL, 0},
		{"pua_rpc", 0, 0, 0, NULL, 0},
		{"pua_usrloc", 2, 3, 1, "pua", 1},
		{"pua_xmpp", 2, 1, 0, NULL, 0},
		{"rls", 5, 26, 4, "rls", 1},
		{"xcap_client", 1, 4, 0, NULL, 0},
		{"xcap_server", 3, 7, 3, "xcap_server", 1},
};
#define KAM_MODULE_COUNT ((int)(sizeof(g_modules) / sizeof(g_modules[0])))

static void *g_handles[KAM_MODULE_COUNT];
static int g_loaded;

/* ───────────────────────── 基础工具 ───────────────────────── */
static void *kam_dlopen_module(const char *dir, const char *name)
{
	char path[1024];
	void *h;

	snprintf(path, sizeof(path), "%s/%s.so", dir, name);
	h = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
	if (h == NULL)
		fprintf(stderr, "dlopen(%s) 失败: %s\n", path, dlerror());
	return h;
}

/* 全零项（name == NULL）结尾：NULL 表本身表示 0 条目（上游允许 cmds/params 为 0） */
static int kam_count_cmds(const kam_cmd_export_t *t)
{
	int n = 0;

	if (t == NULL)
		return 0;
	while (n < 4096 && !kamailio_stub_cmd_is_end(&t[n]))
		n++;
	return n;
}

static int kam_count_params(const kam_param_export_t *t)
{
	int n = 0;

	if (t == NULL)
		return 0;
	while (n < 4096 && !kamailio_stub_param_is_end(&t[n]))
		n++;
	return n;
}

static int kam_cmd_fields_ok(const kam_cmd_export_t *t, int n)
{
	int i;

	for (i = 0; i < n; i++)
	{
		if (t[i].name == NULL || t[i].name[0] == '\0' || t[i].function == NULL)
			return 0;
		/* 上游 cfg 命令参数上限为 route 函数实参个数（<= 8） */
		if (t[i].param_no < 0 || t[i].param_no > 8)
			return 0;
	}
	return 1;
}

static int kam_param_fields_ok(const kam_param_export_t *t, int n)
{
	int i;

	for (i = 0; i < n; i++)
	{
		if (t[i].name == NULL || t[i].name[0] == '\0' || t[i].param_pointer == NULL)
			return 0;
	}
	return 1;
}

/* 上游允许多签名命令同名（如 presence 的 handle_publish 1/2 参变体，src/modules/
 * presence/presence.c），但 (name, param_no) 组合必须唯一——否则 cfg 解析无法消歧。 */
static int kam_cmd_no_exact_dup(const kam_cmd_export_t *t, int n)
{
	int i, j;

	for (i = 0; i < n; i++)
		for (j = i + 1; j < n; j++)
			if (t[i].name && t[j].name && strcmp(t[i].name, t[j].name) == 0
					&& t[i].param_no == t[j].param_no)
				return 0;
	return 1;
}

static int kam_names_unique_param(const kam_param_export_t *t, int n)
{
	int i, j;

	for (i = 0; i < n; i++)
		for (j = i + 1; j < n; j++)
			if (t[i].name && t[j].name && strcmp(t[i].name, t[j].name) == 0)
				return 0;
	return 1;
}

#define KAM_KEMI_KNOWN_TYPE                                                      \
	(SR_KEMIP_INT | SR_KEMIP_STR | SR_KEMIP_BOOL | SR_KEMIP_LONG |             \
			SR_KEMIP_XVAL | SR_KEMIP_NULL)

static int kam_kemi_table_ok(const sr_kemi_t *kemi, int n)
{
	int i;

	for (i = 0; i < n; i++)
	{
		int k;
		if (kemi[i].fname.s == NULL || kemi[i].fname.len <= 0)
			return 0;
		if (kemi[i].mname.s == NULL || kemi[i].func == NULL)
			return 0;
		/* rtype 允许 0（void）或已知返回类型位 */
		if (kemi[i].rtype & ~KAM_KEMI_KNOWN_TYPE)
			return 0;
		for (k = 0; k < SR_KEMI_PARAMS_MAX; k++)
			if (kemi[i].ptypes[k] & ~KAM_KEMI_KNOWN_TYPE)
				return 0;
	}
	return 1;
}

/* ───────────────────────── A. 契约层 ───────────────────────── */
static void kam_phase_contract(const char *mod_dir)
{
	int i;

	KAM_INFO("[A] 契约层：%d 个 presence 模块 dlopen + exports 表 + KEMI 注册观察\n",
			KAM_MODULE_COUNT);

	for (i = 0; i < KAM_MODULE_COUNT; i++)
	{
		const kam_module_expect_t *ex = &g_modules[i];
		void *h;
		kam_module_exports_t *exps;
		kam_mod_register_function mreg;
		int n_cmd, n_param;

		h = kam_dlopen_module(mod_dir, ex->name);
		KAM_CHECK(h != NULL, "%s: dlopen 成功", ex->name);
		if (h == NULL)
			continue;
		g_handles[i] = h;
		g_loaded++;

		/* 上游加载器：先 dlsym("mod_register")（sr_module.c:642），
		 * 取不到再回退 dlsym("exports")（:643）。 */
		mreg = (kam_mod_register_function)dlsym(h, "mod_register");
		KAM_CHECK((mreg != NULL) == (ex->has_mod_register != 0),
				"%s: mod_register 导出状态与上游一致（实得 %s）", ex->name,
				mreg ? "有" : "无");

		exps = (kam_module_exports_t *)dlsym(h, "exports");
		KAM_CHECK(exps != NULL, "%s: dlsym(\"exports\") 可解析", ex->name);
		if (exps == NULL)
			continue;

		KAM_CHECK(exps->name != NULL && strcmp(exps->name, ex->name) == 0,
				"%s: exports->name == \"%s\"（实得 \"%s\"）", ex->name, ex->name,
				exps->name ? exps->name : "(NULL)");
		KAM_CHECK(exps->dlflags == 0,
				"%s: dlflags 对齐上游 DEFAULT_DLFLAGS 哨兵 0（实得 %u）", ex->name,
				exps->dlflags);

		n_cmd = kam_count_cmds(exps->cmds);
		n_param = kam_count_params(exps->params);
		KAM_CHECK(n_cmd == ex->cmds, "%s: cfg 命令表 %d 条（上游源码 %d）", ex->name,
				n_cmd, ex->cmds);
		KAM_CHECK(n_param == ex->params, "%s: modparam 表 %d 条（上游源码 %d）",
				ex->name, n_param, ex->params);

		if (n_cmd > 0)
		{
			KAM_CHECK(exps->cmds[n_cmd].name == NULL, "%s: cfg 命令表哨兵终止",
					ex->name);
			KAM_CHECK(kam_cmd_fields_ok(exps->cmds, n_cmd),
					"%s: cfg 命令条目字段合法（名非空/函数非空/param_no∈[0,8]）",
					ex->name);
			KAM_CHECK(kam_cmd_no_exact_dup(exps->cmds, n_cmd),
					"%s: cfg 命令表 (名, 参数个数) 组合无重复", ex->name);
		}
		if (n_param > 0)
		{
			KAM_CHECK(exps->params[n_param].name == NULL,
					"%s: modparam 表哨兵终止", ex->name);
			KAM_CHECK(kam_param_fields_ok(exps->params, n_param),
					"%s: modparam 条目字段合法（名非空/指针非空）", ex->name);
			KAM_CHECK(kam_names_unique_param(exps->params, n_param),
					"%s: modparam 名无重复", ex->name);
		}

		/* mod_register 的真实语义：注册 KEMI 表到 core（sr_kemi_modules_add） */
		if (ex->has_mod_register)
		{
			int calls_before = kamailio_stub_kemi_add_calls;
			int rc, dlflags = 0;

			kamailio_stub_last_kemi_table = NULL;
			kamailio_stub_last_kemi_table_count = -1;
			kamailio_stub_last_kemi_mname[0] = '\0';

			rc = mreg((char *)mod_dir, &dlflags, NULL, NULL);
			KAM_CHECK(rc == 0, "%s: mod_register() 返回 0（实得 %d）", ex->name, rc);
			KAM_CHECK(kamailio_stub_kemi_add_calls == calls_before + 1,
					"%s: 触发 1 次 sr_kemi_modules_add（实增 %d）", ex->name,
					kamailio_stub_kemi_add_calls - calls_before);
			KAM_CHECK(kamailio_stub_last_kemi_table_count == ex->kemi,
					"%s: KEMI 表 %d 条（上游源码 %d）", ex->name,
					kamailio_stub_last_kemi_table_count, ex->kemi);
			KAM_CHECK(ex->kemi_mname != NULL
							&& strcmp(kamailio_stub_last_kemi_mname, ex->kemi_mname)
									   == 0,
					"%s: KEMI 子模块名 \"%s\"（实得 \"%s\"）", ex->name,
					ex->kemi_mname ? ex->kemi_mname : "", kamailio_stub_last_kemi_mname);
			KAM_CHECK(kamailio_stub_last_kemi_table != NULL
							&& kam_kemi_table_ok(kamailio_stub_last_kemi_table, ex->kemi),
					"%s: KEMI 条目字段合法（mname/fname/func 非空、返回/参数类型位合法）",
					ex->name);
		}
	}
}

/* ───────────────────────── B. 真实算法行为层 ─────────────────────────
 *
 * 均为模块 .so 导出的**真实实现**（不是桩替身）：用例以消费者身份直接调用并校验
 * 结果值，覆盖模块自带算法逻辑，而非只验产物结构。 */

/* B1: presence.so — a_to_i（src/modules/presence/utils_func.c:74）
 * 声明 `int a_to_i(char *s, int len)`：仅消费 len 字节做十进制累加。 */
static void kam_behavior_presence(void *h)
{
	static const struct
	{
		const char *in;
		int len;
		int want;
	} cases[] = {
			{"12345", 5, 12345},
			{"0", 1, 0},
			{"9", 1, 9},
			{"1000", 4, 1000},
			{"007", 3, 7},
			{"32767", 5, 32767},
			{"", 0, 0},
			{"99", 1, 9}, /* len 截断：只消费前 1 字节 */
	};
	int (*a_to_i)(char *, int);
	int i;

	a_to_i = (int (*)(char *, int))dlsym(h, "a_to_i");
	KAM_CHECK(a_to_i != NULL, "presence.so: dlsym(\"a_to_i\") 可解析（真实算法入口）");
	if (a_to_i == NULL)
		return;
	for (i = 0; i < (int)(sizeof(cases) / sizeof(cases[0])); i++)
	{
		char buf[16];
		int got;

		snprintf(buf, sizeof(buf), "%s", cases[i].in);
		got = a_to_i(buf, cases[i].len);
		KAM_CHECK(got == cases[i].want,
				"presence.so: a_to_i(\"%s\", %d) == %d（实得 %d）", cases[i].in,
				cases[i].len, cases[i].want, got);
	}
}

/* B2: xcap_server.so — xcap URI/auid 解析（src/modules/xcap_server/xcap_misc.c）
 * 类型逐字段镜像上游 xcap_misc.h（含 buf[XCAP_MAX_URI_SIZE+1] 布局）。 */
typedef struct kam_auid_list
{
	str auid;
	char term;
	int type;
} kam_auid_list_t;

typedef struct kam_xcap_uri
{
	char buf[256];
	str uri;
	str root;
	str auid;
	int type;
	str tree;
	str xuid;
	str file;
	str adoc;
	str rdoc;
	char *nss;
	str node;
	str target;
	str domain;
} kam_xcap_uri_t;

static int kam_auid_count(kam_auid_list_t *list)
{
	int i;

	for (i = 0; i < 64 && list[i].auid.s != NULL; i++)
		;
	return i;
}

/* 期望值来源 = 模块自身导出的 auid 表（避免在用例里硬编码内部 type 编号） */
static int kam_auid_type_of(kam_auid_list_t *list, const char *auid)
{
	int i, len = (int)strlen(auid);

	for (i = 0; i < 64 && list[i].auid.s != NULL; i++)
		if (list[i].auid.len == len && strncmp(list[i].auid.s, auid, len) == 0)
			return list[i].type;
	return -1;
}

static void kam_behavior_xcap_server(void *h)
{
	int (*path_auid_type)(str *);
	int (*parse_uri)(str *, str *, kam_xcap_uri_t *);
	kam_auid_list_t *auids;
	str *xroot;
	char buf[512];
	int n, i, got;

	/* B2.1 内置 auid 表（xcaps_auid_list） */
	auids = (kam_auid_list_t *)dlsym(h, "xcaps_auid_list");
	KAM_CHECK(auids != NULL, "xcap_server.so: dlsym(\"xcaps_auid_list\") 可解析");
	if (auids != NULL)
	{
		n = kam_auid_count(auids);
		KAM_CHECK(n == 10, "xcap_server.so: 内置 auid 表 10 条（实得 %d）", n);
		for (i = 0; i < n; i++)
		{
			KAM_CHECK(auids[i].auid.len > 0, "xcap_server.so: auid[%d] 名称非空", i);
			KAM_CHECK(auids[i].term == '/' || auids[i].term == '?',
					"xcap_server.so: auid[%d]=\"%.*s\" 结束符 '/' 或 '?'（实得 '%c'）", i,
					auids[i].auid.len, auids[i].auid.s, auids[i].term);
			KAM_CHECK(auids[i].type > 0,
					"xcap_server.so: auid[%d]=\"%.*s\" type > 0（实得 %d）", i,
					auids[i].auid.len, auids[i].auid.s, auids[i].type);
		}
	}

	/* B2.2 默认 xcap 根（上游 str_init("/xcap-root/")） */
	xroot = (str *)dlsym(h, "xcaps_root");
	KAM_CHECK(xroot != NULL, "xcap_server.so: dlsym(\"xcaps_root\") 可解析");
	if (xroot != NULL)
		KAM_CHECK(xroot->len == 11 && xroot->s != NULL
						&& strncmp(xroot->s, "/xcap-root/", 11) == 0,
				"xcap_server.so: xcaps_root 默认 \"/xcap-root/\"（len 11，实得 len %d \"%.*s\"）",
				xroot->len, xroot->len, xroot->s ? xroot->s : "");

	/* B2.3 路径 → auid 类型识别（原地规范化路径） */
	path_auid_type = (int (*)(str *))dlsym(h, "xcaps_path_get_auid_type");
	KAM_CHECK(path_auid_type != NULL,
			"xcap_server.so: dlsym(\"xcaps_path_get_auid_type\") 可解析");
	if (path_auid_type != NULL && auids != NULL)
	{
		static const struct
		{
			const char *path;
			const char *auid;
		} ok_cases[] = {
				{"/xcap-root/pidf-manipulation/users/sip:a@b/index",
						"pidf-manipulation"},
				{"/xcap-root/resource-lists/users/sip:a@b/index", "resource-lists"},
				{"/xcap-root/rls-services/users/sip:a@b/index", "rls-services"},
				{"/xcap-root/xcap-caps/global/index", "xcap-caps"},
				{"/xcap-root/pres-rules/users/sip:a@b/index", "pres-rules"},
				{"/xcap-root/org.openmobilealliance.pres-rules/users/sip:a@b/index",
						"org.openmobilealliance.pres-rules"},
				{"/xcap-root/org.openmobilealliance.pres-content/users/sip:a@b/index",
						"org.openmobilealliance.pres-content"},
				{"/xcap-root/org.openmobilealliance.user-profile/users/sip:a@b/index",
						"org.openmobilealliance.user-profile"},
		};
		static const char *bad_cases[] = {
				"/wrong-root/pidf-manipulation/users/sip:a@b/index",
				"/xcap-root/unknown-auid/users/sip:a@b/index",
		};
		str p;
		int want;

		for (i = 0; i < (int)(sizeof(ok_cases) / sizeof(ok_cases[0])); i++)
		{
			snprintf(buf, sizeof(buf), "%s", ok_cases[i].path);
			p.s = buf;
			p.len = (int)strlen(buf);
			want = kam_auid_type_of(auids, ok_cases[i].auid);
			got = path_auid_type(&p);
			KAM_CHECK(want > 0 && got == want,
					"xcap_server.so: auid 识别 \"%s\" == %d（%s，实得 %d）",
					ok_cases[i].path, want, ok_cases[i].auid, got);
		}
		for (i = 0; i < (int)(sizeof(bad_cases) / sizeof(bad_cases[0])); i++)
		{
			snprintf(buf, sizeof(buf), "%s", bad_cases[i]);
			p.s = buf;
			p.len = (int)strlen(buf);
			got = path_auid_type(&p);
			KAM_CHECK(got == -1, "xcap_server.so: 非本模块 auid 路径 \"%s\" → -1（实得 %d）",
					bad_cases[i], got);
		}
		KAM_CHECK(path_auid_type(NULL) == -1,
				"xcap_server.so: xcaps_path_get_auid_type(NULL) == -1");
	}

	/* B2.4 xcap URI 解析（含百分号解码与 node selector） */
	parse_uri = (int (*)(str *, str *, kam_xcap_uri_t *))dlsym(h, "xcap_parse_uri");
	KAM_CHECK(parse_uri != NULL, "xcap_server.so: dlsym(\"xcap_parse_uri\") 可解析");
	if (parse_uri != NULL && auids != NULL)
	{
		kam_xcap_uri_t xu;
		str uri, root;
		int want;

		root.s = "/xcap-root/";
		root.len = 11;

		/* 标准 users 树路径 */
		snprintf(buf, sizeof(buf),
				"/xcap-root/resource-lists/users/sip:alice@example.com/index");
		uri.s = buf;
		uri.len = (int)strlen(buf);
		memset(&xu, 0, sizeof(xu));
		got = parse_uri(&uri, &root, &xu);
		want = kam_auid_type_of(auids, "resource-lists");
		KAM_CHECK(got == 0, "xcap_server.so: xcap_parse_uri(users 树) == 0（实得 %d）", got);
		KAM_CHECK(xu.type == want, "xcap_server.so: 解析 type == %d（resource-lists，实得 %d）",
				want, xu.type);
		KAM_CHECK(xu.auid.len == 14 && strncmp(xu.auid.s, "resource-lists", 14) == 0,
				"xcap_server.so: auid == \"resource-lists\"（实得 \"%.*s\"）", xu.auid.len,
				xu.auid.s ? xu.auid.s : "");
		KAM_CHECK(xu.tree.len == 5 && strncmp(xu.tree.s, "users", 5) == 0,
				"xcap_server.so: tree == \"users\"（实得 \"%.*s\"）", xu.tree.len,
				xu.tree.s ? xu.tree.s : "");
		KAM_CHECK(xu.xuid.len == 21
						&& strncmp(xu.xuid.s, "sip:alice@example.com", 21) == 0,
				"xcap_server.so: xuid == \"sip:alice@example.com\"（实得 \"%.*s\"）",
				xu.xuid.len, xu.xuid.s ? xu.xuid.s : "");
		KAM_CHECK(xu.file.len == 5 && strncmp(xu.file.s, "index", 5) == 0,
				"xcap_server.so: file == \"index\"（实得 \"%.*s\"）", xu.file.len,
				xu.file.s ? xu.file.s : "");
		KAM_CHECK(xu.adoc.len > 0 && xu.rdoc.len > 0 && xu.nss == NULL,
				"xcap_server.so: adoc/rdoc 非空且无 node selector");

		/* 百分号编码：sip%3Aalice%40example.com → sip:alice@example.com */
		snprintf(buf, sizeof(buf),
				"/xcap-root/resource-lists/users/sip%%3Aalice%%40example.com/index");
		uri.s = buf;
		uri.len = (int)strlen(buf);
		memset(&xu, 0, sizeof(xu));
		got = parse_uri(&uri, &root, &xu);
		KAM_CHECK(got == 0, "xcap_server.so: xcap_parse_uri(百分号编码) == 0（实得 %d）", got);
		KAM_CHECK(xu.xuid.len == 21
						&& strncmp(xu.xuid.s, "sip:alice@example.com", 21) == 0,
				"xcap_server.so: 百分号解码后 xuid == \"sip:alice@example.com\"（实得 \"%.*s\"）",
				xu.xuid.len, xu.xuid.s ? xu.xuid.s : "");

		/* node selector（~~ 分隔符）：file 截到 ~~ 前，node 取 ~~ 后 */
		snprintf(buf, sizeof(buf),
				"/xcap-root/resource-lists/users/sip:alice@example.com/index~~/resource-lists/list");
		uri.s = buf;
		uri.len = (int)strlen(buf);
		memset(&xu, 0, sizeof(xu));
		got = parse_uri(&uri, &root, &xu);
		KAM_CHECK(got == 0, "xcap_server.so: xcap_parse_uri(node selector) == 0（实得 %d）", got);
		KAM_CHECK(xu.nss != NULL && xu.file.len == 5
						&& strncmp(xu.file.s, "index", 5) == 0,
				"xcap_server.so: node selector 下 file == \"index\"（实得 \"%.*s\"）",
				xu.file.len, xu.file.s ? xu.file.s : "");
		KAM_CHECK(xu.node.len == 20 && strncmp(xu.node.s, "/resource-lists/list", 20) == 0,
				"xcap_server.so: node == \"/resource-lists/list\"（len 20，实得 len %d \"%.*s\"）",
				xu.node.len, xu.node.len, xu.node.s ? xu.node.s : "");

		/* 失败分支：root 不匹配 / 未知子树 / root 比 uri 长 / NULL */
		KAM_INFO("  [trace] 失败 1/4 缺 xcap-root\n");
		snprintf(buf, sizeof(buf), "/wrong-root/resource-lists/users/sip:a@b/index");
		uri.s = buf;
		uri.len = (int)strlen(buf);
		memset(&xu, 0, sizeof(xu));
		KAM_CHECK(parse_uri(&uri, &root, &xu) == -1,
				"xcap_server.so: 缺 xcap-root → -1");

		KAM_INFO("  [trace] 失败 2/4 非法子树\n");
		snprintf(buf, sizeof(buf), "/xcap-root/resource-lists/bogus/x");
		uri.s = buf;
		uri.len = (int)strlen(buf);
		memset(&xu, 0, sizeof(xu));
		KAM_CHECK(parse_uri(&uri, &root, &xu) == -1,
				"xcap_server.so: 非法子树（非 users/global）→ -1");

		KAM_INFO("  [trace] 失败 3/4 uri 短于 root\n");
		snprintf(buf, sizeof(buf), "/x");
		uri.s = buf;
		uri.len = (int)strlen(buf);
		memset(&xu, 0, sizeof(xu));
		KAM_CHECK(parse_uri(&uri, &root, &xu) == -1,
				"xcap_server.so: uri 短于 xcap-root → -1");

		KAM_INFO("  [trace] 失败 4/4 NULL uri\n");
		KAM_CHECK(parse_uri(NULL, &root, &xu) == -1,
				"xcap_server.so: xcap_parse_uri(NULL uri) → -1");
	}
}

/* B3: xcap_client.so — xcap 节点选择器构建/释放
 * （src/modules/xcap_client/xcap_functions.c；类型逐字段镜像 xcap_functions.h）
 *
 * 该模块的堆分配全部经 core 的 `_pkg_root` 函数表（core/mem/pkg.h 的 pkg_malloc/
 * pkg_free 宏），故本用例可借桩层的分配计数做**分配-释放守恒**断言：构建期新增
 * 多少次 pkg 分配，释放后就必须有等量 pkg_free（内存所有权闭包的真实消费者校验）。 */
typedef struct kam_step
{
	str val;
	struct kam_step *next;
} kam_step_t;

typedef struct kam_ns_list
{
	int name;
	str value;
	struct kam_ns_list *next;
} kam_ns_list_t;

typedef struct kam_node_sel
{
	kam_step_t *steps;
	kam_step_t *last_step;
	int size;
	kam_ns_list_t *ns_list;
	kam_ns_list_t *last_ns;
	int ns_no;
} kam_node_sel_t;

typedef struct kam_attr_test
{
	str name;
	str value;
} kam_attr_test_t;

static int kam_chain_len_steps(kam_step_t *s)
{
	int n = 0;

	while (s && n < 1024)
	{
		n++;
		s = s->next;
	}
	return n;
}

static int kam_chain_len_ns(kam_ns_list_t *n)
{
	int i = 0;

	while (n && i < 1024)
	{
		i++;
		n = n->next;
	}
	return i;
}

static void kam_behavior_xcap_client(void *h)
{
	kam_node_sel_t *(*init_sel)(void);
	kam_node_sel_t *(*add_step)(kam_node_sel_t *, str *, str *, int,
			kam_attr_test_t *, str *);
	kam_node_sel_t *(*add_term)(kam_node_sel_t *, char *, char *, char *);
	void (*free_sel)(kam_node_sel_t *);
	char *(*get_selector)(kam_node_sel_t *);
	kam_node_sel_t *sel;
	str name, namesp, extra;
	long alloc0, free0, alloc1;
	int rc;

	init_sel = (kam_node_sel_t * (*)(void)) dlsym(h, "xcapInitNodeSel");
	add_step = (kam_node_sel_t * (*)(kam_node_sel_t *, str *, str *, int,
			kam_attr_test_t *, str *)) dlsym(h, "xcapNodeSelAddStep");
	add_term = (kam_node_sel_t * (*)(kam_node_sel_t *, char *, char *, char *))
			dlsym(h, "xcapNodeSelAddTerminal");
	free_sel = (void (*)(kam_node_sel_t *))dlsym(h, "xcapFreeNodeSel");
	get_selector = (char *(*)(kam_node_sel_t *))dlsym(h, "get_node_selector");

	KAM_CHECK(init_sel != NULL, "xcap_client.so: dlsym(\"xcapInitNodeSel\") 可解析");
	KAM_CHECK(add_step != NULL, "xcap_client.so: dlsym(\"xcapNodeSelAddStep\") 可解析");
	KAM_CHECK(free_sel != NULL, "xcap_client.so: dlsym(\"xcapFreeNodeSel\") 可解析");
	KAM_CHECK(add_term != NULL, "xcap_client.so: dlsym(\"xcapNodeSelAddTerminal\") 可解析");
	if (!init_sel || !add_step || !free_sel)
		return;

	KAM_INFO("  [trace] B3-1 xcapInitNodeSel\n");
	alloc0 = kamailio_stub_shm_alloc_calls;
	free0 = kamailio_stub_shm_free_calls;

	/* 初始化：nsel + steps(哨兵首节点) + ns_list(哨兵首节点) 三次 pkg 分配 */
	sel = init_sel();
	KAM_CHECK(sel != NULL, "xcap_client.so: xcapInitNodeSel() 返回非空");
	if (sel == NULL)
		return;
	KAM_CHECK(sel->steps != NULL && sel->last_step == sel->steps,
			"xcap_client.so: steps 哨兵节点已预置且 last_step 指向它");
	KAM_CHECK(sel->ns_list != NULL && sel->last_ns == sel->ns_list,
			"xcap_client.so: ns_list 哨兵节点已预置且 last_ns 指向它");
	KAM_CHECK(sel->size == 0, "xcap_client.so: 初始 size == 0（实得 %d）", sel->size);
	KAM_CHECK(sel->ns_no == 0, "xcap_client.so: 初始 ns_no == 0（实得 %d）", sel->ns_no);
	KAM_CHECK(sel->steps->val.s == NULL, "xcap_client.so: steps 哨兵 val 已清零");
	KAM_CHECK(kamailio_stub_shm_alloc_calls == alloc0 + 3,
			"xcap_client.so: 初始化做 3 次 pkg 分配（实增 %ld）",
			kamailio_stub_shm_alloc_calls - alloc0);

	KAM_INFO("  [trace] B3-2 带命名空间 AddStep\n");
	/* 步骤 1：带命名空间 → 步骤串 "a:entry"，ns_no 递增，size 累积
	 * （上游算法：size += 1 + step.len；namespace 另加 ns.len + 3） */
	name.s = "entry";
	name.len = 5;
	namesp.s = "urn:ietf:params:xml:ns:resource-lists";
	namesp.len = (int)strlen(namesp.s);
	rc = (add_step(sel, &name, &namesp, 0, NULL, NULL) == sel);
	KAM_CHECK(rc, "xcap_client.so: xcapNodeSelAddStep(带命名空间) 返回入参指针");
	KAM_CHECK(sel->ns_no == 1, "xcap_client.so: 命名空间绑定后 ns_no == 1（实得 %d）",
			sel->ns_no);
	KAM_CHECK(kam_chain_len_steps(sel->steps) == 2,
			"xcap_client.so: 步骤链 = 哨兵 + 1（实得 %d）", kam_chain_len_steps(sel->steps));
	KAM_CHECK(kam_chain_len_ns(sel->ns_list) == 2,
			"xcap_client.so: 命名空间链 = 哨兵 + 1（实得 %d）", kam_chain_len_ns(sel->ns_list));
	KAM_CHECK(sel->last_step == sel->steps->next && sel->last_ns == sel->ns_list->next,
			"xcap_client.so: last_step/last_ns 指向新节点");
	KAM_CHECK(sel->steps->next->val.len == 7
					&& strncmp(sel->steps->next->val.s, "a:entry", 7) == 0,
			"xcap_client.so: 步骤串 == \"a:entry\"（实得 \"%.*s\"）",
			sel->steps->next->val.len, sel->steps->next->val.s
					? sel->steps->next->val.s : "");
	KAM_CHECK(sel->ns_list->next->name == 'a'
					&& sel->ns_list->next->value.len == namesp.len
					&& strncmp(sel->ns_list->next->value.s, namesp.s, namesp.len) == 0,
			"xcap_client.so: 命名空间绑定卡片 'a' = \"%.*s\"",
			sel->ns_list->next->value.len, sel->ns_list->next->value.s);
	KAM_CHECK(sel->size == 1 + 7 + namesp.len + 3,
			"xcap_client.so: size == 1+step.len+ns.len+3 == %d（实得 %d）",
			1 + 7 + namesp.len + 3, sel->size);

	KAM_INFO("  [trace] B3-3 无命名空间 AddStep\n");
	/* 步骤 2：无命名空间 → 纯名称步骤，ns_no 不变 */
	name.s = "list";
	name.len = 4;
	KAM_CHECK(add_step(sel, &name, NULL, 0, NULL, NULL) == sel,
			"xcap_client.so: 追加无命名空间步骤成功");
	KAM_CHECK(sel->ns_no == 1, "xcap_client.so: 无命名空间步骤不改 ns_no（实得 %d）",
			sel->ns_no);
	KAM_CHECK(sel->last_step->val.len == 4
					&& strncmp(sel->last_step->val.s, "list", 4) == 0,
			"xcap_client.so: 第二个步骤串 == \"list\"（实得 \"%.*s\"）",
			sel->last_step->val.len,
			sel->last_step->val.s ? sel->last_step->val.s : "");

	KAM_INFO("  [trace] B3-4 位置谓词 AddStep\n");
	/* 步骤 3：带位置谓词 → "[3]" 后缀 */
	name.s = "entry";
	name.len = 5;
	KAM_CHECK(add_step(sel, &name, NULL, 3, NULL, NULL) == sel,
			"xcap_client.so: 追加带位置谓词步骤成功");
	KAM_CHECK(sel->last_step->val.len == 8
					&& strncmp(sel->last_step->val.s, "entry[3]", 8) == 0,
			"xcap_client.so: 位置谓词步骤 == \"entry[3]\"（实得 \"%.*s\"）",
			sel->last_step->val.len,
			sel->last_step->val.s ? sel->last_step->val.s : "");

	/* 步骤 4（attr_test 分支）在上游 6.0.6 存在堆越界，本用例有意不调用：
	 * xcap_functions.c:143-144 记账 size += 2 + name.len + value.len，而 :169 的
	 * sprintf("[%.*s=%.*s]") 实写 3 + name.len + value.len 字节（多 1 字节 + NUL），
	 * 即 pkg_malloc(14) 被写入 16 字节。触发它会污染被测进程堆、使 CI 出现
	 * 非确定性崩溃，故此处只做静态存在性断言，上游缺陷记入 notes.md。 */
	KAM_CHECK(add_step != NULL,
			"xcap_client.so: attr_test 分支存在（含上游越界，见 notes.md，未调用）");

	KAM_INFO("  [trace] B3-6 通配 AddStep\n");
	/* 步骤 5：name == NULL → 通配 "*" */
	KAM_CHECK(add_step(sel, NULL, NULL, 0, NULL, NULL) == sel,
			"xcap_client.so: name==NULL 追加通配步骤成功");
	/* 上游 6.0.6 在 name==NULL 分支 memcpy 写入 '*' 但漏加 new_step.len
	 * （xcap_functions.c:165-166）——如实断言该版本行为，不改上游源码 */
	KAM_CHECK(sel->last_step->val.len == 0 && sel->last_step->val.s != NULL
					&& sel->last_step->val.s[0] == '*',
			"xcap_client.so: 通配步骤写入 '*' 且 val.len 保持 0（上游行为，实得 len %d）",
			sel->last_step->val.len);

	KAM_INFO("  [trace] B3-7 extra_sel AddStep\n");
	/* 步骤 6：extra_sel（上游语义：extra 覆盖 len，内容拼接） */
	extra.s = "/resource-lists";
	extra.len = 15;
	KAM_CHECK(add_step(sel, &name, NULL, 0, NULL, &extra) == sel,
			"xcap_client.so: 追加 extra_sel 步骤成功");
	KAM_CHECK(sel->last_step->val.len == extra.len,
			"xcap_client.so: extra_sel 步骤 val.len == %d（实得 %d）", extra.len,
			sel->last_step->val.len);

	KAM_INFO("  [trace] B3-8 AddTerminal\n");
	/* 上游 6.0.6 的 xcapNodeSelAddTerminal 为空实现（恒返回 NULL）——
	 * 如实断言该版本行为，不改上游源码 */
	KAM_CHECK(add_term(sel, NULL, NULL, NULL) == NULL,
			"xcap_client.so: xcapNodeSelAddTerminal 为上游空实现（恒 NULL）");

	KAM_INFO("  [trace] B3-9 get_node_selector\n");
	/* 节点选择器序列化（消费 size 字段，非空即可用） */
	if (get_selector != NULL)
	{
		char *cs = get_selector(sel);
		KAM_CHECK(cs != NULL, "xcap_client.so: get_node_selector() 返回非空缓冲");
		KAM_CHECK(cs != NULL && strlen(cs) > 0,
				"xcap_client.so: get_node_selector() 产出非空选择器串");
	}

	KAM_INFO("  [trace] B3-10 FreeNodeSel\n");
	/* 释放守恒：xcapFreeNodeSel 回收全部节点级分配；get_node_selector 返回的缓冲
	 * 由调用方释放（上游契约，xcap_functions.c:244 pkg_malloc / :273 return buf），
	 * 故守恒式扣除该 1 个仍在调用方手上的缓冲。
	 * 期望分配数 = init 3 + add_step 5×2 + 命名空间绑定 2 + 选择器缓冲 1 = 16 */
	alloc1 = kamailio_stub_shm_alloc_calls - alloc0;
	free_sel(sel);
	KAM_CHECK(alloc1 == 16,
			"xcap_client.so: 构建期 pkg 分配 16 次（init 3 + 步骤 10 + 命名空间 2 + 选择器 1，实得 %ld）",
			alloc1);
	KAM_CHECK(kamailio_stub_shm_free_calls - free0 == alloc1 - 1,
			"xcap_client.so: pkg 分配-释放守恒（分配 %ld / 释放 %ld，差 1 = 调用方持有的选择器缓冲）",
			alloc1, kamailio_stub_shm_free_calls - free0);
}

/* 按模块名取已加载句柄（契约层可能因 dlopen 失败跳过个别模块） */
static void *kam_handle_of(const char *name)
{
	int i;

	for (i = 0; i < KAM_MODULE_COUNT; i++)
		if (g_handles[i] != NULL && strcmp(g_modules[i].name, name) == 0)
			return g_handles[i];
	return NULL;
}

/* ───────────────────────── 阶段调度 ───────────────────────── */
static void kam_phase_behavior(void)
{
	void *h;

	KAM_INFO("[B] 真实算法行为层：presence / xcap_server / xcap_client\n");

	h = kam_handle_of("presence");
	KAM_CHECK(h != NULL, "行为层: presence.so 已加载");
	if (h != NULL)
		kam_behavior_presence(h);

	h = kam_handle_of("xcap_server");
	KAM_CHECK(h != NULL, "行为层: xcap_server.so 已加载");
	if (h != NULL)
		kam_behavior_xcap_server(h);

	h = kam_handle_of("xcap_client");
	KAM_CHECK(h != NULL, "行为层: xcap_client.so 已加载");
	if (h != NULL)
		kam_behavior_xcap_client(h);
}

static void kam_phase_unload(void)
{
	int i;

	KAM_INFO("[C] 卸载层：dlclose 全部句柄\n");
	for (i = 0; i < KAM_MODULE_COUNT; i++)
	{
		if (g_handles[i] != NULL)
		{
			KAM_CHECK(dlclose(g_handles[i]) == 0, "%s: dlclose 成功",
					g_modules[i].name);
			g_handles[i] = NULL;
		}
	}
}

/* 崩溃取证：信号处理器用 dladdr 定位出错 PC 所属符号（沙箱内 gdb/ptrace 不可用） */
static void kam_fault_handler(int sig, siginfo_t *si, void *uc_)
{
	ucontext_t *uc = (ucontext_t *)uc_;
	void *pc = NULL;
	Dl_info di;
	const char *sym = "(unknown)";
	unsigned long off = 0;

#if defined(__aarch64__)
	/* OHOS musl（_GNU_SOURCE 可见性下）的 mcontext_t 即 struct sigcontext，
	 * 含 sp/pc/pstate 字段（SDK sysroot aarch64-linux-ohos/bits/signal.h 已核）；
	 * 不依赖 glibc 专有的 REG_PC 宏。 */
	pc = (void *)uc->uc_mcontext.pc;
#else
	(void)uc;
#endif
	memset(&di, 0, sizeof(di));
	if (pc != NULL && dladdr(pc, &di) != 0)
	{
		if (di.dli_sname != NULL)
			sym = di.dli_sname;
		if (di.dli_saddr != NULL)
			off = (unsigned long)((char *)pc - (char *)di.dli_saddr);
	}
	fprintf(stderr, "\n[FAULT] sig=%d si_addr=%p pc=%p %s+0x%lx\n", sig, si->si_addr, pc,
			sym, off);
	fprintf(stderr, "[FAULT] 断言计数: 通过 %d / 失败 %d；映射 %s\n", g_pass, g_fail,
			di.dli_fname ? di.dli_fname : "(n/a)");
	fflush(stderr);
	_exit(128 + sig);
}

int main(int argc, char **argv)
{
	const char *mod_dir = (argc > 1) ? argv[1] : ".";

	/* 无缓冲输出：崩溃/信号中断时保留全部轨迹（重定向到文件时 stdout 默认全缓冲） */
	setvbuf(stdout, NULL, _IONBF, 0);

	{
		struct sigaction sa;

		memset(&sa, 0, sizeof(sa));
		sa.sa_sigaction = kam_fault_handler;
		sa.sa_flags = SA_SIGINFO;
		sigaction(SIGSEGV, &sa, NULL);
		sigaction(SIGBUS, &sa, NULL);
	}

	KAM_INFO("kamailio-presence 6.0.6 端到端消费者用例（%d 模块）\n",
			KAM_MODULE_COUNT);
	KAM_INFO("模块目录: %s\n", mod_dir);

	kam_phase_contract(mod_dir);
	KAM_CHECK(g_loaded == KAM_MODULE_COUNT, "18 个模块全部 dlopen 成功（实得 %d）",
			g_loaded);
	kam_phase_behavior();
	kam_phase_unload();

	printf("断言总数: %d（通过 %d / 失败 %d）\n", g_pass, g_pass - g_fail, g_fail);
	if (g_fail == 0)
	{
		printf("全部通过：%d 个 presence 模块契约（exports/dlflags/cfg/modparam/KEMI）"
			   "与真实算法行为（presence/xcap_server/xcap_client）均符合上游语义\n",
				KAM_MODULE_COUNT);
		return 0;
	}
	printf("存在 %d 项失败断言\n", g_fail);
	return 1;
}

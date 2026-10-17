/*
 * kamailio-debugger 消费者端到端用例（test_package 专用，不依赖 kamailio 源码树）
 *
 * 目的：以「真实的模块消费者」方式走通 debugger.so，而不是只做产物结构断言：
 *   1. dlopen(debugger.so, RTLD_NOW|RTLD_GLOBAL) —— 在 OHOS/musl 下 RTLD_LAZY 等价于
 *      RTLD_NOW（不做惰性绑定），因此这一步同时验证了模块对 core 符号的依赖声明完整、
 *      可被真实消费者进程解析（core 符号由链接进本用例的 kamailio_core_stub.c 提供）；
 *   2. dlsym("exports") 取得模块导出描述符，按 core ABI（cmd_export_t/param_export_t）
 *      重放 core 的加载流程：核对命令表、参数表与生命周期钩子；
 *   3. 调用模块真实 API dbg_init_rpc()，并遍历它交给 core 的 RPC 方法表
 *      （rpc_register_array 记录器），核对 8 个 dbg.* 方法确实注册；
 *   4. 按描述符调用命令处理函数与各 fixup —— 含非法参数的负例，验证真实转换逻辑；
 *   5. 调用 exports.destroy_mod_f（mod_destroy）并核对模块状态（dbg_cfg 被清空）；
 *   6. dlclose。
 *
 * 用法：test_debugger_e2e <debugger.so 路径>
 * 退出码：0 = 全部断言通过；1 = 存在失败断言。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#include "kamailio_core_stub.h"

#define S(x) ((x) ? (x) : "(null)")

/* 期望的 cmd 表（顺序与 debugger_mod.c:85-101 的 cmds[] 一致）：
 * 模块名与参数个数是 core 分派命令的依据，顺序错位会让脚本调用落到错误的原型上。 */
static const char *k_expected_cmds[] = {"dbg_breakpoint", "dbg_pv_dump", "dbg_pv_dump",
		"dbg_pv_dump", "dbg_sip_msg", "dbg_sip_msg", "dbg_sip_msg"};
static const int k_expected_cmd_params[] = {1, 0, 1, 2, 0, 1, 2};
#define N_EXPECTED_CMDS ((int)(sizeof(k_expected_cmds) / sizeof(k_expected_cmds[0])))

/* 期望的 modparam 表（顺序与 debugger_mod.c:103-123 的 params[] 一致）：
 * 19 个配置项里前 11 个是模块自身变量，mod_hash_size/mod_level_mode/mod_facility_mode
 * 指向 default_dbg_cfg（cfg 组），mod_level/mod_facility 是 PARAM_USE_FUNC 处理函数。 */
static const char *k_expected_params[] = {"cfgtrace", "cfgtrace_format", "breakpoint",
		"log_level", "log_facility", "log_prefix", "log_level_name", "log_assign",
		"step_usleep", "step_loops", "mod_hash_size", "mod_level_mode", "mod_level",
		"mod_facility_mode", "mod_facility", "reset_msgid", "cfgpkgcheck", "cfgtest"};
#define N_EXPECTED_PARAMS ((int)(sizeof(k_expected_params) / sizeof(k_expected_params[0])))

/* 期望的 RPC 方法（debugger_api.c:1010 的 dbg_rpc[]） */
static const char *k_expected_rpc[] = {"dbg.bp", "dbg.ls", "dbg.trace",
		"dbg.set_mod_level", "dbg.set_mod_facility", "dbg.get_mod_level",
		"dbg.get_mod_facility", "dbg.reset_msgid"};
#define N_EXPECTED_RPC ((int)(sizeof(k_expected_rpc) / sizeof(k_expected_rpc[0])))

static int g_pass = 0;
static int g_fail = 0;
static int g_skip = 0;

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

/* 按 core 的 fixup_function 原型调用模块导出的 fixup：模块会把转换结果写回 *param */
static int call_fixup(stub_fixup_function_t f, int param_no, char *text, long *out)
{
	void *p = (void *)text;
	int r = f(&p, param_no);

	*out = (long)p;
	return r;
}

/* 从 cmd_export_t 表里取第一条指定名字的命令（同名多条时返回首个匹配） */
static cmd_export_t *find_cmd(cmd_export_t *cmds, const char *name, int param_no)
{
	int i;

	for(i = 0; cmds[i].name != NULL; i++) {
		if(strcmp(cmds[i].name, name) == 0 && cmds[i].param_no == param_no)
			return &cmds[i];
	}
	return 0;
}

int main(int argc, char **argv)
{
	char what[320];
	void *handle;
	module_exports_t *e;
	typedef int (*dbg_init_rpc_t)(void);
	dbg_init_rpc_t dbg_init_rpc;
	int i, n;
	long v1 = 0, v2 = 0, vdbg = 0, verr = 0;
	int r;

	if(argc < 2) {
		fprintf(stderr, "usage: %s <debugger.so>\n", argv[0]);
		return 2;
	}

	printf("== kamailio-debugger 消费者端到端用例 ==\nmodule: %s\n\n", argv[1]);

	/* 1) 加载：musl 不做惰性绑定，全部未定义符号必须在此刻解析完 */
	handle = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
	if(handle == 0) {
		printf("[FAIL] dlopen(RTLD_NOW) 失败：%s\n", dlerror());
		return 1;
	}
	check(1, "dlopen(debugger.so, RTLD_NOW|RTLD_GLOBAL) 成功（core 符号全部解析）");

	/* 2) 导出描述符 */
	e = (module_exports_t *)dlsym(handle, "exports");
	if(e == 0) {
		printf("[FAIL] dlsym(\"exports\") 失败：%s\n", dlerror());
		return 1;
	}
	snprintf(what, sizeof(what), "exports.name == \"debugger\"（实际 \"%s\"）", S(e->name));
	check(e->name != NULL && strcmp(e->name, "debugger") == 0, what);
	/* core 约定：DEFAULT_DLFLAGS == 0 是「由模块加载器使用 kamailio 默认 dlopen 标志」
	 * 的哨兵值（src/core/sr_module.h:188），并非字段未初始化。 */
	snprintf(what, sizeof(what),
			"exports.dlflags == 0（core 约定的默认加载标志哨兵值，实际 %u）", e->dlflags);
	check(e->dlflags == 0, what);
	check(e->cmds != NULL, "exports.cmds 非空（命令表已导出）");
	check(e->params != NULL, "exports.params 非空（modparam 表已导出）");
	check(e->rpc_methods == NULL,
			"exports.rpc_methods == NULL（本模块经 dbg_init_rpc() 注册 RPC）");
	check(e->init_mod_f != NULL, "exports.init_mod_f 非空（mod_init 已挂载）");
	check(e->init_child_f != NULL, "exports.init_child_f 非空（child_init 已挂载）");
	check(e->destroy_mod_f != NULL, "exports.destroy_mod_f 非空（mod_destroy 已挂载）");

	/* 3) 重放 core 的命令表加载：逐条核对名字/参数个数/处理函数/fixup */
	for(i = 0; i < N_EXPECTED_CMDS; i++) {
		if(e->cmds[i].name == NULL) {
			snprintf(what, sizeof(what), "cmds[%d].name == \"%s\"（实际提前终止）", i,
					k_expected_cmds[i]);
			check(0, what);
			continue;
		}
		snprintf(what, sizeof(what), "cmds[%d].name == \"%s\"（实际 \"%s\"）", i,
				k_expected_cmds[i], S(e->cmds[i].name));
		check(strcmp(e->cmds[i].name, k_expected_cmds[i]) == 0, what);
		snprintf(what, sizeof(what), "cmds[%d].param_no == %d（实际 %d）", i,
				k_expected_cmd_params[i], e->cmds[i].param_no);
		check(e->cmds[i].param_no == k_expected_cmd_params[i], what);
		snprintf(what, sizeof(what), "cmds[%d] 处理函数与 fixup 均非空", i);
		check(e->cmds[i].function != NULL && e->cmds[i].fixup != NULL, what);
		snprintf(what, sizeof(what), "cmds[%d].flags 非 0（路由类型可调用）", i);
		check(e->cmds[i].flags != 0, what);
	}
	/* 遍历终止：表以全 0 项结束（core 据此停止注册） */
	n = 0;
	while(e->cmds[n].name != NULL)
		n++;
	snprintf(what, sizeof(what), "cmds[] 以空项终止，共 %d 条命令", n);
	check(e->cmds[n].function == NULL && n == N_EXPECTED_CMDS, what);

	/* 4) 重放 core 的 modparam 表加载 */
	for(i = 0; i < N_EXPECTED_PARAMS; i++) {
		if(e->params[i].name == NULL) {
			snprintf(what, sizeof(what), "params[%d].name == \"%s\"（实际提前终止）", i,
					k_expected_params[i]);
			check(0, what);
			continue;
		}
		snprintf(what, sizeof(what), "params[%d].name == \"%s\"（实际 \"%s\"）", i,
				k_expected_params[i], S(e->params[i].name));
		check(strcmp(e->params[i].name, k_expected_params[i]) == 0, what);
	}
	snprintf(what, sizeof(what), "params[%d] 为终止项，共 %d 个 modparam",
			N_EXPECTED_PARAMS, N_EXPECTED_PARAMS);
	check(e->params[N_EXPECTED_PARAMS].name == NULL
					&& e->params[N_EXPECTED_PARAMS].param_pointer == NULL,
			what);
	n = 0;
	while(e->params[n].name != NULL) {
		if(e->params[n].param_pointer == NULL) {
			snprintf(what, sizeof(what), "params[%d] (%s) 绑定目标非空", n,
					S(e->params[n].name));
			check(0, what);
		}
		n++;
	}
	snprintf(what, sizeof(what), "全部 %d 个 modparam 的绑定目标均非空", n);
	check(n == N_EXPECTED_PARAMS, what);

	/* 5) 真实消费者路径：mod_init 的 RPC 注册（dbg_init_rpc → rpc_register_array） */
	dbg_init_rpc = (dbg_init_rpc_t)dlsym(handle, "dbg_init_rpc");
	if(dbg_init_rpc == 0) {
		printf("[FAIL] dlsym(\"dbg_init_rpc\") 失败：%s\n", dlerror());
		g_fail++;
		return 1;
	}
	r = dbg_init_rpc();
	snprintf(what, sizeof(what), "dbg_init_rpc() 返回 0（实际 %d）", r);
	check(r == 0, what);
	snprintf(what, sizeof(what),
			"rpc_register_array() 被调用 1 次（实际 %d，证明走了 core 注册通道）",
			stub_rpc_register_calls);
	check(stub_rpc_register_calls == 1, what);
	check(stub_rpc_registered_array != NULL, "注册的 RPC 表指针非空");

	if(stub_rpc_registered_array != NULL) {
		rpc_export_t *tbl = (rpc_export_t *)stub_rpc_registered_array;
		for(i = 0; i < N_EXPECTED_RPC; i++) {
			if(tbl[i].name == NULL) {
				snprintf(what, sizeof(what), "rpc[%d].name == \"%s\"（实际提前终止）", i,
						k_expected_rpc[i]);
				check(0, what);
				continue;
			}
			snprintf(what, sizeof(what), "rpc[%d].name == \"%s\"（实际 \"%s\"）", i,
					k_expected_rpc[i], S(tbl[i].name));
			check(strcmp(tbl[i].name, k_expected_rpc[i]) == 0, what);
			snprintf(what, sizeof(what), "rpc[%d] (%s) 处理函数与文档串非空", i,
					k_expected_rpc[i]);
			check(tbl[i].function != NULL && tbl[i].doc_str != NULL, what);
		}
		n = 0;
		while(tbl[n].name != NULL)
			n++;
		snprintf(what, sizeof(what), "rpc[] 以空项终止，共注册 %d 个方法", n);
		check(tbl[n].function == NULL && n == N_EXPECTED_RPC, what);
	}

	/* 6) 真实消费者路径：按描述符调用命令处理函数（core 在脚本路由里就是这么调的） */
	{
		cmd_export_t *c = find_cmd(e->cmds, "dbg_breakpoint", 1);
		if(c == NULL) {
			check(0, "可在命令表中定位 dbg_breakpoint(1)");
		} else {
			r = c->function(NULL, NULL, NULL);
			snprintf(what, sizeof(what),
					"dbg_breakpoint(mode) 处理函数返回 1（实际 %d）", r);
			check(r == 1, what);
		}
	}

	/* 7) 真实消费者路径：fixup 正负例（core 在加载脚本时调用，决定参数是否合法） */
	{
		cmd_export_t *pv =
				find_cmd(e->cmds, "dbg_pv_dump", 2); /* 带 mask+level 的重载 */
		cmd_export_t *sip =
				find_cmd(e->cmds, "dbg_sip_msg", 2); /* 带 level+facility 的重载 */
		cmd_export_t *sip1 = find_cmd(e->cmds, "dbg_sip_msg", 1);

		if(pv == NULL || sip == NULL || sip1 == NULL) {
			check(0, "可在命令表中定位 dbg_pv_dump(2)/dbg_sip_msg(2)/dbg_sip_msg(1)");
		} else {
			/* dbg_pv_dump("31", "L_DBG")：mask 走 str2int，level 取名字第 3 个字符 */
			r = call_fixup(pv->fixup, 1, "31", &v1);
			snprintf(what, sizeof(what),
					"fixup_dbg_pv_dump(mask) 接受 \"31\"（r=%d, mask=%ld）", r, v1);
			check(r == 0 && v1 == 31, what);

			r = call_fixup(pv->fixup, 1, "abc", &v1);
			snprintf(what, sizeof(what),
					"fixup_dbg_pv_dump(mask) 拒绝非法 \"abc\"（r=%d）", r);
			check(r != 0, what);

			r = call_fixup(pv->fixup, 2, "L_DBG", &v2);
			snprintf(what, sizeof(what),
					"fixup_dbg_pv_dump(level) \"L_DBG\" → L_DBG(3)（r=%d, level=%ld）", r, v2);
			check(r == 0 && v2 == 3, what);

			r = call_fixup(pv->fixup, 2, "L_ALERT", &v2);
			snprintf(what, sizeof(what),
					"fixup_dbg_pv_dump(level) \"L_ALERT\" → L_ALERT(-5)（r=%d, level=%ld）",
					r, v2);
			check(r == 0 && v2 == -5, what);

			r = call_fixup(pv->fixup, 2, "L_XX", &v2);
			snprintf(what, sizeof(what),
					"fixup_dbg_pv_dump(level) 拒绝非法 \"L_XX\"（r=%d）", r);
			check(r != 0, what);

			/* dbg_sip_msg(level, facility)：facility 走 core str2facility（shim 实现
			 * 只认 LOG_DAEMON），level 走名字第 3 个字符 + L_OFFSET（L_WARN 被当作空指针，
			 * 故模块统一加偏移）——此处只断言「已转换且不同级别可区分」，不写死 L_OFFSET。 */
			r = call_fixup(sip->fixup, 2, "LOG_DAEMON", &v2);
			snprintf(what, sizeof(what),
					"fixup_dbg_sip_msg(facility) \"LOG_DAEMON\" → 24（r=%d, facility=%ld）", r,
					v2);
			check(r == 0 && v2 == 24, what);

			r = call_fixup(sip->fixup, 2, "BOGUS", &v2);
			snprintf(what, sizeof(what),
					"fixup_dbg_sip_msg(facility) 拒绝非法 \"BOGUS\"（r=%d）", r);
			check(r != 0, what);

			r = call_fixup(sip1->fixup, 1, "L_DBG", &vdbg);
			snprintf(what, sizeof(what),
					"fixup_dbg_sip_msg(level) \"L_DBG\" 转换为非空级别（r=%d, level=%ld）", r,
					vdbg);
			check(r == 0 && vdbg != 0, what);

			r = call_fixup(sip1->fixup, 1, "L_ERR", &verr);
			snprintf(what, sizeof(what),
					"fixup_dbg_sip_msg(level) \"L_ERR\" 转换为非空级别（r=%d, level=%ld）", r,
					verr);
			check(r == 0 && verr != 0, what);
			check(vdbg != verr, "不同级别名被转换为不同级别值（L_DBG != L_ERR）");
		}
	}

	/* 8) 生命周期闭环：core 卸载模块时会调用 destroy_mod_f（mod_destroy） */
	{
		void **cfg_slot = (void **)dlsym(handle, "dbg_cfg");
		if(cfg_slot == NULL) {
			printf("[skip] dlsym(\"dbg_cfg\") 不可见，跳过 destroy 状态断言\n");
			g_skip++;
		} else {
			static int sentinel = 0;
			void (*destroy_f)(void) = (void (*)(void))e->destroy_mod_f;

			*cfg_slot = (void *)&sentinel;
			check(*cfg_slot != NULL, "destroy 前置：dbg_cfg 已被置入哨兵值");
			destroy_f();
			check(*cfg_slot == NULL,
					"destroy_mod_f() 执行后 dbg_cfg == NULL（mod_destroy 真实生效）");
		}
	}

	check(dlclose(handle) == 0, "dlclose(debugger.so) 成功（卸载无残留引用）");

	printf("\n== 结果：%d passed, %d failed, %d skipped ==\n", g_pass, g_fail, g_skip);
	printf("== %s ==\n", g_fail == 0 ? "ALL CHECKS PASSED" : "CHECKS FAILED");
	return g_fail == 0 ? 0 : 1;
}

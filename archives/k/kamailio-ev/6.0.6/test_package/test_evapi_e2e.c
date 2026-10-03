/* test_evapi_e2e.c — kamailio-ev 鸿蒙特有端到端消费者用例
 *
 * 目的（rule12「完整消费者用例」）：在 OHOS 上真实走通 kamailio core 加载并消费
 * evapi 模块的完整路径，而非只做产物静态断言：
 *
 *   dlopen(evapi.so, RTLD_NOW)                ← musl 不做惰性绑定，全部符号须可解析
 *     → dlsym("exports")                        ← module_exports 描述符（loadmodule 读取入口）
 *     → 校验 name=="evapi" / DEFAULT_DLFLAGS / cfg 命令表 9 项 / 参数表 7 项（含指针绑定核验）/ PV 表 1 项
 *     → dlsym("mod_register") → 调用
 *     → 观察 core 侧 sr_kemi_modules_add() 收到的 KEMI 函数表（8 项，名称/返回类型/参数类型）
 *     → 真实调用模块导出函数：
 *         evapi_env_reset()          环境结构复位（conidx=-1）
 *         evapi_init_environment(1)  事件路由解析（桩层记录 3 个路由名）
 *         evapi_set_tag()/evapi_cfg_close() 入参契约（NULL 分支返回 -1）
 *     → 真实调用**运行时依赖** libev（模块 DT_NEEDED=libev.so）：
 *         ev_default_loop() + ev_io_start() + ev_run() + ev_io_stop() 完成一次真实
 *         fd 就绪回调（证明依赖链在目标机可加载且可运行）
 *     → dlclose
 *
 * core 符号由 kamailio_core_stub.c 提供，测试可执行文件以 -Wl,--export-dynamic 导出，
 * 供 dlopen 解析（OHOS/musl 加载器 RTLD_NOW 语义）。
 *
 * 用法：test_evapi_e2e <evapi.so 绝对路径>
 */
#include "kamailio_core_stub.h"

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <ev.h> /* libev：模块的运行时依赖（DT_NEEDED=libev.so） */

/* module_exports 前 6 个字段（src/core/sr_module.h 6.0.6 顺序，与 evapi_mod.c:110-121
 * 的初始化列表逐项对应）：
 *   char *name; int dlflags; cmd_export_t *cmds; param_export_t *params;
 *   rpc_export_t *rpcs; pv_export_t *pvs; ... */
typedef struct
{
	char *name;
	int dlflags;
	void *cmds;
	void *params;
	void *rpcs;
	void *pvs;
} module_exports_head_t;

/* cmd_export_t：name / function / param_no / fixup / free_fixup / flags */
typedef struct
{
	char *name;
	void *function;
	int param_no;
	void *fixup;
	void *free_fixup;
	int flags;
} cmd_export_t;

/* param_export_t：name / type / 目标指针 */
typedef struct
{
	char *name;
	int type;
	void *param_pointer;
} param_export_t;

/* evapi_env_t（src/modules/evapi/evapi_mod.c:70-79） */
typedef struct _evapi_env
{
	int eset;
	int conidx;
	str msg;
	struct _evapi_env *next;
} evapi_env_t;

/* evapi_mod.c:80-91 —— cfg 命令表（9 项 + 全零结尾项），与 param_no 逐项对应 */
static const char *EXPECTED_CMDS[] = {
	"evapi_relay", "evapi_async_relay", "evapi_multicast", "evapi_async_multicast",
	"evapi_unicast", "evapi_async_unicast", "evapi_close", "evapi_close", "evapi_set_tag",
};
static const int EXPECTED_CMD_PARAM_NO[] = {1, 1, 2, 2, 2, 2, 0, 1, 1};
/* evapi_mod.c:93-101 —— 参数表（7 项 + 全零结尾项） */
static const char *EXPECTED_PARAMS[] = {
	"workers", "bind_addr", "netstring_format", "event_callback",
	"max_clients", "wait_idle", "wait_increase",
};
/* evapi_mod.c:828-870 —— KEMI 函数表（8 项 + 全零结尾项） */
static const char *EXPECTED_KEMI[] = {
	"relay", "relay_unicast", "relay_multicast", "close",
	"set_tag", "async_relay", "async_unicast", "async_multicast",
};
/* 各项参数类型（src/modules/evapi/evapi_mod.c:828-870 的 ptypes 初始化） */
static const int EXPECTED_KEMI_PTYPES[][2] = {
	{SR_KEMIP_STR, 0}, {SR_KEMIP_STR, SR_KEMIP_STR}, {SR_KEMIP_STR, SR_KEMIP_STR}, {0, 0},
	{SR_KEMIP_STR, 0}, {SR_KEMIP_STR, 0},   {SR_KEMIP_STR, SR_KEMIP_STR},
	{SR_KEMIP_STR, SR_KEMIP_STR},
};
/* evapi_dispatch.c:evapi_init_environment() 解析的三个事件路由名 */
static const char *EXPECTED_ROUTES[] = {
	"evapi:connection-new", "evapi:connection-closed", "evapi:message-received",
};

/* kamailio 6.0.6 的 DEFAULT_DLFLAGS 是「交回 core 决定实际 dlopen flags」的哨兵值 0
 * （src/core/sr_module.h:188）；故此处断言相等而非不等。 */
#define EVAPI_DEFAULT_DLFLAGS_SENTINEL 0

/* evapi_mod.c:47-56 参数默认值（params[] 的绑定目标初值） */
#define EXPECTED_WORKERS 1
#define EXPECTED_MAX_CLIENTS 8
#define EXPECTED_WAIT_IDLE 500000
#define EXPECTED_WAIT_INCREASE 3
#define EXPECTED_DISPATCHER_PID (-1)

/* 模块参数表的绑定目标（evapi_mod.c 中非 static 的全局量）——由 dlsym 在运行时取得
 * （模块经 dlopen 加载，消费者可执行文件不与其链接）。 */

/* 模块导出函数（evapi_dispatch.h / evapi_mod.c） */
typedef void (*env_reset_fn_t)(evapi_env_t *evenv);
typedef void (*init_env_fn_t)(int dformat);
typedef int (*set_tag_fn_t)(void *msg, str *stag);
typedef int (*cfg_close_fn_t)(void *msg);

/* ---- 真实调用运行时依赖 libev：一次 fd 就绪回调 ---- */
static int libev_cb_fired = 0;
static void libev_io_cb(EV_P_ ev_io *w, int revents)
{
	(void)revents;
	libev_cb_fired = 1;
	ev_break(EV_A_ EVBREAK_ONE);
	(void)w;
}

int main(int argc, char **argv)
{
	if(argc < 2)
	{
		fprintf(stderr, "usage: %s <path/to/evapi.so>\n", argv[0]);
		return 2;
	}
	const char *module_path = argv[1];
	printf("kamailio-ev 鸿蒙端到端消费者用例\n  module=%s\n", module_path);

	/* ---- 1. 加载模块（模拟 kamailio loadmodule，RTLD_NOW = musl 语义） ---- */
	void *handle = dlopen(module_path, RTLD_NOW | RTLD_GLOBAL);
	if(handle == NULL)
	{
		fprintf(stderr, "dlopen failed: %s\n", dlerror());
		return 1;
	}
	KAM_STUB_CHECK(handle != NULL, "dlopen(evapi.so, RTLD_NOW|RTLD_GLOBAL) 成功");

	/* ---- 2. module_exports 描述符：kamailio 加载器读取的第一入口 ---- */
	KAM_STUB_STEP("exports 描述符");
	module_exports_head_t *exports = (module_exports_head_t *)dlsym(handle, "exports");
	KAM_STUB_CHECK(exports != NULL && exports->name != NULL,
			"dlsym(\"exports\") 返回 module_exports 描述符");
	KAM_STUB_CHECK(strcmp(exports->name, "evapi") == 0,
			"exports.name == \"evapi\"（实得 \"%s\"）", exports->name);
	KAM_STUB_CHECK(exports->dlflags == EVAPI_DEFAULT_DLFLAGS_SENTINEL,
			"exports.dlflags == DEFAULT_DLFLAGS 哨兵值 %d（实得 %d）",
			EVAPI_DEFAULT_DLFLAGS_SENTINEL, exports->dlflags);
	KAM_STUB_CHECK(exports->rpcs == NULL, "exports.rpcs == 0（evapi 不导出 RPC）");

	/* ---- 3. cfg 命令表：kamailio 加载时注册的 route 命令 ---- */
	KAM_STUB_STEP("cfg 命令表");
	KAM_STUB_CHECK(exports->cmds != NULL, "cfg 命令表指针非空");
	cmd_export_t *cmds = (cmd_export_t *)exports->cmds;
	int n_cmds = 0;
	while(cmds[n_cmds].name != NULL)
	{
		KAM_STUB_CHECK(cmds[n_cmds].function != NULL,
				"cfg 命令 %s 的函数指针非空", cmds[n_cmds].name);
		n_cmds++;
	}
	KAM_STUB_CHECK(n_cmds == 9, "cfg 命令表条目数 == 9（实得 %d）", n_cmds);
	for(int i = 0; i < n_cmds; i++)
	{
		KAM_STUB_CHECK(strcmp(cmds[i].name, EXPECTED_CMDS[i]) == 0,
				"cfg 命令[%d] == \"%s\"（实得 \"%s\"）", i, EXPECTED_CMDS[i], cmds[i].name);
		KAM_STUB_CHECK(cmds[i].param_no == EXPECTED_CMD_PARAM_NO[i],
				"cfg 命令[%d] %s 参数个数 == %d（实得 %d）", i, EXPECTED_CMDS[i],
				EXPECTED_CMD_PARAM_NO[i], cmds[i].param_no);
	}
	/* 两个 evapi_close 重载（0 参 / 1 参）不带 fixup；其余带 fixup */
	KAM_STUB_CHECK(cmds[6].fixup == NULL && cmds[7].fixup == NULL,
			"evapi_close（0/1 参两个重载）fixup == NULL");
	KAM_STUB_CHECK(cmds[0].fixup != NULL && cmds[1].fixup != NULL && cmds[2].fixup != NULL
					&& cmds[3].fixup != NULL && cmds[4].fixup != NULL
					&& cmds[5].fixup != NULL && cmds[8].fixup != NULL,
			"其余 7 条命令 fixup 指针非空（加载器会调用 fixup 解析参数）");

	/* ---- 4. 参数表：名称 + 绑定目标指针 + 默认值 ---- */
	KAM_STUB_STEP("参数表与绑定目标");
	/* 参数绑定目标所在的模块全局量（evapi_mod.c 非 static 定义，模块动态导出） */
	int *p_workers = (int *)dlsym(handle, "_evapi_workers");
	int *p_max_clients = (int *)dlsym(handle, "_evapi_max_clients");
	int *p_wait_idle = (int *)dlsym(handle, "_evapi_wait_idle");
	int *p_wait_increase = (int *)dlsym(handle, "_evapi_wait_increase");
	int *p_dispatcher_pid = (int *)dlsym(handle, "_evapi_dispatcher_pid");
	str *p_event_callback = (str *)dlsym(handle, "_evapi_event_callback");
	KAM_STUB_CHECK(p_workers != NULL && p_max_clients != NULL && p_wait_idle != NULL
					&& p_wait_increase != NULL && p_dispatcher_pid != NULL
					&& p_event_callback != NULL,
			"dlsym 取得 6 个模块全局量（参数绑定目标）");
	KAM_STUB_CHECK(exports->params != NULL, "参数表指针非空");
	param_export_t *params = (param_export_t *)exports->params;
	int n_params = 0;
	while(params[n_params].name != NULL)
	{
		KAM_STUB_CHECK(params[n_params].param_pointer != NULL,
				"参数 %s 的绑定目标指针非空", params[n_params].name);
		n_params++;
	}
	KAM_STUB_CHECK(n_params == 7, "参数表条目数 == 7（实得 %d）", n_params);
	for(int i = 0; i < n_params; i++)
		KAM_STUB_CHECK(strcmp(params[i].name, EXPECTED_PARAMS[i]) == 0,
				"参数[%d] == \"%s\"（实得 \"%s\"）", i, EXPECTED_PARAMS[i], params[i].name);
	/* 绑定目标必须指向模块内真实全局量 */
	KAM_STUB_CHECK(params[0].param_pointer == (void *)p_workers,
			"参数 workers → &_evapi_workers");
	KAM_STUB_CHECK(params[3].param_pointer == (void *)p_event_callback,
			"参数 event_callback → &_evapi_event_callback");
	KAM_STUB_CHECK(params[4].param_pointer == (void *)p_max_clients,
			"参数 max_clients → &_evapi_max_clients");
	KAM_STUB_CHECK(params[5].param_pointer == (void *)p_wait_idle,
			"参数 wait_idle → &_evapi_wait_idle");
	KAM_STUB_CHECK(params[6].param_pointer == (void *)p_wait_increase,
			"参数 wait_increase → &_evapi_wait_increase");
	/* 默认值（evapi_mod.c:47-57） */
	KAM_STUB_CHECK(*p_workers == EXPECTED_WORKERS,
			"_evapi_workers 默认值 == %d（实得 %d）", EXPECTED_WORKERS, *p_workers);
	KAM_STUB_CHECK(*p_max_clients == EXPECTED_MAX_CLIENTS,
			"_evapi_max_clients 默认值 == %d（实得 %d）", EXPECTED_MAX_CLIENTS,
			*p_max_clients);
	KAM_STUB_CHECK(*p_wait_idle == EXPECTED_WAIT_IDLE,
			"_evapi_wait_idle 默认值 == %d（实得 %d）", EXPECTED_WAIT_IDLE, *p_wait_idle);
	KAM_STUB_CHECK(*p_wait_increase == EXPECTED_WAIT_INCREASE,
			"_evapi_wait_increase 默认值 == %d（实得 %d）", EXPECTED_WAIT_INCREASE,
			*p_wait_increase);
	KAM_STUB_CHECK(*p_dispatcher_pid == EXPECTED_DISPATCHER_PID,
			"_evapi_dispatcher_pid 默认值 == %d（实得 %d）", EXPECTED_DISPATCHER_PID,
			*p_dispatcher_pid);
	KAM_STUB_CHECK(p_event_callback->s == NULL && p_event_callback->len == 0,
			"_evapi_event_callback 默认 STR_NULL（s=NULL, len=0）");

	/* ---- 5. PV 导出表（$evapi(...) 伪变量） ---- */
	KAM_STUB_STEP("PV 导出表");
	KAM_STUB_CHECK(exports->pvs != NULL, "PV 表指针非空");
	pv_export_t *pvs = (pv_export_t *)exports->pvs;
	KAM_STUB_CHECK(pvs[0].name.s != NULL && strcmp(pvs[0].name.s, "evapi") == 0
					&& pvs[0].name.len == 5,
			"PV[0].name == \"evapi\"（len 5）");
	KAM_STUB_CHECK(pvs[0].type == STUB_PVT_OTHER,
			"PV[0].type == PVT_OTHER(%d)（实得 %d）", STUB_PVT_OTHER, pvs[0].type);
	KAM_STUB_CHECK(pvs[0].getf != NULL && pvs[0].setf != NULL && pvs[0].parse_name != NULL,
			"PV[0] getf/setf/parse_name 三个回调均非空");
	KAM_STUB_CHECK(pvs[1].name.s == NULL, "PV 表以全零项结尾（仅 1 项）");

	/* ---- 6. KEMI 注册入口：加载器随后调用 mod_register() ---- */
	KAM_STUB_STEP("mod_register → KEMI 表");
	typedef int (*mod_register_fn_t)(char *path, int *dlflags, void *p1, void *p2);
	mod_register_fn_t mod_register = (mod_register_fn_t)dlsym(handle, "mod_register");
	KAM_STUB_CHECK(mod_register != NULL, "dlsym(\"mod_register\") 非空");
	int dlflags = 0;
	int rc = mod_register((char *)module_path, &dlflags, NULL, NULL);
	KAM_STUB_CHECK(rc == 0, "mod_register() 返回 0（实得 %d）", rc);
	KAM_STUB_CHECK(kamailio_stub_kemi_add_calls == 1,
			"mod_register() 恰好调用 sr_kemi_modules_add() 一次（实得 %d 次）",
			kamailio_stub_kemi_add_calls);

	const sr_kemi_t *table = kamailio_stub_last_kemi_table;
	KAM_STUB_CHECK(table != NULL, "sr_kemi_modules_add() 收到的 KEMI 函数表非空");
	int n_kemi = 0;
	while(!kamailio_stub_is_table_end(&table[n_kemi]))
		n_kemi++;
	KAM_STUB_CHECK(n_kemi == 8, "KEMI 函数表条目数 == 8（实得 %d）", n_kemi);
	for(int i = 0; i < n_kemi; i++)
	{
		KAM_STUB_CHECK(table[i].mname.s != NULL && strcmp(table[i].mname.s, "evapi") == 0
						&& table[i].mname.len == 5,
				"KEMI[%d] 子模块名为 \"evapi\"（KSR.evapi.*）", i);
		KAM_STUB_CHECK(table[i].fname.s != NULL && strcmp(table[i].fname.s, EXPECTED_KEMI[i]) == 0,
				"KEMI[%d] 函数名 == \"%s\"", i, EXPECTED_KEMI[i]);
		KAM_STUB_CHECK(table[i].rtype == SR_KEMIP_INT,
				"KEMI[%d] 返回类型 == SR_KEMIP_INT（实得 %d）", i, table[i].rtype);
		KAM_STUB_CHECK(table[i].func != NULL, "KEMI[%d] 函数指针非空", i);
		KAM_STUB_CHECK(table[i].ptypes[0] == EXPECTED_KEMI_PTYPES[i][0]
						&& table[i].ptypes[1] == EXPECTED_KEMI_PTYPES[i][1]
						&& table[i].ptypes[2] == SR_KEMIP_NONE,
				"KEMI[%d] 参数类型 == (%s,%s,none…)", i,
				EXPECTED_KEMI_PTYPES[i][0] == SR_KEMIP_STR ? "str" : "none",
				EXPECTED_KEMI_PTYPES[i][1] == SR_KEMIP_STR ? "str" : "none");
	}

	/* ---- 7. 真实调用模块导出函数：环境复位 + 事件路由解析 + 入参契约 ---- */
	KAM_STUB_STEP("evapi_env_reset / evapi_init_environment");
	env_reset_fn_t env_reset = (env_reset_fn_t)dlsym(handle, "evapi_env_reset");
	init_env_fn_t init_env = (init_env_fn_t)dlsym(handle, "evapi_init_environment");
	KAM_STUB_CHECK(env_reset != NULL, "dlsym(\"evapi_env_reset\") 非空");
	KAM_STUB_CHECK(init_env != NULL, "dlsym(\"evapi_init_environment\") 非空");

	/* 环境结构复位：先填脏，复位后应全零且 conidx == -1（evapi_dispatch.c:evapi_env_reset） */
	evapi_env_t env;
	memset(&env, 0xAB, sizeof(env));
	env_reset(NULL); /* NULL 契约：直接返回，不崩溃 */
	KAM_STUB_CHECK(1, "evapi_env_reset(NULL) 不崩溃（NULL 契约）");
	env_reset(&env);
	KAM_STUB_CHECK(env.conidx == -1, "evapi_env_reset() 置 conidx == -1（实得 %d）", env.conidx);
	KAM_STUB_CHECK(env.eset == 0 && env.msg.s == NULL && env.msg.len == 0 && env.next == NULL,
			"evapi_env_reset() 将其余字段清零（eset/msg/next）");

	/* 事件路由解析：模块按名解析 3 个事件路由（桩层 record，恒返回 -1 = 未配置分支） */
	init_env(1);
	KAM_STUB_CHECK(kamailio_stub_route_lookup_calls == 3,
			"evapi_init_environment() 调用 route_lookup() 恰好 3 次（实得 %d）",
			kamailio_stub_route_lookup_calls);
	for(int i = 0; i < 3; i++)
		KAM_STUB_CHECK(strcmp(kamailio_stub_route_names[i], EXPECTED_ROUTES[i]) == 0,
				"route_lookup 第 %d 次解析 \"%s\"（实得 \"%s\"）", i, EXPECTED_ROUTES[i],
				kamailio_stub_route_names[i]);
	KAM_STUB_CHECK(kamailio_stub_route_rts_arg != NULL,
			"route_lookup 收到的 route_list 指针非空（即 &event_rt）");

	/* 入参契约：NULL 分支必须返回 -1（不进入需要运行中 core 的路径） */
	set_tag_fn_t set_tag = (set_tag_fn_t)dlsym(handle, "evapi_set_tag");
	cfg_close_fn_t cfg_close = (cfg_close_fn_t)dlsym(handle, "evapi_cfg_close");
	KAM_STUB_CHECK(set_tag != NULL && cfg_close != NULL,
			"dlsym(\"evapi_set_tag\"/\"evapi_cfg_close\") 非空");
	KAM_STUB_CHECK(set_tag(NULL, NULL) == -1, "evapi_set_tag(NULL,NULL) == -1");
	str tag = {(char *)"client-a", 8};
	KAM_STUB_CHECK(set_tag(NULL, &tag) == -1, "evapi_set_tag(NULL, tag) == -1");
	KAM_STUB_CHECK(cfg_close(NULL) == -1, "evapi_cfg_close(NULL) == -1");
	/* 需要 shm/运行中 core 的入口仅断言符号存在（不在本用例调用，见 notes.md 已知限制） */
	KAM_STUB_CHECK(dlsym(handle, "evapi_clients_init") != NULL
					&& dlsym(handle, "evapi_queue_init") != NULL
					&& dlsym(handle, "evapi_run_dispatcher") != NULL
					&& dlsym(handle, "evapi_run_worker") != NULL
					&& dlsym(handle, "evapi_relay") != NULL
					&& dlsym(handle, "evapi_relay_unicast") != NULL
					&& dlsym(handle, "evapi_relay_multicast") != NULL,
			"核心运行期入口符号齐备（clients/queue/dispatcher/worker/relay×3）");

	/* ---- 8. 真实调用运行时依赖 libev（模块 DT_NEEDED=libev.so） ---- */
	KAM_STUB_STEP("libev 运行时依赖");
	struct ev_loop *loop = ev_default_loop(0);
	KAM_STUB_CHECK(loop != NULL, "ev_default_loop() 返回非空事件循环（libev.so 已加载）");
	int lpfd[2] = {-1, -1};
	KAM_STUB_CHECK(pipe(lpfd) == 0, "创建测试管道成功");
	ev_io watcher;
	ev_io_init(&watcher, libev_io_cb, lpfd[0], EV_READ);
	ev_io_start(loop, &watcher);
	KAM_STUB_CHECK(write(lpfd[1], "x", 1) == 1, "向管道写入 1 字节触发可读事件");
	ev_run(loop, 0);
	ev_io_stop(loop, &watcher);
	KAM_STUB_CHECK(libev_cb_fired == 1, "ev_run() 真实派发 EV_READ 回调（回调已触发）");
	close(lpfd[0]);
	close(lpfd[1]);

	/* ---- 9. 卸载 ---- */
	KAM_STUB_CHECK(dlclose(handle) == 0, "dlclose(evapi.so) 成功");

	printf("ALL CHECKS PASSED (%d/%d)\n", kamailio_stub_assertions, kamailio_stub_assertions);
	printf("ALL OHOS E2E PASSED (%d assertions, loadmodule path dlopen->exports->cmds/params/pvs->"
		   "mod_register->KEMI table->env_reset/init_environment/set_tag->libev io callback->dlclose)\n",
			kamailio_stub_assertions);
	return 0;
}

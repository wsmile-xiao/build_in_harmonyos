/*
 * kamailio core 最小 ABI 复刻 + shim 记录器声明 —— 仅供 test_package 的消费者
 * 端到端用例使用（kamailio_core_stub.c / test_debugger_e2e.c）。
 *
 * 之所以在此重述类型：e2e 用例不依赖 kamailio 源码树（CI 上只有本包制品与
 * test_package/），故把用到的 core ABI 以最小形式固化下来。字段顺序/类型与 core
 * 头文件逐字段对齐：
 *   cmd_export_t    ← src/core/sr_module.h:206
 *   param_export_t  ← src/core/sr_module.h:234
 *   rpc_export_t    ← src/core/rpc.h:134
 *   module_exports_t← src/core/sr_module.h:288
 */
#ifndef KAMAILIO_CORE_STUB_H
#define KAMAILIO_CORE_STUB_H

/* ── src/core/sr_module.h:206 ──
 *   { char *name; cmd_function function; int param_no; fixup_function fixup;
 *     free_fixup_function free_fixup; unsigned int flags; }
 * debugger 的 cmds[] 与调试无关的函数原型是 (sip_msg*, char*, char*)，此处以
 * void* 代替 sip_msg*（指针宽度一致，本用例不对 SIP 消息解引用）。 */
typedef int (*stub_cmd_function_t)(void *msg, char *p1, char *p2);
typedef int (*stub_fixup_function_t)(void **param, int param_no);

typedef struct cmd_export_ {
	char *name;
	stub_cmd_function_t function;
	int param_no;
	stub_fixup_function_t fixup;
	void *free_fixup;
	unsigned int flags;
} cmd_export_t;

/* ── src/core/sr_module.h:234 ── { char *name; modparam_t type; void *param_pointer; } */
typedef struct param_export_ {
	char *name;
	unsigned int type;
	void *param_pointer;
} param_export_t;

/* ── src/core/rpc.h:134 ──
 *   { const char *name; rpc_function_t function; const char **doc_str; unsigned int flags; } */
typedef struct rpc_export_ {
	const char *name;
	void *function;
	const char **doc_str;
	unsigned int flags;
} rpc_export_t;

/* ── src/core/sr_module.h:288 ── 10 个字段，顺序与 core 完全一致 */
typedef struct module_exports_ {
	char *name;
	unsigned int dlflags;
	cmd_export_t *cmds;
	param_export_t *params;
	rpc_export_t *rpc_methods;
	void *pv_items;
	void *response_f;
	void *init_mod_f;
	void *init_child_f;
	void *destroy_mod_f;
} module_exports_t;

/* ── core shim 记录器（由 kamailio_core_stub.c 定义，用例读取）────────────── */
extern int stub_rpc_register_calls;	 /* rpc_register_array() 调用次数 */
extern void *stub_rpc_registered_array;	 /* 最后一次注册的 rpc_export_t* */
extern int stub_script_cb_calls;	 /* register_script_cb() 调用次数 */
extern int stub_event_cb_calls;		 /* sr_event_register_cb() 调用次数 */
extern int stub_kemi_add_calls;		 /* sr_kemi_modules_add() 调用次数 */
extern void *stub_module_level_cb;	 /* set_module_debug_level_cb() 入参 */
extern void *stub_module_facility_cb;	 /* set_module_debug_facility_cb() 入参 */

#endif /* KAMAILIO_CORE_STUB_H */

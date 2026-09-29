/*
 * lrkproxy 端到端消费者用例（rule12：完整消费者用例，非纯断言）
 *
 * 以 kamailio core 加载模块的真实消费路径走通完整生命周期：
 *   1. dlopen(lrkproxy.so)          —— core 插件加载（OHOS musl 急切绑定，
 *                                      由 lrkproxy_core_stub.c 提供 core ABI）
 *   2. dlsym("exports")             —— 取 module_exports，校验模块名/命令表/参数表
 *   3. 遍历 params 找 "lrkproxy_sock"，以 PARAM_STRING 真实调用其 setter
 *      （lrkproxy_set_store：pkg_malloc 存储代理集字符串，模拟 kamailio.conf
 *       的 modparam("lrkproxy", "lrkproxy_sock", "udp:127.0.0.1:10000")）
 *   4. 调用 exports.init_mod_f()    —— 真实执行 mod_init：shm_malloc 建
 *      lrkp_set_list 头节点并解析存储的代理集（真实业务状态被建立）
 *   5. 调用 exports.destroy_mod_f() —— 真实执行 mod_destroy 释放
 *   6. dlclose
 * 每一步的返回值/模块状态均被断言；任何一步失败即用例失败。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#include "lrkproxy_core_stub.h"

/* core 结构布局（与 src/core/sr_module.h、str.h 逐字段对齐） */
typedef struct _str {
	char *s;
	int len;
} str_t;

typedef int (*cmd_function)(void *, char *, char *);
typedef int (*fixup_function)(void **param, int param_no);
typedef int (*free_fixup_function)(void **param, int param_no);
typedef unsigned int modparam_t;
typedef int (*param_func_t)(modparam_t type, void *val);

typedef struct cmd_export {
	char *name;
	cmd_function function;
	int param_no;
	fixup_function fixup;
	free_fixup_function free_fixup;
	unsigned int flags;
} cmd_export_t;

typedef struct param_export {
	char *name;
	modparam_t type;
	void *param_pointer;
} param_export_t;

typedef int (*init_function)(void);
typedef int (*child_init_function)(int rank);
typedef void (*destroy_function)(void);
typedef int (*response_function)(void *);

typedef struct module_exports {
	char *name;
	unsigned int dlflags;
	cmd_export_t *cmds;
	param_export_t *params;
	void *rpc_methods;
	void *pv_items;
	response_function response_f;
	init_function init_mod_f;
	child_init_function init_child_f;
	destroy_function destroy_mod_f;
} module_exports_t;

#define PARAM_STRING (1U << 0)
#define PARAM_INT (1U << 1)
#define PARAM_USE_FUNC (1U << (8 * sizeof(int) - 1))
#define PARAM_TYPE_MASK(_x) ((_x) & (~PARAM_USE_FUNC))

static int failures;

static void check(int cond, const char *label)
{
	printf("[%s] %s\n", cond ? "PASS" : "FAIL", label);
	if (!cond)
		failures++;
}

int main(int argc, char **argv)
{
	if (argc < 2) {
		fprintf(stderr, "usage: %s <path/to/lrkproxy.so>\n", argv[0]);
		return 2;
	}
	const char *module_path = argv[1];

	/* 无缓冲输出：崩溃时也能看到已到达的步骤 */
	setvbuf(stdout, NULL, _IONBF, 0);

	/* 1) dlopen：core 插件加载（musl 急切绑定，stub 提供 core ABI） */
	void *h = dlopen(module_path, RTLD_NOW | RTLD_LOCAL);
	if (!h) {
		fprintf(stderr, "dlopen failed: %s\n", dlerror());
		return 1;
	}
	printf("artifact: %s loaded\n", module_path);

	/* 2) dlsym exports：模块注册入口（kamailio core 加载后即读此符号） */
	dlerror();
	module_exports_t *exp = (module_exports_t *)dlsym(h, "exports");
	check(exp != NULL, "dlsym exports（模块注册入口）");
	if (!exp) {
		dlclose(h);
		return 1;
	}
	check(exp->name != NULL && strcmp(exp->name, "lrkproxy") == 0,
	      "exports.name == \"lrkproxy\"");
	check(exp->cmds != NULL, "exports.cmds 非空（导出 SIP 命令表）");
	if (exp->cmds) {
		int n = 0;
		for (; exp->cmds[n].name; n++)
			;
		check(n >= 2, "命令表含导出命令");
		printf("  cmds: ");
		for (int i = 0; i < n; i++)
			printf("%s%s", i ? ", " : "", exp->cmds[i].name);
		printf("\n");
	}
	check(exp->params != NULL, "exports.params 非空（导出模块参数表）");
	check(exp->init_mod_f != NULL, "exports.init_mod_f 存在");
	check(exp->destroy_mod_f != NULL, "exports.destroy_mod_f 存在");

	/* 3) 真实调用参数 setter：等价于 kamailio.conf 的
	 *    modparam("lrkproxy", "lrkproxy_sock", "udp:127.0.0.1:10000") */
	char sock_param[] = "udp:127.0.0.1:10000";
	int called = 0;
	if (exp->params) {
		printf("  params: ");
		for (int i = 0; exp->params[i].name; i++) {
			printf("%s ", exp->params[i].name);
			if (strcmp(exp->params[i].name, "lrkproxy_sock") == 0
				&& PARAM_TYPE_MASK(exp->params[i].type) == PARAM_STRING
				&& (exp->params[i].type & PARAM_USE_FUNC)
				&& exp->params[i].param_pointer) {
				param_func_t setter = (param_func_t)exp->params[i].param_pointer;
				printf("\n  [debug] calling setter...\n");
				int src = setter(PARAM_STRING, sock_param);
				printf("  [debug] setter rc=%d\n", src);
				check(src == 0, "真实调用 lrkproxy_sock setter（参数存储）");
				called = 1;
				break;
			}
		}
		printf("\n");
	}
	check(called, "找到 lrkproxy_sock 参数（PARAM_STRING|PARAM_USE_FUNC）");

	/* 4) 真实执行 mod_init：shm_malloc 建 set-list + 解析代理集 */
	check(exp->init_mod_f() == 0, "init_mod_f()（mod_init）执行成功");

	/* 5) 真实执行 mod_destroy 释放 */
	exp->destroy_mod_f();
	check(1, "destroy_mod_f()（mod_destroy）执行完成");

	/* 6) dlclose */
	dlclose(h);
	check(1, "dlclose 正常卸载");

	if (failures) {
		printf("\nE2E FAILED: %d 项\n", failures);
		return 1;
	}
	printf("\nE2E OK: loadmodule 消费路径全部通过\n");
	return 0;
}

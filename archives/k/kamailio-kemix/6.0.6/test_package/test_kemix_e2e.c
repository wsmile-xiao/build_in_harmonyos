/* test_kemix_e2e.c — kamailio-kemix 鸿蒙特有端到端消费者用例
 *
 * 目的（rule12「完整消费者用例」）：在 OHOS 上真实走通 kamailio core 加载并消费
 * core 插件模块的完整路径，而非只做产物静态断言：
 *
 *   dlopen(kemix.so, RTLD_NOW)                 ← musl 不做惰性绑定，全部符号须可解析
 *     → dlsym("exports")                        ← module_exports 描述符（loadmodule 读取入口）
 *     → 校验 name=="kemix" / dlflags / 无 cfg 命令导出
 *     → dlsym("mod_register")                   ← kamailio 加载器随后调用的注册入口
 *     → 调用 mod_register(path, &dlflags, NULL, NULL)
 *     → 观察 core 侧 sr_kemi_modules_add() 收到的 KEMI 函数表（本用例的桩层记录）
 *     → 遍历 sr_kemi_kx_exports 全表（69 项 + 结尾项），校验模块名/返回类型/函数指针
 *     → 真实调用其中一个函数指针 (kx, get_ruri) 并检查返回值语义
 *
 * core 符号由 kamailio_core_stub.c 提供，测试可执行文件以 -Wl,--export-dynamic 导出，
 * 供 dlopen 解析（OHOS/musl 加载器 RTLD_NOW 语义）。
 *
 * 用法：test_kemix_e2e <kemix.so 绝对路径>
 */
#include "kamailio_core_stub.h"

#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

/* module_exports 前 3 个字段（src/core/sr_module.h 6.0.6 顺序）：
 * char *name; int dlflags; cmd_export_t *cmds; ... */
typedef struct
{
	char *name;
	int dlflags;
	void *cmds;
} module_exports_head_t;

/* KEMI 表中 (kx, fname) 的 XVAL 型函数指针签名：sr_kemi_xval_t *(sip_msg_t *)
 * （kemix 全部 69 个函数都只接收 msg，参数类型均为 SR_KEMIP_NONE） */
typedef sr_kemi_xval_t *(*kemix_xval_fn_t)(void *msg);

/* 期望存在的上游 KEMI 函数名（doc/kemix_admin.xml 登记，源码实测） */
static const char *EXPECTED_NAMES[] = {
	"get_ruri", "get_ruser", "get_rhost", "get_ouri",
	"get_furi", "get_tuser", "get_thost", "get_envn",
};
static const int EXPECTED_NAMES_N = (int)(sizeof(EXPECTED_NAMES) / sizeof(EXPECTED_NAMES[0]));

/* 上游 kemix 模块 KEMI 函数表条目数（src/modules/kemix/kemix_mod.c:1296 起，
 * 每项 str_init("kx") + str_init("<fname>")，表尾为全零项） */
#define EXPECTED_TABLE_ENTRIES 69

/* kamailio 6.0.6 的 DEFAULT_DLFLAGS 是「交回 core 决定实际 dlopen flags」的哨兵值 0
 * （src/core/sr_module.h:188，注释原文：value that signals to module loader to use
 * default dlopen flags in Kamailio）；故此处断言相等而非不等。 */
#define KEMIX_DEFAULT_DLFLAGS_SENTINEL 0

int main(int argc, char **argv)
{
	if(argc < 2)
	{
		fprintf(stderr, "usage: %s <path/to/kemix.so>\n", argv[0]);
		return 2;
	}
	const char *module_path = argv[1];
	printf("kamailio-kemix 鸿蒙端到端消费者用例\n  module=%s\n", module_path);

	/* ---- 1. 加载模块（模拟 kamailio loadmodule，RTLD_NOW = musl 语义） ---- */
	void *handle = dlopen(module_path, RTLD_NOW | RTLD_GLOBAL);
	if(handle == NULL)
	{
		fprintf(stderr, "dlopen failed: %s\n", dlerror());
		return 1;
	}
	KAM_STUB_CHECK(handle != NULL, "dlopen(kemix.so, RTLD_NOW|RTLD_GLOBAL) 成功");

	/* ---- 2. module_exports 描述符：kamailio 加载器读取的第一入口 ---- */
	module_exports_head_t *exports = (module_exports_head_t *)dlsym(handle, "exports");
	KAM_STUB_CHECK(exports != NULL && exports->name != NULL,
			"dlsym(\"exports\") 返回 module_exports 描述符");
	KAM_STUB_CHECK(strcmp(exports->name, "kemix") == 0,
			"exports.name == \"kemix\"（实得 \"%s\"）", exports->name);
	KAM_STUB_CHECK(exports->dlflags == KEMIX_DEFAULT_DLFLAGS_SENTINEL,
			"exports.dlflags == DEFAULT_DLFLAGS 哨兵值 %d（实得 %d；实际 dlopen flags 由 core 加载器决定）",
			KEMIX_DEFAULT_DLFLAGS_SENTINEL, exports->dlflags);
	KAM_STUB_CHECK(exports->cmds == NULL,
			"kemix 不导出 cfg 命令（exports.cmds == NULL，KEMI-only 模块）");

	/* ---- 3. KEMI 注册入口：加载器随后调用 mod_register() ---- */
	typedef int (*mod_register_fn_t)(char *path, int *dlflags, void *p1, void *p2);
	mod_register_fn_t mod_register = (mod_register_fn_t)dlsym(handle, "mod_register");
	KAM_STUB_CHECK(mod_register != NULL, "dlsym(\"mod_register\") 非空");

	int dlflags = 0;
	int rc = mod_register((char *)module_path, &dlflags, NULL, NULL);
	KAM_STUB_CHECK(rc == 0, "mod_register() 返回 0（实得 %d）", rc);
	KAM_STUB_CHECK(kamailio_stub_kemi_add_calls == 1,
			"mod_register() 恰好调用 sr_kemi_modules_add() 一次（实得 %d 次）",
			kamailio_stub_kemi_add_calls);

	/* ---- 4. 遍历注册进 core 的 KEMI 函数表 ---- */
	const sr_kemi_t *table = kamailio_stub_last_kemi_table;
	KAM_STUB_CHECK(table != NULL, "sr_kemi_modules_add() 收到的函数表非空");

	int n = 0;
	while(!kamailio_stub_is_table_end(&table[n]))
		n++;
	KAM_STUB_CHECK(n == EXPECTED_TABLE_ENTRIES,
			"KEMI 函数表条目数 == %d（实得 %d）", EXPECTED_TABLE_ENTRIES, n);

	int all_kx = 1, all_func = 1;
	int n_xval = 0, n_int = 0, n_bool = 0, n_other = 0;
	for(int i = 0; i < n; i++)
	{
		if(table[i].mname.s == NULL || strcmp(table[i].mname.s, "kx") != 0
				|| table[i].mname.len != 2)
			all_kx = 0;
		switch(table[i].rtype)
		{
			case SR_KEMIP_XVAL: n_xval++; break;
			case SR_KEMIP_INT: n_int++; break;
			case SR_KEMIP_BOOL: n_bool++; break;
			default: n_other++; break;
		}
		if(table[i].func == NULL)
			all_func = 0;
	}
	KAM_STUB_CHECK(all_kx, "全部 %d 项子模块名均为 \"kx\"（KSR.kx.*）", n);
	/* rtype 分布（源码实测，kemix_mod.c 表内逐项）：
	 *   SR_KEMIP_XVAL 57 项（返回 sr_kemi_xval_t*，如 get_ruri/get_ruser）
	 *   SR_KEMIP_INT  10 项（返回 int，如 get_msgtype/get_status/get_bodylen）
	 *   SR_KEMIP_BOOL  2 项（ifdef/ifndef）
	 * 合计 69，与表条目数一致；其它取值说明用例结构体布局与上游 sr_kemi_t 不符 */
	KAM_STUB_CHECK(n_xval == 57 && n_int == 10 && n_bool == 2 && n_other == 0,
			"返回类型分布与上游一致（XVAL=57 INT=10 BOOL=2 其它=0；实得 XVAL=%d INT=%d BOOL=%d 其它=%d）",
			n_xval, n_int, n_bool, n_other);
	KAM_STUB_CHECK(all_func, "全部 %d 项函数指针非空", n);

	for(int k = 0; k < EXPECTED_NAMES_N; k++)
	{
		int found = 0;
		for(int i = 0; i < n && !found; i++)
			if(table[i].fname.s != NULL && strcmp(table[i].fname.s, EXPECTED_NAMES[k]) == 0)
				found = 1;
		KAM_STUB_CHECK(found, "表中存在 KEMI 函数 (kx, %s)", EXPECTED_NAMES[k]);
	}

	/* ---- 5. 真实调用一个函数指针：NULL 消息应返回 SR_KEMIP_NULL ---- */
	kemix_xval_fn_t get_ruri = NULL;
	for(int i = 0; i < n; i++)
		if(table[i].fname.s != NULL && strcmp(table[i].fname.s, "get_ruri") == 0)
		{
			get_ruri = (kemix_xval_fn_t)table[i].func;
			break;
		}
	KAM_STUB_CHECK(get_ruri != NULL, "取得 (kx, get_ruri) 的函数指针");
	sr_kemi_xval_t *xval = get_ruri(NULL); /* msg == NULL：core 语义返回 NULL 型 xval */
	KAM_STUB_CHECK(xval != NULL, "get_ruri(NULL) 返回非空 xval 指针");
	KAM_STUB_CHECK(xval->vtype == SR_KEMIP_NULL,
			"get_ruri(NULL).vtype == SR_KEMIP_NULL(%d)（实得 %d）",
			SR_KEMIP_NULL, xval->vtype);

	/* ---- 6. 卸载 ---- */
	KAM_STUB_CHECK(dlclose(handle) == 0, "dlclose(kemix.so) 成功");

	printf("ALL CHECKS PASSED (%d/%d)\n", kamailio_stub_assertions, kamailio_stub_assertions);
	printf("ALL OHOS E2E PASSED (%d assertions, loadmodule path dlopen->exports->mod_register->KEMI table->call)\n",
			kamailio_stub_assertions);
	return 0;
}

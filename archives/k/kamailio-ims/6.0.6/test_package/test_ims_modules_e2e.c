/* test_ims_modules_e2e.c — kamailio-ims 6.0.6 端到端消费者用例（16 模块 + 真实算法）
 *
 * 消费者视角：模拟 kamailio 加载器对 16 个 IMS core 插件模块的真实使用序列：
 *
 *   A. dlopen(模块, RTLD_NOW|RTLD_GLOBAL) —— 与 kamailio loadmodule 同语义
 *      （OHOS/musl 无惰性绑定：未定义符号必须全部可解析，桩层 + 自动生成弱桩
 *      与之配套，见 kamailio_core_stub.c / gen_core_stub.py）
 *   B. dlsym("exports") 读取模块导出结构，校验：
 *        - 契约名（kamailio 注册模块所用名字）
 *        - dlflags == RTLD_NOW（立即绑定；同时校验结构字段偏移正确）
 *        - MODULE_VERSION 生成的三个符号在运行时可解析
 *   C. 遍历 cfg 命令表 / modparam 表至哨兵项，校验每项 name 非空、函数指针非空、
 *      modparam 类型非零且指向真实存储 —— 并核对条目数与上游源码一致
 *      （条目数由 count_entries.py 大括号配对解析上游源码得出）
 *   D. 调用模块 mod_register()，校验 KEMI 表注册行为（表指针、条目数、子模块名
 *      一致性、函数指针与参数类型位有效）
 *   E. ims_ipsec_pcscf.so 的 SPI 链表真实算法行为用例：对**已编译产物**中的
 *      create_list/spi_add/spi_remove_head/spi_remove/spi_in_list/destroy_list 做
 *      正常路径 + 边界路径 + 内存配对校验（内存后端由桩层以 malloc/free 真实实现）
 *
 * 返回 0 = 全部断言通过；非 0 = 首个失败断言（stderr 输出断言序号与详情）。
 */

#include "kamailio_core_stub.h"

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ─────────────── 期望契约表（条目数 = 上游源码精确解析值，不含哨兵项） ─────────────── */
typedef struct
{
	const char *file;
	const char *contract;
	int cmds;   /* cfg 命令表条目数 */
	int params; /* modparam 表条目数 */
	int kemi;   /* mod_register 注册的 KEMI 条目数（0 = 模块无 KEMI 表） */
} mod_expect_t;

/* 期望值口径：逐模块按上游源码数组初始化器统计（先剥离 C 注释——注释内逗号会误切表项，
 * 再按顶层逗号切分并剔除全零哨兵项），非人工摘录。实测校准：cdp 命令表 41 项
 * = 4 项显式 + 37 项 EXP_FUNC(AAA*) 宏展开（cdp_mod.c:131-179）。 */
static const mod_expect_t MODULES[] = {
		{"cdp.so", "cdp", 41, 10, 3},
		{"cdp_avp.so", "cdp_avp", 1, 0, 0},
		{"ims_auth.so", "ims_auth", 9, 18, 0},
		{"ims_charging.so", "ims_charging", 3, 32, 3},
		{"ims_dialog.so", "ims_dialog", 16, 16, 3},
		{"ims_diameter_server.so", "ims_diameter_server", 4, 0, 2},
		{"ims_icscf.so", "ims_icscf", 4, 11, 0},
		{"ims_ipsec_pcscf.so", "ims_ipsec_pcscf", 8, 12, 0},
		{"ims_isc.so", "ims_isc", 3, 5, 0},
		{"ims_ocs.so", "ims_ocs", 1, 0, 0},
		{"ims_qos.so", "ims_qos", 2, 27, 2},
		/* 上游 ims_qos_npn 的 exports.name 与 ims_qos 同为 "ims_qos"（上游写法） */
		{"ims_qos_npn.so", "ims_qos", 3, 29, 2},
		{"ims_registrar_pcscf.so", "ims_registrar_pcscf", 9, 14, 0},
		{"ims_registrar_scscf.so", "ims_registrar_scscf", 18, 43, 0},
		{"ims_usrloc_pcscf.so", "ims_usrloc_pcscf", 1, 11, 0},
		{"ims_usrloc_scscf.so", "ims_usrloc_scscf", 1, 26, 0},
};
#define NMODULES ((int)(sizeof(MODULES) / sizeof(MODULES[0])))

/* ─────────────── SPI 链表结构镜像（src/modules/ims_ipsec_pcscf/spi_list.h 逐字段一致） ─────────────── */
typedef struct kam_spi_node
{
	struct kam_spi_node *next;
	uint32_t spi_cid;
	uint32_t spi_sid;
	uint16_t sport;
	uint16_t cport;
} kam_spi_node_t;

typedef struct
{
	kam_spi_node_t *head;
	kam_spi_node_t *tail;
} kam_spi_list_t;

typedef kam_spi_list_t (*fn_create)(void);
typedef void (*fn_destroy)(kam_spi_list_t *);
typedef int (*fn_add)(kam_spi_list_t *, uint32_t, uint32_t, uint16_t, uint16_t);
typedef int (*fn_rm_head)(kam_spi_list_t *);
typedef int (*fn_remove)(kam_spi_list_t *, uint32_t, uint32_t);
typedef int (*fn_in_list)(kam_spi_list_t *, uint32_t, uint32_t);

typedef int (*fn_mod_register)(char *, int *, void *, void *);

/* ─────────────── 辅助 ─────────────── */

static const char *MODDIR = NULL;

static int walk_cmds(const char *mod, kam_cmd_export_t *cmds, int expect)
{
	int n = 0;

	if (!cmds)
		return expect == 0 ? 0 : -1;
	while (!kamailio_stub_cmd_is_end(&cmds[n]))
	{
		if (n >= 512)
		{
			fprintf(stderr, "ASSERT FAILED: %s cfg 命令表超过 512 项无哨兵项\n", mod);
			return -1;
		}
		if (!cmds[n].function)
		{
			fprintf(stderr, "ASSERT FAILED: %s cfg 命令 %s 的函数指针为空\n", mod,
					cmds[n].name ? cmds[n].name : "(null)");
			return -1;
		}
		n++;
	}
	if (n != expect)
	{
		fprintf(stderr, "ASSERT FAILED: %s cfg 命令表条目数 %d != 期望 %d\n", mod, n, expect);
		return -1;
	}
	return n;
}

static int walk_params(const char *mod, kam_param_export_t *params, int expect)
{
	int n = 0;

	if (!params)
		return expect == 0 ? 0 : -1;
	while (!kamailio_stub_param_is_end(&params[n]))
	{
		if (n >= 512)
		{
			fprintf(stderr, "ASSERT FAILED: %s modparam 表超过 512 项无哨兵项\n", mod);
			return -1;
		}
		if (!params[n].type)
		{
			fprintf(stderr, "ASSERT FAILED: %s modparam %s 的类型位为 0\n", mod,
					params[n].name ? params[n].name : "(null)");
			return -1;
		}
		if (!params[n].param_pointer)
		{
			fprintf(stderr, "ASSERT FAILED: %s modparam %s 未指向真实存储\n", mod,
					params[n].name ? params[n].name : "(null)");
			return -1;
		}
		n++;
	}
	if (n != expect)
	{
		fprintf(stderr, "ASSERT FAILED: %s modparam 表条目数 %d != 期望 %d\n", mod, n, expect);
		return -1;
	}
	return n;
}

/* ─────────────── A/B/C/D：16 模块契约 + 表结构 + KEMI 注册 ─────────────── */

static int check_module(const mod_expect_t *m)
{
	char path[1024];
	void *h = NULL;
	kam_module_exports_t *exp = NULL;
	void *sym = NULL;
	int dlflags_local = RTLD_NOW;

	snprintf(path, sizeof(path), "%s/%s", MODDIR, m->file);
	KAM_STUB_STEP("dlopen %s", m->file);
	h = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
	/* dlerror() 读取即清空错误状态：必须只取一次，否则第二次得 NULL（曾致失败信息 "(null)"） */
	const char *dl_err = dlerror();
	KAM_STUB_CHECK(h != NULL, "%s: dlopen 失败（未定义符号未全部解析？）: %s", m->file,
				   dl_err ? dl_err : "?");

	exp = (kam_module_exports_t *)dlsym(h, "exports");
	KAM_STUB_CHECK(exp != NULL, "%s: dlsym(exports) 为空", m->file);
	KAM_STUB_CHECK(exp->name != NULL && strcmp(exp->name, m->contract) == 0,
				   "%s: exports->name = %s，期望 %s", m->file,
				   exp->name ? exp->name : "(null)", m->contract);
	/* exports->dlflags：sr_module.h:188 `#define DEFAULT_DLFLAGS 0`——0 表示「用加载器
	 * 默认 dlopen 标志」（cdp.cdp_mod.c:406 的 mod_register 只注册 KEMI、不设 dlflags）；
	 * 模块亦可显式写 RTLD_NOW|RTLD_GLOBAL（如上游 app_jsdt）。加载器仅在「非 0 且与请求
	 * 值不同」时按模块要求重载（sr_module.c:669）→ 合法取值 = 0 或含 RTLD_NOW 的标志位。 */
	KAM_STUB_CHECK((int)exp->dlflags == 0 || ((int)exp->dlflags & RTLD_NOW) != 0,
				   "%s: exports->dlflags = %d，期望 0(DEFAULT_DLFLAGS) 或含 RTLD_NOW(%d)",
				   m->file, (int)exp->dlflags, RTLD_NOW);

	/* MODULE_VERSION 宏生成的三个符号必须可被加载器解析 */
	const char *vsyms[] = {"module_version", "module_flags", "module_interface_ver"};
	for (int i = 0; i < 3; i++)
	{
		sym = dlsym(h, vsyms[i]);
		KAM_STUB_CHECK(sym != NULL, "%s: dlsym(%s) 为空", m->file, vsyms[i]);
	}

	/* C. 表结构遍历 + 条目数核对 */
	KAM_STUB_STEP("%s cfg 命令 %d 项 / modparam %d 项", m->file, m->cmds, m->params);
	KAM_STUB_CHECK(walk_cmds(m->contract, exp->cmds, m->cmds) == m->cmds,
				   "%s: cfg 命令表校验失败", m->file);
	KAM_STUB_CHECK(walk_params(m->contract, exp->params, m->params) == m->params,
				   "%s: modparam 表校验失败", m->file);

	/* D. mod_register：可选兼容入口（sr_module.c:624 先取 mod_register 作 dlflags
	 *    协商；取不到时加载器回退 dlsym("exports")，:643）。上游 6.0.6 中 6/16 模块
	 *    带该符号，其余 10 个仅导出 exports → 非必需；带该符号者须完成 KEMI 注册。
	 *    对照 archives/k/kamailio-gcrypt/6.0.6（单模块）曾以 mod_register 为硬要求，
	 *    本包为 16 模块集，按模块实际契约分形态核验。 */
	fn_mod_register reg = (fn_mod_register)dlsym(h, "mod_register");

	kamailio_stub_kemi_add_calls = 0;
	kamailio_stub_last_kemi_table = NULL;
	kamailio_stub_last_kemi_table_count = -1;
	kamailio_stub_last_kemi_mname[0] = '\0';

	if (reg)
	{
		int rc = reg((char *)path, &dlflags_local, NULL, NULL);
		KAM_STUB_CHECK(rc == 0, "%s: mod_register 返回 %d（期望 0）", m->file, rc);
		KAM_STUB_STEP("%s mod_register ok → KEMI 注册 %d 次 / 表 %d 项", m->file,
					  kamailio_stub_kemi_add_calls,
					  kamailio_stub_last_kemi_table_count);
		KAM_STUB_CHECK(kamailio_stub_kemi_add_calls == (m->kemi > 0 ? 1 : 0),
					   "%s: sr_kemi_modules_add 调用 %d 次，期望 %d 次", m->file,
					   kamailio_stub_kemi_add_calls, m->kemi > 0 ? 1 : 0);
		KAM_STUB_CHECK(kamailio_stub_last_kemi_table_count == m->kemi,
					   "%s: KEMI 表条目数 %d，期望 %d", m->file,
					   kamailio_stub_last_kemi_table_count, m->kemi);
	}
	else
	{
		KAM_STUB_STEP("%s 无 mod_register（加载器回退 exports 契约）", m->file);
		KAM_STUB_CHECK(m->kemi == 0,
					   "%s: KEMI 表预期 %d 项但产物不含 mod_register 入口",
					   m->file, m->kemi);
	}
	if (kamailio_stub_last_kemi_table != NULL)
	{
		const sr_kemi_t *t = kamailio_stub_last_kemi_table;
		KAM_STUB_CHECK(kamailio_stub_last_kemi_mname[0] != '\0',
					   "%s: KEMI 首项子模块名为空", m->file);
		for (int i = 0; i < m->kemi; i++)
		{
			KAM_STUB_CHECK(t[i].mname.s != NULL && t[i].mname.len > 0,
						   "%s: KEMI[%d] 子模块名为空", m->file, i);
			KAM_STUB_CHECK(t[i].fname.s != NULL && t[i].fname.len > 0,
						   "%s: KEMI[%d] 函数名为空", m->file, i);
			KAM_STUB_CHECK(t[i].func != NULL, "%s: KEMI[%d] 函数指针为空", m->file, i);
			KAM_STUB_CHECK(t[i].rtype != 0, "%s: KEMI[%d] 返回类型位为 0", m->file, i);
			KAM_STUB_CHECK(strncmp(t[i].mname.s, kamailio_stub_last_kemi_mname,
										   t[i].mname.len) == 0,
						   "%s: KEMI[%d] 子模块名与首项不一致", m->file, i);
			for (int j = 0; j < SR_KEMI_PARAMS_MAX; j++)
				KAM_STUB_CHECK((t[i].ptypes[j] & ~0x3F) == 0,
							   "%s: KEMI[%d] 参数类型位非法: %d", m->file, i,
							   t[i].ptypes[j]);
		}
	}

	dlclose(h);
	return 0;
}

/* ─────────────── E：ims_ipsec_pcscf.so 的 SPI 链表真实算法行为用例 ─────────────── */

static int spi_behavior(void)
{
	const char *file = "ims_ipsec_pcscf.so";
	char path[1024];
	void *h;
	fn_create create;
	fn_destroy destroy;
	fn_add add;
	fn_rm_head rm_head;
	fn_remove remove_;
	fn_in_list in_list;
	kam_spi_list_t lst;
	long alloc0, free0;

	snprintf(path, sizeof(path), "%s/%s", MODDIR, file);
	h = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
	KAM_STUB_CHECK(h != NULL, "%s: dlopen 失败: %s", file, dlerror() ? dlerror() : "?");
	create = (fn_create)dlsym(h, "create_list");
	destroy = (fn_destroy)dlsym(h, "destroy_list");
	add = (fn_add)dlsym(h, "spi_add");
	rm_head = (fn_rm_head)dlsym(h, "spi_remove_head");
	remove_ = (fn_remove)dlsym(h, "spi_remove");
	in_list = (fn_in_list)dlsym(h, "spi_in_list");
	KAM_STUB_CHECK(create && destroy && add && rm_head && remove_ && in_list,
				   "%s: SPI 链表 API 导出不全（create=%p destroy=%p add=%p rm_head=%p "
				   "remove=%p in_list=%p）",
				   file, (void *)create, (void *)destroy, (void *)add, (void *)rm_head,
				   (void *)remove_, (void *)in_list);

	/* 1. 空表初始化 */
	KAM_STUB_STEP("SPI 1/6 空表初始化");
	lst = create();
	KAM_STUB_CHECK(lst.head == NULL && lst.tail == NULL, "SPI: create_list 未返回空表");

	/* 2. 追加两项（FIFO；spi_add(cport, sport) 参数序） */
	KAM_STUB_STEP("SPI 2/6 追加两项 + 字段落位");
	alloc0 = kamailio_stub_shm_alloc_calls;
	KAM_STUB_CHECK(add(&lst, 0xAABBCCDDu, 0x11223344u, 0x1000u, 0x2000u) == 0,
				   "SPI: 首次 spi_add 返回非 0");
	KAM_STUB_CHECK(lst.head == lst.tail && lst.head != NULL,
				   "SPI: 首项后 head/tail 应指向同一节点");
	KAM_STUB_CHECK(lst.head->spi_cid == 0xAABBCCDDu && lst.head->spi_sid == 0x11223344u,
				   "SPI: 节点 spi_cid/spi_sid 落位错误");
	KAM_STUB_CHECK(lst.head->cport == 0x1000u && lst.head->sport == 0x2000u,
				   "SPI: 节点 cport/sport 落位错误(cport=%u sport=%u)", lst.head->cport,
				   lst.head->sport);
	KAM_STUB_CHECK(lst.head->next == NULL, "SPI: 首项 next 非空");
	KAM_STUB_CHECK(add(&lst, 0x01020304u, 0x05060708u, 0x0011u, 0x0022u) == 0,
				   "SPI: 第二次 spi_add 返回非 0");
	KAM_STUB_CHECK(lst.head != lst.tail && lst.tail->spi_cid == 0x01020304u,
				   "SPI: 追加语义错误（应挂到 tail）");
	KAM_STUB_CHECK(lst.head->spi_cid == 0xAABBCCDDu, "SPI: 追加后表头被改写");
	KAM_STUB_CHECK(kamailio_stub_shm_alloc_calls - alloc0 == 2,
				   "SPI: 两次 spi_add 的 shm_malloc 次数应为 2");

	/* 3. 查找 */
	KAM_STUB_STEP("SPI 3/6 查找命中/未命中");
	KAM_STUB_CHECK(in_list(&lst, 0xAABBCCDDu, 0x11223344u) == 1, "SPI: 首项查找未命中");
	KAM_STUB_CHECK(in_list(&lst, 0x01020304u, 0x05060708u) == 1, "SPI: 末项查找未命中");
	KAM_STUB_CHECK(in_list(&lst, 0xAABBCCDDu, 0xDEADBEEFu) == 0, "SPI: 错 sid 误判命中");
	KAM_STUB_CHECK(in_list(&lst, 0xDEADBEEFu, 0x11223344u) == 0, "SPI: 错 cid 误判命中");

	/* 4. 删除中间/末项 → 返回值语义 + tail 一致性 */
	KAM_STUB_STEP("SPI 4/6 删除（表尾/未命中）");
	KAM_STUB_CHECK(remove_(&lst, 0xDEADBEEFu, 0xDEADBEEFu) == -1,
				   "SPI: 未命中删除应返回 -1");
	KAM_STUB_CHECK(in_list(&lst, 0x01020304u, 0x05060708u) == 1,
				   "SPI: 未命中删除误伤既有项");
	KAM_STUB_CHECK(remove_(&lst, 0x01020304u, 0x05060708u) == 1,
				   "SPI: 删除表尾项应返回 1");
	KAM_STUB_CHECK(in_list(&lst, 0x01020304u, 0x05060708u) == 0, "SPI: 表尾项未删掉");
	KAM_STUB_CHECK(lst.tail == lst.head, "SPI: 删除表尾后 tail 未回收至 head");

	/* 5. 删除 head + 空表边界返回值 */
	KAM_STUB_STEP("SPI 5/6 删除表头 + 空表边界");
	KAM_STUB_CHECK(remove_(&lst, 0xAABBCCDDu, 0x11223344u) == 1, "SPI: 删除表头应返回 1");
	KAM_STUB_CHECK(lst.head == NULL && lst.tail == NULL,
				   "SPI: 删空后 head/tail 未同时复位");
	KAM_STUB_CHECK(rm_head(&lst) == 1, "SPI: 空表 spi_remove_head 应返回 1");
	KAM_STUB_CHECK(remove_(&lst, 1u, 2u) == 0, "SPI: 空表 spi_remove 应返回 0");
	KAM_STUB_CHECK(in_list(&lst, 1u, 2u) == 0, "SPI: 空表 spi_in_list 应返回 0");

	/* 6. NULL 边界 + 内存配对 */
	KAM_STUB_STEP("SPI 6/6 NULL 边界 + shm 分配/释放配对");
	KAM_STUB_CHECK(add(NULL, 1u, 2u, 3u, 4u) == 1, "SPI: NULL 表 spi_add 应返回 1");
	KAM_STUB_CHECK(rm_head(NULL) == 1, "SPI: NULL 表 spi_remove_head 应返回 1");
	KAM_STUB_CHECK(remove_(NULL, 1u, 2u) == 0, "SPI: NULL 表 spi_remove 应返回 0");
	KAM_STUB_CHECK(in_list(NULL, 1u, 2u) == 0, "SPI: NULL 表 spi_in_list 应返回 0");
	destroy(NULL); /* 不得崩溃 */
	KAM_STUB_CHECK(1, "SPI: destroy_list(NULL) 未崩溃");

	free0 = kamailio_stub_shm_free_calls;
	lst = create();
	for (int i = 0; i < 3; i++)
		KAM_STUB_CHECK(add(&lst, (uint32_t)(0x100 + i), (uint32_t)(0x200 + i), (uint16_t)i,
						   (uint16_t)(i + 8)) == 0,
					   "SPI: 批量 spi_add 第 %d 项失败", i);
	KAM_STUB_CHECK(in_list(&lst, 0x101u, 0x201u) == 1, "SPI: 批量插入后中间项查找失败");
	destroy(&lst);
	KAM_STUB_CHECK(lst.head == NULL && lst.tail == NULL, "SPI: destroy_list 未复位表头/表尾");
	KAM_STUB_CHECK(kamailio_stub_shm_free_calls - free0 == 3,
				   "SPI: destroy_list 应释放 3 个节点，实得 %ld",
				   kamailio_stub_shm_free_calls - free0);
	KAM_STUB_CHECK(kamailio_stub_shm_alloc_calls == kamailio_stub_shm_free_calls,
				   "SPI: shm 分配/释放未配对（alloc=%ld free=%ld）",
				   kamailio_stub_shm_alloc_calls, kamailio_stub_shm_free_calls);
	dlclose(h);
	return 0;
}

/* ─────────────── main ─────────────── */

int main(int argc, char **argv)
{
	if (argc < 2)
	{
		fprintf(stderr, "用法: %s <模块目录>\n", argv[0]);
		return 2;
	}
	MODDIR = argv[1];

	printf("=======================================================================\n");
	printf("kamailio-ims 6.0.6 端到端消费者用例（%d 模块 + SPI 链表真实算法）\n", NMODULES);
	printf("模块目录: %s\n", MODDIR);
	printf("=======================================================================\n");

	for (int i = 0; i < NMODULES; i++)
	{
		printf("\n[%02d/%d] %s\n", i + 1, NMODULES, MODULES[i].file);
		if (check_module(&MODULES[i]) != 0)
		{
			fprintf(stderr, "\n结论: FAILED（模块 %s）——断言已执行 %d 条\n", MODULES[i].file,
					kamailio_stub_assertions);
			return 1;
		}
	}

	printf("\n[SPI 行为用例] ims_ipsec_pcscf.so（模块真实算法）\n");
	if (spi_behavior() != 0)
	{
		fprintf(stderr, "\n结论: FAILED（SPI 行为用例）——断言已执行 %d 条\n",
				kamailio_stub_assertions);
		return 1;
	}

	printf("\n=======================================================================\n");
	printf("结论: PASSED —— %d 模块 dlopen/契约/cfg 表/modparam 表/KEMI 注册全部通过，\n",
		   NMODULES);
	printf("      ims_ipsec_pcscf.so SPI 链表算法 6 组行为用例通过（含 NULL/空表/未命中边界）\n");
	printf("断言总数: %d\n", kamailio_stub_assertions);
	printf("=======================================================================\n");
	return 0;
}

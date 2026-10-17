/* test_gcrypt_e2e.c — kamailio-gcrypt 鸿蒙特有端到端消费者用例
 *
 * 目的（rule12「完整消费者用例」）：在 OHOS 上真实走通 kamailio core 加载并消费
 * gcrypt 模块的完整路径，而非只做产物静态断言：
 *
 *   dlopen(gcrypt.so, RTLD_NOW)                ← musl 不做惰性绑定，全部符号须可解析
 *     → dlsym("exports")                        ← module_exports 描述符（loadmodule 读取入口）
 *     → 校验 name=="gcrypt" / DEFAULT_DLFLAGS / cfg 命令表 3 项 / 参数表 3 项
 *     → dlsym("mod_register")                   ← kamailio 加载器随后调用的注册入口
 *     → 调用 mod_register(path, &dlflags, NULL, NULL)
 *     → 观察 core 侧 sr_kemi_modules_add() 收到的 KEMI 函数表（本用例的桩层记录）
 *     → dlsym("aes128_context_init/encrypt/decrypt/destroy")
 *     → 真实做 AES-128-CBC 已知答案测试（KAT，向量由 openssl 独立复算）
 *     → dlclose
 *
 * core 符号由 kamailio_core_stub.c 提供，测试可执行文件以 -Wl,--export-dynamic 导出，
 * 供 dlopen 解析（OHOS/musl 加载器 RTLD_NOW 语义）。
 *
 * 用法：test_gcrypt_e2e <gcrypt.so 绝对路径>
 */
#include "kamailio_core_stub.h"

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* module_exports 前 6 个字段（src/core/sr_module.h 6.0.6 顺序，与 gcrypt_mod.c
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

/* gcrypt_mod.c:62-69 —— cfg 命令表（3 项 + 全零结尾项） */
static const char *EXPECTED_CMDS[] = {
	"gcrypt_aes_encrypt", "gcrypt_aes_decrypt", "bind_gcrypt",
};
/* gcrypt_mod.c:71-77 —— 参数表（3 项 + 全零结尾项） */
static const char *EXPECTED_PARAMS[] = {"init_vector", "register_callid", "aes_mode"};
/* gcrypt_mod.c:427-440 —— KEMI 函数表（2 项 + 全零结尾项） */
static const char *EXPECTED_KEMI[] = {"aes_encrypt", "aes_decrypt"};

/* AES-128-CBC 已知答案向量（IV = 全 0，与 gcrypt_aes128.c 的 iv[16]={0} 一致；
 * 期望密文由 openssl 独立复算：
 *   openssl enc -aes-128-cbc -K <key> -iv 00..00 -nopad  →  <ct>）
 * 向量 1：FIPS-197 AES-128 分组测试键/明文（key 000102…0f，pt 00112233…eeff）
 * 向量 2：NIST SP 800-38A F.2.1 首分组（key 2b7e1516…4f3c，pt 6bc1bee2…172a） */
static const uint8_t KAT1_KEY[16] = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
									 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f};
static const uint8_t KAT1_PT[16] = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
									0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff};
static const uint8_t KAT1_CT[16] = {0x69, 0xc4, 0xe0, 0xd8, 0x6a, 0x7b, 0x04, 0x30,
									0xd8, 0xcd, 0xb7, 0x80, 0x70, 0xb4, 0xc5, 0x5a};
static const uint8_t KAT2_KEY[16] = {0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
									 0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c};
static const uint8_t KAT2_PT[16] = {0x6b, 0xc1, 0xbe, 0xe2, 0x2e, 0x40, 0x9f, 0x96,
									0xe9, 0x3d, 0x7e, 0x11, 0x73, 0x93, 0x17, 0x2a};
static const uint8_t KAT2_CT[16] = {0x3a, 0xd7, 0x7b, 0xb4, 0x0d, 0x7a, 0x36, 0x60,
									0xa8, 0x9e, 0xca, 0xf3, 0x24, 0x66, 0xef, 0x97};

/* 模块导出的 AES 辅助 API（src/modules/gcrypt/gcrypt_aes128.h） */
typedef void *(*aes_init_fn_t)(uint8_t key[16]);
typedef void (*aes_destroy_fn_t)(void **context);
typedef int (*aes_crypt_fn_t)(uint8_t *output, uint8_t *input, void *context);

/* kamailio 6.0.6 的 DEFAULT_DLFLAGS 是「交回 core 决定实际 dlopen flags」的哨兵值 0
 * （src/core/sr_module.h:188）；故此处断言相等而非不等。 */
#define GCRYPT_DEFAULT_DLFLAGS_SENTINEL 0

static int kat_case(aes_init_fn_t init, aes_crypt_fn_t enc, aes_crypt_fn_t dec,
		aes_destroy_fn_t destroy, const char *label, const uint8_t key[16],
		const uint8_t pt[16], const uint8_t ct[16])
{
	uint8_t out[16];
	uint8_t back[16];
	uint8_t k[16];

	memcpy(k, key, 16);
	memset(out, 0, sizeof(out));
	memset(back, 0, sizeof(back));

	void *ctx = init(k);
	KAM_STUB_CHECK(ctx != NULL, "%s：aes128_context_init() 返回非空上下文", label);
	KAM_STUB_CHECK(enc(out, (uint8_t *)pt, ctx) == 0, "%s：aes128_encrypt() 返回 0", label);
	KAM_STUB_CHECK(memcmp(out, ct, 16) == 0,
			"%s：密文与 openssl 独立复算的已知答案逐字节一致", label);
	KAM_STUB_CHECK(dec(back, out, ctx) == 0, "%s：aes128_decrypt() 返回 0", label);
	KAM_STUB_CHECK(memcmp(back, pt, 16) == 0, "%s：解密还原明文（round-trip）", label);
	destroy(&ctx);
	KAM_STUB_CHECK(ctx == NULL, "%s：aes128_context_destroy() 置空上下文", label);
	return 0;
}

int main(int argc, char **argv)
{
	if(argc < 2)
	{
		fprintf(stderr, "usage: %s <path/to/gcrypt.so>\n", argv[0]);
		return 2;
	}
	const char *module_path = argv[1];
	printf("kamailio-gcrypt 鸿蒙端到端消费者用例\n  module=%s\n", module_path);

	/* ---- 1. 加载模块（模拟 kamailio loadmodule，RTLD_NOW = musl 语义） ---- */
	void *handle = dlopen(module_path, RTLD_NOW | RTLD_GLOBAL);
	if(handle == NULL)
	{
		fprintf(stderr, "dlopen failed: %s\n", dlerror());
		return 1;
	}
	KAM_STUB_CHECK(handle != NULL, "dlopen(gcrypt.so, RTLD_NOW|RTLD_GLOBAL) 成功");

	/* ---- 2. module_exports 描述符：kamailio 加载器读取的第一入口 ---- */
	module_exports_head_t *exports = (module_exports_head_t *)dlsym(handle, "exports");
	KAM_STUB_CHECK(exports != NULL && exports->name != NULL,
			"dlsym(\"exports\") 返回 module_exports 描述符");
	KAM_STUB_CHECK(strcmp(exports->name, "gcrypt") == 0,
			"exports.name == \"gcrypt\"（实得 \"%s\"）", exports->name);
	KAM_STUB_CHECK(exports->dlflags == GCRYPT_DEFAULT_DLFLAGS_SENTINEL,
			"exports.dlflags == DEFAULT_DLFLAGS 哨兵值 %d（实得 %d）",
			GCRYPT_DEFAULT_DLFLAGS_SENTINEL, exports->dlflags);

	/* ---- 3. cfg 命令表：kamailio 加载时注册的 route 命令 ---- */
	KAM_STUB_CHECK(exports->cmds != NULL, "cfg 命令表指针非空");
	cmd_export_t *cmds = (cmd_export_t *)exports->cmds;
	int n_cmds = 0;
	while(cmds[n_cmds].name != NULL)
	{
		KAM_STUB_CHECK(cmds[n_cmds].function != NULL,
				"cfg 命令 %s 的函数指针非空", cmds[n_cmds].name);
		n_cmds++;
	}
	KAM_STUB_CHECK(n_cmds == 3, "cfg 命令表条目数 == 3（实得 %d）", n_cmds);
	for(int i = 0; i < n_cmds; i++)
		KAM_STUB_CHECK(strcmp(cmds[i].name, EXPECTED_CMDS[i]) == 0,
				"cfg 命令[%d] == \"%s\"（实得 \"%s\"）", i, EXPECTED_CMDS[i], cmds[i].name);
	KAM_STUB_CHECK(cmds[0].param_no == 3 && cmds[1].param_no == 3 && cmds[2].param_no == 0,
			"cfg 命令参数个数为 3/3/0（aes_encrypt/aes_decrypt/bind_gcrypt）");

	/* ---- 4. 参数表 ---- */
	KAM_STUB_CHECK(exports->params != NULL, "参数表指针非空");
	param_export_t *params = (param_export_t *)exports->params;
	int n_params = 0;
	while(params[n_params].name != NULL)
		n_params++;
	KAM_STUB_CHECK(n_params == 3, "参数表条目数 == 3（实得 %d）", n_params);
	for(int i = 0; i < n_params; i++)
		KAM_STUB_CHECK(strcmp(params[i].name, EXPECTED_PARAMS[i]) == 0,
				"参数[%d] == \"%s\"（实得 \"%s\"）", i, EXPECTED_PARAMS[i], params[i].name);

	/* ---- 5. KEMI 注册入口：加载器随后调用 mod_register() ---- */
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
	KAM_STUB_CHECK(n_kemi == 2, "KEMI 函数表条目数 == 2（实得 %d）", n_kemi);
	for(int i = 0; i < n_kemi; i++)
	{
		KAM_STUB_CHECK(table[i].mname.s != NULL && strcmp(table[i].mname.s, "gcrypt") == 0
						&& table[i].mname.len == 6,
				"KEMI[%d] 子模块名为 \"gcrypt\"（KSR.gcrypt.*）", i);
		KAM_STUB_CHECK(table[i].fname.s != NULL && strcmp(table[i].fname.s, EXPECTED_KEMI[i]) == 0,
				"KEMI[%d] 函数名 == \"%s\"", i, EXPECTED_KEMI[i]);
		KAM_STUB_CHECK(table[i].rtype == SR_KEMIP_INT,
				"KEMI[%d] 返回类型 == SR_KEMIP_INT（实得 %d）", i, table[i].rtype);
		KAM_STUB_CHECK(table[i].func != NULL, "KEMI[%d] 函数指针非空", i);
		KAM_STUB_CHECK(table[i].ptypes[0] == SR_KEMIP_STR && table[i].ptypes[1] == SR_KEMIP_STR
						&& table[i].ptypes[2] == SR_KEMIP_STR
						&& table[i].ptypes[3] == SR_KEMIP_NONE,
				"KEMI[%d] 参数类型 == (str,str,str,none…)", i);
	}

	/* ---- 6. 真实调用模块导出的 AES 辅助 API：已知答案测试（KAT） ---- */
	aes_init_fn_t aes_init = (aes_init_fn_t)dlsym(handle, "aes128_context_init");
	aes_crypt_fn_t aes_enc = (aes_crypt_fn_t)dlsym(handle, "aes128_encrypt");
	aes_crypt_fn_t aes_dec = (aes_crypt_fn_t)dlsym(handle, "aes128_decrypt");
	aes_destroy_fn_t aes_destroy = (aes_destroy_fn_t)dlsym(handle, "aes128_context_destroy");
	KAM_STUB_CHECK(aes_init != NULL && aes_enc != NULL && aes_dec != NULL && aes_destroy != NULL,
			"dlsym 取得 aes128 四个导出符号（init/encrypt/decrypt/destroy）");
	KAM_STUB_CHECK(kat_case(aes_init, aes_enc, aes_dec, aes_destroy, "KAT-1",
					KAT1_KEY, KAT1_PT, KAT1_CT) == 0, "KAT-1 用例通过");
	KAM_STUB_CHECK(kat_case(aes_init, aes_enc, aes_dec, aes_destroy, "KAT-2",
					KAT2_KEY, KAT2_PT, KAT2_CT) == 0, "KAT-2 用例通过");
	/* NULL 上下文：模块自身的错误分支（aes128_encrypt 返回 -1，日志经桩层落空） */
	KAM_STUB_CHECK(aes_enc((uint8_t *)KAT1_PT, (uint8_t *)KAT1_PT, NULL) == -1,
			"aes128_encrypt(NULL 上下文) 返回 -1（模块错误分支）");

	/* ---- 7. 卸载 ---- */
	KAM_STUB_CHECK(dlclose(handle) == 0, "dlclose(gcrypt.so) 成功");

	printf("ALL CHECKS PASSED (%d/%d)\n", kamailio_stub_assertions, kamailio_stub_assertions);
	printf("ALL OHOS E2E PASSED (%d assertions, loadmodule path dlopen->exports->cmds/params->"
		   "mod_register->KEMI table->aes128 KAT->dlclose)\n",
			kamailio_stub_assertions);
	return 0;
}

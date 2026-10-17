/*
 * kamailio core 符号 shim —— 仅供 test_package 的消费者端到端用例使用。
 *
 * 背景：debugger.so 是 kamailio 的 **core 插件**：它把 core 提供的 API 与全局量当作
 * 「未定义符号」引用。本机对构建产物实测（llvm-nm -u debugger.so）共 68 个未定义符号，
 * 其中 11 个来自 libc（fprintf/memcmp/memset/sleep/snprintf/stderr/strchr/strcpy/
 * strlen/strncmp/strncpy），其余 57 个全部来自 kamailio core。真实部署时这些 core
 * 符号由 kamailio 主程序导出（-Wl,--export-dynamic）。
 *
 * OHOS 使用 musl libc，其动态链接器**不做惰性绑定**：dlopen(RTLD_LAZY) 等价于
 * RTLD_NOW，库内所有未定义符号必须在加载时就解析完。因此独立加载该模块时，消费者
 * 进程必须提供这 57 个 core 符号 —— 本文件即该最小符号层。它与 test_debugger_e2e.c
 * 链接成同一个测试可执行文件，并依靠 -Wl,--export-dynamic 把符号导出到动态符号表
 * 供 dlopen 解析。
 *
 * 逐符号取舍（core 语义 + 本用例是否真实调用）：
 *   1) rpc_register_array      —— 记录器实现。模块的 dbg_init_rpc()（debugger_api.c:1027）
 *                                 用它把 8 个 RPC 方法注册进 core，本用例直接调用该函数，
 *                                 从而真实走通「模块注册 RPC 表」这条消费者路径。
 *   2) cfg_declare / 回调注册  —— 记录器实现（形参透出为全局量供用例断言）。
 *   3) str2facility            —— 真实实现（决定 dbg_sip_msg fixup 的正/负例分支）。
 *   4) 其余 core API           —— 仅需可被解析（本用例路径上不存在调用点）。
 *   5) core 全局量             —— 零值存储；core_cfg 为零值缓冲区**指针**（cfg_get 宏
 *                                 会解引用它，故必须是有效指针而非数组本体）。
 *   6) 日志机制                —— core 以「函数指针变量」导出 _km_log_func/_ksr_slog_func
 *                                 （src/core/dprint.h），此处按同一 ABI 定义为指向空实现的
 *                                 指针；故任何日志路径都安全、且不产生输出。
 */
#include <stdio.h>
#include <string.h>

#include "kamailio_core_stub.h"

/* ── 记录器（用例读取；见 kamailio_core_stub.h 声明）────────────────────── */
int stub_rpc_register_calls = 0;
void *stub_rpc_registered_array = 0;
int stub_script_cb_calls = 0;
int stub_event_cb_calls = 0;
int stub_kemi_add_calls = 0;
void *stub_module_level_cb = 0;
void *stub_module_facility_cb = 0;

/* ─────── 1) RPC 注册（本用例真实调用：dbg_init_rpc → 8 个方法）──────────
 * core src/core/rpc.h: int rpc_register_array(rpc_export_t *rpc_export)。
 * 记录表指针：用例据 rpc_export_t 布局自行遍历该表，断言方法名/处理函数/文档串，
 * 即「模块确实把 8 个 RPC 方法交给了 core」，而非空转。 */
int rpc_register_array(rpc_export_t *rpc_export)
{
	stub_rpc_register_calls++;
	stub_rpc_registered_array = (void *)rpc_export;
	return 0;
}

/* ─────── 2) cfg 框架与回调注册（记录）──────────────────────────────────
 * core src/core/cfg/cfg.h: int cfg_declare(char *name, cfg_def_t *def, void *defval,
 *                                          int size, void **handle)
 * core 语义：handle 被指向该配置组的实例（默认值实例或 shm 分配的组副本）。此处
 * 直接把 handle 指向模块传入的默认值实例（defval），使模块后续 cfg_get() 读到自身
 * 默认配置，且不触碰 core 的 shm 分配器。 */
int cfg_declare(char *name, void *def, void *defval, int size, void **handle)
{
	(void)name;
	(void)def;
	(void)size;
	if(handle)
		*handle = defval;
	return 0;
}

/* core src/core/script_cb.h: int register_script_cb(ksr_script_cb *cb, unsigned int flags) */
int register_script_cb(void *cb, unsigned int flags)
{
	(void)cb;
	(void)flags;
	stub_script_cb_calls++;
	return 0;
}

/* core src/core/events.h: int sr_event_register_cb(int type, sr_event_cb_f f) */
int sr_event_register_cb(int type, void *f)
{
	(void)type;
	(void)f;
	stub_event_cb_calls++;
	return 0;
}

/* core src/core/kemi.h: int sr_kemi_modules_add(const sr_kemi_t *kemi) */
int sr_kemi_modules_add(void *kemi)
{
	(void)kemi;
	stub_kemi_add_calls++;
	return 0;
}

/* core src/core/dprint.h:198/199 与 src/core/lvalue.h:54 —— 模块 mod_init 注册这三个
 * 回调，供 core 在运行时按模块名调整日志级别/facility 与 log_assign 动作。 */
void set_module_debug_level_cb(void *cb)
{
	stub_module_level_cb = cb;
}
void set_module_debug_facility_cb(void *cb)
{
	stub_module_facility_cb = cb;
}
void set_log_assign_action_cb(void *cb)
{
	(void)cb;
}

/* ─────── 3) 真实实现：日志 facility 名解析（fixup 正/负例依据）────────────
 * core src/core/dprint.c: int str2facility(char *s) —— 名字合法返回 facility 值，
 * 否则返回 -1。模块 fixup_dbg_sip_msg（debugger_mod.c:449）对参数 2 调它：
 * 返回 -1 → E_UNSPEC（负例），否则把 facility 值写入 *param（正例）。 */
int str2facility(char *s)
{
	if(s && strcmp(s, "LOG_DAEMON") == 0)
		return 24; /* LOG_DAEMON = 3 << 3，与 core 一致 */
	return -1;
}

/* core src/core/dprint.c: char *facility2str(int facility) —— 反向名解析。 */
char *facility2str(int facility)
{
	(void)facility;
	return "LOG_DAEMON";
}

/* ─────── 4) 仅需可被解析的 core API（本用例路径不调用）──────────────────
 * 统一以 long 返回 0（指针场景即 NULL、整型场景即 0），且不声明形参：调用约定下
 * 实参多余部分被忽略，返回值在 x0 —— 与本用例无关的符号只需可解析即可。 */
#define STUB_RET0(name) \
	long name(void)     \
	{                   \
		return 0;       \
	}

STUB_RET0(build_req_buf_from_sip_req)	/* core: 由请求构造发送缓冲（Lump 链） */
STUB_RET0(generate_res_buf_from_sip_res) /* core: 由响应构造发送缓冲 */
STUB_RET0(find_export)			/* core: 按名字查已导出命令（cfgt 绑定用） */
STUB_RET0(get_debug_facility)		/* core: 当前日志 facility */
STUB_RET0(get_max_procs)		/* core: 最大进程数 */
STUB_RET0(process_lumps)		/* core: 处理 Lump 链表 */
STUB_RET0(pv_cache_get_name)		/* core: 取 pv 缓存名 */
STUB_RET0(pv_cache_get_table)		/* core: 取 pv 缓存表 */
STUB_RET0(pv_get_avp_name)		/* core: 取 AVP 名字 */
STUB_RET0(pv_get_spec_value)		/* core: 取 pv 值 */
STUB_RET0(pv_parse_spec2)		/* core: 解析 pv 规格串 */
STUB_RET0(search_avp_by_index)		/* core: 按索引查 AVP */
STUB_RET0(search_first_avp)		/* core: 查首个 AVP */
STUB_RET0(search_next_avp)		/* core: 查下一个 AVP */
STUB_RET0(select)			/* core: select 表达式求值 */
STUB_RET0(xavp_get_by_index)		/* core: 按索引取 XAVP */
STUB_RET0(xavp_get_list_key_names)	/* core: 取 XAVP 列表键名 */
STUB_RET0(xavp_get_next)		/* core: 取下一个 XAVP */

/* core src/core/srjson.h —— 模块 debugger_json.c 使用的 JSON 构造层（仅 pv 转储
 * 路径调用，本用例不进入该路径）。 */
STUB_RET0(srjson_AddItemToArray)
STUB_RET0(srjson_AddItemToObject)
STUB_RET0(srjson_AddStrItemToObject)
STUB_RET0(srjson_CreateArray)
STUB_RET0(srjson_CreateNull)
STUB_RET0(srjson_CreateNumber)
STUB_RET0(srjson_CreateObject)
STUB_RET0(srjson_CreateStr)
STUB_RET0(srjson_Delete)
STUB_RET0(srjson_DestroyDoc)
STUB_RET0(srjson_GetArraySize)
STUB_RET0(srjson_InitDoc)
STUB_RET0(srjson_PrintUnformatted)

/* core: int get_debug_level(void) —— 返回低于 L_ERR(-1) 的级别，使 LM_ERR 阈值
 * 检查不通过（配合下面的空实现日志函数，双保险：任何日志路径既不打印也不崩溃）。 */
int get_debug_level(void)
{
	return -2;
}

/* core src/core/dprint.h: pid_t my_pid(void) —— 模块 dbg_msgid_filter 以函数形式调用。 */
int my_pid(void)
{
	return 1;
}

/* ─────── 5) 日志机制：按 core ABI 定义「函数指针变量 + 空实现」────────── */
typedef void (*stub_km_log_f)(int level, const char *fmt, ...);

static void stub_log_impl(int level, const char *fmt, ...)
{
	(void)level;
	(void)fmt;
}

/* core src/core/dprint.h: extern km_log_f _km_log_func; extern km_log_f _ksr_slog_func; */
stub_km_log_f _km_log_func = stub_log_impl;
stub_km_log_f _ksr_slog_func = stub_log_impl;

/* core src/core/dprint.h:217/218 —— 颜色输出（函数，非数据） */
void dprint_color(int level)
{
	(void)level;
}
void dprint_color_reset(void)
{
}

/* ─────── 6) core 全局量：零值存储 ──────────────────────────────────────
 * 可读可写的字节存储；本用例既不读也不写这些量（仅要求符号可解析）。 */
char _pkg_root[64];	   /* core: struct sr_pkg_root *_pkg_root（私有内存根） */
char _shm_root[64];	   /* core: struct sr_shm_root *_shm_root（共享内存根） */
volatile int dprint_crit = 0;  /* core: volatile int dprint_crit */
int log_stderr = 0;	   /* core: int log_stderr（日志是否输出到 stderr） */
char log_color[8];	   /* core: int log_color（日志彩色开关） */
int process_no = 0;	   /* core: int process_no（进程编号） */
int route_type = 0;	   /* core: int route_type（当前路由类型） */
void *log_prefix_val = 0;  /* core: str *log_prefix_val（日志前缀，NULL 安全） */

/* core: struct log_level_info { char *name; int syslog_level; } log_level_info[];
 * 日志级别名表（按级别下标访问，L_ALERT(-5) 起）；零值即可 —— 配合空实现日志函数，
 * 名字永不被人读取。留足 32 项覆盖 -5..+3 全部下标。 */
struct stub_log_level_info {
	char *name;
	int syslog_level;
} log_level_info[32];

/* core src/core/cfg/cfg.h: extern struct cfg_group_core *core_cfg;
 * LM_* 宏经 cfg_get(core, core_cfg, debug) 解引用它，故必须是「有效指针」。
 * 指向全零缓冲区：debug=0、log_facility=0 —— 即使日志宏被求值也是安全读。 */
static char stub_core_cfg_buffer[4096];
void *core_cfg = stub_core_cfg_buffer;

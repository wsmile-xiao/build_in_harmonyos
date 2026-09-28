/*
 * kamailio core 最小 ABI 复刻 + shim 记录器声明 —— 仅供 test_package 的消费者
 * 端到端用例使用（kamailio_core_stub.c / test_outbound_e2e.c）。
 *
 * 之所以在此重述类型：e2e 用例不依赖 kamailio 源码树（CI 上只有本包制品与
 * test_package/），故把用到的 core ABI 以最小形式固化下来。字段顺序/类型与
 * kamailio 6.0.6 core 头文件逐字段对齐，偏移量由本机探针（clang，含真实 core
 * 头文件与 --target 同构的 aarch64 目标）实测记录：
 *   struct sip_msg        sizeof=2016  offsetof(ldv)=1792  sizeof(ldv)=224
 *   ldv.flow              offsetof=0   sizeof=216  flow.decoded@0  flow.rcv@8
 *   struct receive_info   sizeof=208  src_ip@0 dst_ip@24 src_port@48
 *                         dst_port@50 bind_address@192 proto@204
 *   struct ip_addr        sizeof=24   u@8
 *   cmd_export_t sizeof=48   param_export_t sizeof=24   module_exports_t sizeof=80
 *   PARAM_STRING=1  PARAM_INT=2  PARAM_STR=4  DEFAULT_DLFLAGS=0
 *
 * 引用位置（kamailio 6.0.6）：
 *   cmd_export_t      ← src/core/sr_module.h:206
 *   param_export_t    ← src/core/sr_module.h:234
 *   module_exports_t  ← src/core/sr_module.h:288
 *   struct ip_addr    ← src/core/ip_addr.h（src_ip/dst_ip/ports/proto/bind_address）
 *   ldv.flow          ← src/core/parser/msg_parser.h（flow.decoded / flow.rcv）
 */
#ifndef KAMAILIO_CORE_STUB_H
#define KAMAILIO_CORE_STUB_H

#include <stddef.h>

/* ── src/core/sr_module.h:206 ──
 *   { char *name; cmd_function function; int param_no; fixup_function fixup;
 *     free_fixup_function free_fixup; unsigned int flags; }
 * 本例以 void * 代替 sip_msg*（指针宽度一致，用例不对 SIP 消息解引用）。 */
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

/* ── src/core/sr_module.h:234 ── { char *name; modparam_t type; void *param_pointer; }
 * modparam_t 取值（src/core/sr_module.h）：PARAM_STRING=1 PARAM_INT=2 PARAM_STR=4。 */
typedef struct param_export_ {
	char *name;
	unsigned int type;
	void *param_pointer;
} param_export_t;

/* ── src/core/sr_module.h:288 ── outbound 的 exports 用到前 5 个字段 +
 * init_mod_f/init_child_f/destroy_mod_f 三个生命周期指针（共 80 字节）。 */
typedef struct module_exports_ {
	char *name;
	unsigned int dlflags;
	cmd_export_t *cmds;
	param_export_t *params;
	void *rpc_methods;
	void *pv_items;
	void *response_f;
	void *init_mod_f;
	void *init_child_f;
	void *destroy_mod_f;
} module_exports_t;

/* ── src/core/ip_addr.h ──
 * struct ip_addr { int af; int len; union { unsigned char addr[16]; } u; }
 * 用例只用 u.addr[] 与 af/len（IPv4 4 字节 / IPv6 16 字节两种分支）。 */
typedef struct stub_ip_addr_ {
	int af;
	int len;
	union {
		unsigned char addr[16];
	} u;
} stub_ip_addr_t;

/* ── src/core/ip_addr.h: struct receive_info ──
 * 只复刻 outbound 读到的字段，其余以填充字节占位保持偏移一致
 * （bind_address@192、proto@204 由探针实测锚定）。bind_address 置 NULL，
 * 使 encode_flow_token 走「以收包地址为目的地址」的默认分支。 */
typedef struct stub_receive_info_ {
	stub_ip_addr_t src_ip;	 /* @0   */
	stub_ip_addr_t dst_ip;	 /* @24  */
	unsigned short src_port; /* @48  */
	unsigned short dst_port; /* @50  */
	unsigned char reserved[140]; /* @52..@191 */
	void *bind_address;		 /* @192 */
	unsigned char reserved2[4];	 /* @200..@203 */
	unsigned int proto;		 /* @204 */
} stub_receive_info_t;

/* ── src/core/parser/msg_parser.h: msg->ldv.flow ──
 * flow { int decoded; struct receive_info rcv; }（decoded@0、rcv@8、共 216 字节）
 * ldv 共 224 字节，其后字段以填充占位。sip_msg 其余 1792 字节同样填充 ——
 * 用例只把 ldv 当容器交给 decode_flow_token 写入，不触碰其它成员。 */
typedef struct stub_ldv_flow_ {
	int decoded;
	unsigned char pad0[4];
	stub_receive_info_t rcv;
} stub_ldv_flow_t;

typedef struct stub_ldv_ {
	stub_ldv_flow_t flow;
	unsigned char tail[8];
} stub_ldv_t;

typedef struct stub_sip_msg_ {
	unsigned char pad[1792];
	stub_ldv_t ldv;
} stub_sip_msg_t;

/* ── core shim 记录器（由 kamailio_core_stub.c 定义，用例读取）────────────── */
extern int stub_cfg_declare_calls; /* cfg_declare() 调用次数 */
extern char stub_cfg_group[64];	   /* 最后一次 cfg_declare 的配置组名 */
extern void *stub_cfg_default_ptr; /* cfg_declare 收到的默认值实例 */
extern void *stub_cfg_handle_ptr;  /* cfg_declare 回填的句柄（模块 cfg 实例） */
extern int stub_shm_alloc_calls;   /* 经 _shm_root.xmalloc 的分配次数 */
extern int stub_shm_free_calls;	   /* 经 _shm_root.xfree 的释放次数 */
extern int stub_pkg_alloc_calls;   /* pkg_malloc 内联路径的分配次数 */
extern int stub_pkg_free_calls;	   /* pkg_free 内联路径的释放次数 */
extern int stub_find_module_calls; /* find_module_by_name() 调用次数 */

/* ── 符号层初始化（由用例在 dlopen 之前/之后、调用模块功能之前调用）──
 * stub_init       : 安放 _pkg_root/_shm_root 的分配器函数指针
 * stub_init_basex : 填充 _bx_b64_12/_bx_ub64 查找表 */
extern void stub_init(void);
extern void stub_init_basex(void);

/* 释放由 pkg_malloc（= _pkg_root.xmalloc）分配的缓冲区：用例经此释放模块返回的
 * flow-token，使 pkg 分配/释放计数闭环。 */
extern void stub_pkg_free(void *p);

#endif /* KAMAILIO_CORE_STUB_H */

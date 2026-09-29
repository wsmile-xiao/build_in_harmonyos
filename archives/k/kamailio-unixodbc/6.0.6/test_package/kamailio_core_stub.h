/*
 * kamailio core 最小类型定义（与 core 定义逐字段同构）——仅供 test_package 的
 * rule12 端到端消费者用例使用（kamailio_core_stub.c / test_db_unixodbc_e2e.c）。
 *
 * 之所以要在此重述类型：e2e 用例不依赖 kamailio 源码树（CI 上只有本包与
 * test_package/），因此需要把用到的 core ABI 以最小形式固化下来。
 */
#ifndef KAMAILIO_CORE_STUB_H
#define KAMAILIO_CORE_STUB_H

/* core src/core/str.h: struct { char *s; int len; } */
typedef struct
{
	char *s;
	int len;
} str;

/* core src/lib/srdb1/db_con.h:40
 *   typedef struct { const str *table; const char *tquote; unsigned long tail; } db1_con_t;
 * 字段顺序/类型必须与 core 一致：CON_TABLE(cn) 即 (cn)->table，模块写表名时
 * 直接写这个字段，用例据偏移断言数据流。 */
typedef struct
{
	const str *table;   /* CON_TABLE(cn) */
	const char *tquote; /* CON_TQUOTE(cn) */
	unsigned long tail; /* CON_TAIL(cn)，驱动自定义尾部 */
} db1_con_t;

#endif /* KAMAILIO_CORE_STUB_H */

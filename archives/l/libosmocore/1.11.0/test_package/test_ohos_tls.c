/*
 * test_package/test_ohos_tls.c — 鸿蒙特有测试：跨 DSO 的线程局部变量（TLS）一致性
 *
 * 背景：libosmocore 通过公共头文件导出线程局部变量（`extern __thread`）：
 *          include/osmocom/core/talloc.h:22   osmo_ctx
 *          include/osmocom/gsm/cbsp.h:306     osmo_cbsp_errstr
 *       OHOS clang 默认使用模拟 TLS（emutls）。当库与消费者使用不同 TLS 模型时，
 *       跨 DSO 访问这些变量在运行时段错误或读到错误副本；本平台实测：
 *       「库 emutls + 消费者原生 TLS」→ 运行时段错误（对照实验见 notes.md）。
 *       因此配方以原生 TLS（-fno-emulated-tls）构建并通过 cpp_info 传播。
 *
 * 本测试从消费者侧验证三点：
 *       1) 库导出的 TLS 变量可初始化、可读写（跨 DSO 引用可用）
 *       2) 子线程中的同名变量是独立副本（线程隔离）
 *       3) 子线程写入不影响主线程（无跨线程污染）
 */
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>

#include <osmocom/core/talloc.h>  /* osmo_ctx_init() / osmo_ctx */
#include <osmocom/gsm/cbsp.h>     /* osmo_cbsp_errstr */

#define MAIN_TLS_VALUE  "main-thread-tls"
#define CHILD_TLS_VALUE "child-thread-tls"

struct thread_result {
	const char *initial;    /* 子线程首次读到的值（应为 NULL：与主线程隔离） */
	const char *after_set;  /* 子线程写入后读回的值 */
};

static void *thread_fn(void *arg)
{
	struct thread_result *res = arg;

	res->initial = osmo_cbsp_errstr;  /* 主线程已赋值，子线程应仍为初始值 NULL */
	osmo_cbsp_errstr = CHILD_TLS_VALUE;
	res->after_set = osmo_cbsp_errstr;
	return NULL;
}

int main(void)
{
	pthread_t th;
	struct thread_result res = { NULL, NULL };

	/* 1) 库导出的 TLS 变量可在主线程初始化并读写 */
	assert(osmo_ctx_init("test_ohos_tls") == 0);
	assert(osmo_ctx != NULL);
	printf("[ohos-tls] osmo_ctx_init OK, osmo_ctx = %p\n", (void *)osmo_ctx);

	osmo_cbsp_errstr = MAIN_TLS_VALUE;
	assert(strcmp(osmo_cbsp_errstr, MAIN_TLS_VALUE) == 0);
	printf("[ohos-tls] main thread write/read osmo_cbsp_errstr OK\n");

	/* 2) 子线程持有独立副本，写入不污染主线程 */
	assert(pthread_create(&th, NULL, thread_fn, &res) == 0);
	assert(pthread_join(th, NULL) == 0);
	assert(res.initial == NULL);
	assert(res.after_set != NULL);
	assert(strcmp(res.after_set, CHILD_TLS_VALUE) == 0);
	assert(strcmp(osmo_cbsp_errstr, MAIN_TLS_VALUE) == 0);
	printf("[ohos-tls] cross-DSO TLS isolation OK (child initial=%s, main=%s)\n",
	       res.initial ? res.initial : "(null)", osmo_cbsp_errstr);

	/* 3) 主线程的 osmo_ctx 未被其他线程覆盖 */
	assert(osmo_ctx != NULL);

	printf("test libosmocore 1.11.0 OHOS TLS: OK\n");
	return 0;
}

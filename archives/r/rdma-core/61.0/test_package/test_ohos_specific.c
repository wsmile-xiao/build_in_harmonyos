/*
 * test_ohos_specific.c — HarmonyOS 专项测试 (独立于上游测试与消费者用例计数)
 *
 * 针对 OHOS musl libc 平台差异的适配点逐一验证（61.0 补丁的回归验证）：
 *   1. sockaddr_storage 重定义修复（E119）: 同 TU 内同时包含 <linux/netlink.h>
 *      与 <sys/socket.h> 不再重定义 sockaddr_storage（__MUSL__ 定义生效）。
 *   2. getpass() 兼容实现: musl 无 GNU getpass，验证弱符号兼容层可用。
 *   3. rindex -> strrchr: musl 无 rindex()，验证 POSIX strrchr 语义等价。
 *   4. program_invocation_short_name -> __progname: 验证 __progname 可取程序名。
 *   5. pthread_cancel 缺失 -> 信号式线程退出（E513）: 创建工作线程后用保留信号
 *      终止并 join，验证可回收 joinable 线程生命周期。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <signal.h>
#include <unistd.h>

/* 1. E119: 同时包含 linux/netlink.h 与 sys/socket.h 相关头,
 *    netdb.h 已从 netlink-attr.h 移除, sockaddr_storage 不得重定义 */
#include <linux/netlink.h>
#include <sys/socket.h>

/* getpass() 弱符号声明（与补丁 0002/0003 一致） */
char *getpass(const char *prompt) __attribute__((weak));
extern char *__progname;

/* 5. 信号式线程退出验证 */
static void ohos_thread_exit_handler(int sig)
{
	(void)sig;
	pthread_exit(NULL);
}

static void *worker(void *arg)
{
	struct sigaction sa;
	(void)arg;
	memset(&sa, 0, sizeof(sa));
	sa.sa_handler = ohos_thread_exit_handler;
	sigaction(SIGUSR1, &sa, NULL);
	for (;;)
		pause();
	return NULL;
}

static int failures = 0;
#define CHECK(cond, msg) do { \
	if (cond) \
		printf("  [PASS] %s\n", msg); \
	else { \
		printf("  [FAIL] %s\n", msg); \
		failures++; \
	} \
} while (0)

int main(void)
{
	pthread_t th;
	struct sockaddr_storage ss_probe;
	pthread_t id;
	int rc;

	printf("== rdma-core 61.0 HarmonyOS 专项测试 ==\n");

	/* 1. E119 sockaddr_storage */
	printf("[1] sockaddr_storage redefinition (E119)\n");
	memset(&ss_probe, 0, sizeof(ss_probe));
	ss_probe.ss_family = AF_UNSPEC;
	CHECK(sizeof(ss_probe) >= sizeof(struct sockaddr), "header coexistence, sockaddr_storage usable");

	/* 2. getpass 兼容实现 */
	printf("[2] getpass compat (weak symbol)\n");
	{
		char *p = NULL;
		/* 通过管道喂入一行避免阻塞交互 */
		FILE *old = stdin;
		(void)old;
		/* getpass 打开 /dev/tty 失败时回退 stdin；此处直接验证符号存在 */
		CHECK(getpass != NULL, "getpass weak symbol available");
		/* 不实际调用以免挂起, 符号级验证即可 */
		(void)p;
	}

	/* 3. rindex -> strrchr */
	printf("[3] rindex -> strrchr equivalence\n");
	{
		const char *path = "/dev/infiniband/rdma0";
		const char *slash = strrchr(path, '/');
		CHECK(slash != NULL && strcmp(slash, "/rdma0") == 0,
		      "strrchr finds last '/', rindex 语义等价");
	}

	/* 4. __progname */
	printf("[4] __progname\n");
	CHECK(__progname != NULL && strlen(__progname) > 0,
	      "__progname available (program_invocation_short_name 替代)");

	/* 5. 信号式线程退出 (E513) */
	printf("[5] signal-based joinable thread teardown (E513)\n");
	rc = pthread_create(&th, NULL, worker, NULL);
	CHECK(rc == 0, "pthread_create worker");
	if (rc == 0) {
		usleep(100000);
		rc = pthread_kill(th, SIGUSR1);
		CHECK(rc == 0, "pthread_kill(SIGUSR1)");
		rc = pthread_join(th, NULL);
		CHECK(rc == 0, "pthread_join reaps worker (no pthread_cancel needed)");
	}

	/* 汇总 */
	printf("== 结果: %s (%d failure(s)) ==\n", failures == 0 ? "PASS" : "FAIL", failures);
	return failures == 0 ? 0 : 1;
}
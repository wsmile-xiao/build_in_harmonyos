/*
 * test_package consumer test — torsocks 2.5.0
 *
 * dlopen 打包的 libtorsocks.so（通过 VirtualRunEnv 的 LD_LIBRARY_PATH 找到），
 * 验证：
 *   1. 共享库可加载，constructor(tsocks_init) 成功（内部 dlopen 真实 libc）；
 *   2. tsocks_libc_socket 导出符号可解析，且指向的真实 libc socket 能创建 socket；
 *   3. tsocks_libc_connect 导出符号可解析。
 *
 * 注意：tsocks_libc_* 在 libtorsocks.so 中是「函数指针变量」而非函数
 * （torsocks.h 的 TSOCKS_LIBC_DECL 展开为 `类型 (*tsocks_libc_xxx)(...)`，
 * 由 init_libc_symbols() 在 constructor 里 dlsym 真实 libc 后赋值）。dlsym 返回
 * 的是该指针变量的地址（指针槽），必须先解引用再调用，否则 CPU 会把指针数据当
 * 代码执行 → SIGSEGV（rc=139）。dlopen 只用 RTLD_NOW（不加 RTLD_GLOBAL），避免
 * 测试进程自身的 close()/socket() 被插桩符号劫持。
 *
 * 每个用例输出一行 "case N: PASS/FAIL"，最后输出 "RESULT: passed/total"，
 * 供 test_package/conanfile.py 解析并上报 HMBS_TEST_PACKAGE_RESULT。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <sys/socket.h>
#include <unistd.h>

typedef int (*socket_fn_t)(int, int, int);
typedef int (*connect_fn_t)(int, const void *, unsigned int);

static int total = 0;
static int passed = 0;

static void check(int ok, const char *name)
{
	total++;
	if (ok) {
		passed++;
		printf("case %d: %s: PASS\n", total, name);
	} else {
		printf("case %d: %s: FAIL\n", total, name);
	}
}

int main(void)
{
	void *h = dlopen("libtorsocks.so", RTLD_NOW);
	if (!h) {
		printf("dlopen libtorsocks.so failed: %s\n", dlerror());
		check(0, "dlopen libtorsocks.so");
	} else {
		check(1, "dlopen libtorsocks.so");
		/* tsocks_libc_socket 是指针变量，dlsym 得到指针槽地址，解引用后调用。 */
		socket_fn_t *socket_slot = (socket_fn_t *) dlsym(h, "tsocks_libc_socket");
		if (!socket_slot || !*socket_slot) {
			check(0, "dlsym tsocks_libc_socket");
		} else {
			int fd = (*socket_slot)(AF_INET, SOCK_STREAM, 0);
			if (fd >= 0) {
				close(fd);
				check(1, "tsocks_libc_socket");
			} else {
				check(0, "tsocks_libc_socket");
			}
		}
		connect_fn_t *connect_slot =
			(connect_fn_t *) dlsym(h, "tsocks_libc_connect");
		check(connect_slot && *connect_slot != NULL, "dlsym tsocks_libc_connect");
	}
	printf("RESULT: %d/%d\n", passed, total);
	return passed == total ? 0 : 1;
}

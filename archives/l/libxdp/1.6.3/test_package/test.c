/*
 * test_package/test.c — libxdp 1.6.3 L1 官方测试
 *
 * 只调用不需要运行内核的公开 API（OHOS 无 BPF syscall）：
 *   libxdp_strerror        —— 错误码转字符串
 *   libxdp_set_print       —— 日志钩子设置（返回旧钩子，默认非空）
 *   xdp_program__open_file —— 打开不存在的 BPF 对象要返回错误指针，
 *                             并由 libxdp_get_error() 正确报错
 * 任一断言失败返回非零退出码，conan create 即失败。R34 禁止空壳/print-only。
 */
#include <errno.h>
#include <stdio.h>
#include <string.h>

#include <xdp/libxdp.h>

int main(void)
{
	char buf[256];
	libxdp_print_fn_t prev;
	struct xdp_program *prog;
	long err;
	int rc = 0;

	/* 1) public error-string helper */
	memset(buf, 0, sizeof(buf));
	if (libxdp_strerror(-EINVAL, buf, sizeof(buf)) != 0 || strlen(buf) == 0) {
		fprintf(stderr, "FAIL: libxdp_strerror returned empty string\n");
		rc = 1;
	} else {
		printf("libxdp_strerror(-EINVAL) = \"%s\"\n", buf);
	}

	/* 2) default logging hook must be installed */
	prev = libxdp_set_print(NULL);
	if (!prev) {
		fprintf(stderr, "FAIL: libxdp_set_print(NULL) returned NULL\n");
		rc = 1;
	} else {
		printf("libxdp_set_print(NULL) returned previous hook\n");
	}

	/* 3) error path: open_file() of a missing object returns an *error
	 *    pointer*, not NULL (libxdp contract), so close() must NOT be called
	 *    and libxdp_get_error() must report the failure. */
	prog = xdp_program__open_file("/nonexistent/libxdp-l1.o", NULL, NULL);
	err = libxdp_get_error(prog);
	if (err == 0) {
		fprintf(stderr, "FAIL: open_file(missing) unexpectedly succeeded\n");
		xdp_program__close(prog);
		rc = 1;
	} else {
		printf("xdp_program__open_file(missing) error = %ld (expected)\n", err);
	}

	if (rc == 0)
		printf("test libxdp 1.6.3: PASS\n");
	return rc;
}

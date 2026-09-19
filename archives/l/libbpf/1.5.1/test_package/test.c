/*
 * libbpf 1.5.1 test_package — L1 官方测试
 * 实际调用被测包公开 API（R34 禁止空壳/print-only）：
 *   libbpf_version_string / libbpf_bpf_prog_type_str /
 *   libbpf_strerror / btf__new_empty + btf__add_int
 * 任一断言失败返回非零退出码，conan create 即失败。
 * (与消费者用例同构，仅作配方内 L1 测试)
 */
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <bpf/bpf.h>
#include <bpf/libbpf.h>
#include <bpf/btf.h>

int main(void)
{
	const char *ver = libbpf_version_string();
	struct btf *btf;
	int id;
	char errbuf[256];
	int rc = 0;

	printf("libbpf version: %s\n", ver ? ver : "(null)");
	if (!ver || strncmp(ver, "v1.5", 4) != 0)
		rc = 1;

	if (strcmp(libbpf_bpf_prog_type_str(BPF_PROG_TYPE_SOCKET_FILTER),
		   "socket_filter") != 0)
		rc = 1;

	if (libbpf_strerror(-EINVAL, errbuf, sizeof(errbuf)) != 0 ||
	    strlen(errbuf) == 0)
		rc = 1;

	btf = btf__new_empty();
	if (!btf) {
		rc = 1;
	} else {
		id = btf__add_int(btf, "my_int", 4, 0);
		if (id <= 0 || btf__find_by_name(btf, "my_int") != id)
			rc = 1;
		else
			printf("btf int id=%d\n", id);
		btf__free(btf);
	}

	if (rc == 0)
		printf("test libbpf 1.5.1: PASS\n");
	return rc;
}
#include <stdio.h>
#include <string.h>
#include <bpf/libbpf.h>
#include <bpf/btf.h>

/*
 * test_package 消费者测试 — 实质调用 libbpf 公开 API（R34/PF3 合规）：
 *   - libbpf_version_string()  版本字符串
 *   - libbpf_strerror()        错误码转换
 *   - btf__new_empty/add_int   构建 BTF 元数据（可观察结果：类型 ID/总数）
 * 仅依赖已安装的公开头文件与静态库，验证第三方消费者可编译、链接、运行。
 */
int main(void)
{
    int fails = 0;
    const char *ver = libbpf_version_string();
    printf("libbpf version: %s\n", ver);
    if (!ver || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: empty version\n");
        fails++;
    }

    char errbuf[64];
    libbpf_strerror(-22, errbuf, sizeof(errbuf));
    printf("libbpf_strerror(-22): %s\n", errbuf);
    if (strlen(errbuf) == 0) {
        fprintf(stderr, "FAIL: empty strerror\n");
        fails++;
    }

    struct btf *btf = btf__new_empty();
    if (!btf) {
        fprintf(stderr, "FAIL: btf__new_empty\n");
        fails++;
    } else {
        int id = btf__add_int(btf, "test_int", 4, 0);
        printf("btf__add_int -> id=%d type_cnt=%u\n", id, btf__type_cnt(btf));
        if (id < 0 || btf__type_cnt(btf) < 2) {
            fprintf(stderr, "FAIL: btf build\n");
            fails++;
        }
        btf__free(btf);
    }

    printf("%s\n", fails ? "TEST FAIL" : "TEST PASS");
    return fails ? 1 : 0;
}
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gsf/gsf.h>

int main(void)
{
	GsfInput *input;
	guint8 const data[] = "libgsf-consumer-test";
	guint8 const *buf;
	gsf_off_t size;

	/* gsf_init 返回 void，直接调用初始化 */
	gsf_init();

	/* 实质调用 libgsf API：内存输入流创建 + 读取 */
	input = gsf_input_memory_new(data, sizeof(data) - 1, FALSE);
	if (input == NULL) {
		fprintf(stderr, "gsf_input_memory_new failed\n");
		gsf_shutdown();
		return 1;
	}

	size = gsf_input_size(input);
	if (size != (gsf_off_t)(sizeof(data) - 1)) {
		fprintf(stderr, "gsf_input_size mismatch: %lld\n", (long long)size);
		g_object_unref(input);
		gsf_shutdown();
		return 1;
	}

	buf = gsf_input_read(input, sizeof(data) - 1, NULL);
	if (buf == NULL || memcmp(buf, data, sizeof(data) - 1) != 0) {
		fprintf(stderr, "gsf_input_read content mismatch\n");
		g_object_unref(input);
		gsf_shutdown();
		return 1;
	}

	printf("libgsf 1.14.51 consumer test: OK (size=%lld)\n", (long long)size);
	g_object_unref(input);
	gsf_shutdown();
	return 0;
}

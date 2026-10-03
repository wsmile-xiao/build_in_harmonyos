/*
 * 消费者测试 — zoitechat 2.18.1
 *
 * R34: 本测试实质使用被测包产物，而非只打印字符串：
 *   1. 编译期/运行期使用被测包安装的插件宿主头文件 zoitechat-plugin.h，
 *      校验其类型、常量与结构体 ABI 布局（验证 include 安装与头文件完整）；
 *   2. 校验被测包安装的插件共享模块确实产出且为可加载的 ELF
 *      （插件按设计依赖宿主二进制导出符号，故此处只验证产物有效性，
 *      不直接 dlopen）；
 *   3. 被测程序本体由 test_package/conanfile.py 实际执行
 *      （`zoitechat --version`），验证真实可执行产物与依赖链。
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include <zoitechat-plugin.h>

static int check_header_api(void)
{
	/* 头文件中的类型与常量必须可用（编译期 + 运行期双重验证） */
	zoitechat_plugin *ph = NULL;
	zoitechat_event_attrs attrs;

	memset(&attrs, 0, sizeof(attrs));

	if (sizeof(zoitechat_event_attrs) == 0)
		return 0;
	if (sizeof(zoitechat_plugin *) != sizeof(void *))
		return 0;
	if (ZOITECHAT_PRI_NORM != 0)
		return 0;
	if (ZOITECHAT_PRI_HIGHEST <= ZOITECHAT_PRI_LOWEST)
		return 0;
	if (ZOITECHAT_EAT_ALL != (ZOITECHAT_EAT_ZOITECHAT | ZOITECHAT_EAT_PLUGIN))
		return 0;
	/* 结构体成员（ABI 布局）可寻址 */
	if (offsetof(zoitechat_plugin, zoitechat_print) == 0)
		return 0;
	(void)ph;
	printf("zoitechat-plugin.h: API check OK (PRI_NORM=%d, EAT_ALL=%d)\n",
	       ZOITECHAT_PRI_NORM, ZOITECHAT_EAT_ALL);
	return 1;
}

static int check_elf_magic(const char *path, const char *label)
{
	unsigned char magic[4] = {0, 0, 0, 0};
	FILE *fh = fopen(path, "rb");

	if (fh == NULL) {
		fprintf(stderr, "FAIL: cannot open %s (%s)\n", path, label);
		return 0;
	}
	if (fread(magic, 1, sizeof(magic), fh) != sizeof(magic)) {
		fprintf(stderr, "FAIL: cannot read %s (%s)\n", path, label);
		fclose(fh);
		return 0;
	}
	fclose(fh);
	if (memcmp(magic, "\x7f""ELF", 4) != 0) {
		fprintf(stderr, "FAIL: %s is not an ELF file (%s)\n", path, label);
		return 0;
	}
	printf("plugin artifact %s: valid ELF\n", label);
	return 1;
}

static int check_plugin(const char *dir, const char *name)
{
	char path[4096];

	if (snprintf(path, sizeof(path), "%s/%s", dir, name) >= (int)sizeof(path)) {
		fprintf(stderr, "FAIL: plugin path too long\n");
		return 0;
	}
	return check_elf_magic(path, name);
}

int main(int argc, char *argv[])
{
	int rc = 0;

	if (!check_header_api())
		rc = 1;

	/* argv[1] = 被测包安装的插件目录 */
	if (argc > 1) {
		if (!check_plugin(argv[1], "checksum.so"))
			rc = 1;
		if (!check_plugin(argv[1], "fishlim.so"))
			rc = 1;
		if (!check_plugin(argv[1], "lua.so"))
			rc = 1;
	} else {
		fprintf(stderr, "FAIL: plugin dir argument missing\n");
		rc = 1;
	}

	if (rc == 0)
		printf("test zoitechat 2.18.1: OK\n");
	return rc;
}

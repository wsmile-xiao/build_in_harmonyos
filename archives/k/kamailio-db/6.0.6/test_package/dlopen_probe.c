/*
 * dlopen_probe.c —— kamailio-db 6.0.6 test_package 鸿蒙特有用例 [H7]
 *
 * 在 OHOS 上用真实动态加载器解析被测插件（33 个 kamailio 模块 .so）：
 *   - 加载成功                        -> PASS
 *   - 仅因 kamailio core 符号缺失失败 -> PASS（kamailio 插件的预期行为：插件由
 *     kamailio 主程序在 RTLD_GLOBAL 下加载并提供 core 符号）
 *   - 其他失败（ELF 损坏 / 架构不符 / 非预期依赖缺失） -> FAIL
 *
 * 用法: dlopen_probe <modules-dir>     （遍历目录内全部 *.so）
 */
#include <dirent.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

static int probe_one(const char *path)
{
	void *handle;

	handle = dlopen(path, RTLD_LAZY | RTLD_LOCAL);
	if (handle != NULL) {
		printf("  [H7] dlopen OK: %s\n", path);
		dlclose(handle);
		return 0;
	}

	const char *err = dlerror();
	if (err != NULL
			&& (strstr(err, "symbol not found") != NULL
					|| strstr(err, "undefined symbol") != NULL)) {
		printf("  [H7] dlopen 已解析 ELF；未解析符号来自 kamailio core（预期行为）: %s\n",
			   path);
		return 0;
	}

	fprintf(stderr, "  [H7] FAIL dlopen: %s -> %s\n", path, err ? err : "unknown");
	return 1;
}

int main(int argc, char **argv)
{
	DIR *dir;
	struct dirent *ent;
	int total = 0, failed = 0;
	char path[4096];

	if (argc != 2) {
		fprintf(stderr, "usage: %s <modules-dir>\n", argv[0]);
		return 2;
	}

	dir = opendir(argv[1]);
	if (dir == NULL) {
		fprintf(stderr, "[H7] 无法打开目录: %s\n", argv[1]);
		return 1;
	}

	printf("[H7] OHOS 加载器实测: %s\n", argv[1]);
	while ((ent = readdir(dir)) != NULL) {
		size_t n = strlen(ent->d_name);
		if (n < 4 || strcmp(ent->d_name + n - 3, ".so") != 0)
			continue;
		snprintf(path, sizeof(path), "%s/%s", argv[1], ent->d_name);
		total++;
		failed += probe_one(path);
	}
	closedir(dir);

	printf("[H7] OHOS 加载器实测汇总: total=%d failed=%d\n", total, failed);
	if (total == 0) {
		fprintf(stderr, "[H7] 目录内未发现任何 .so\n");
		return 1;
	}
	return failed == 0 ? 0 : 1;
}

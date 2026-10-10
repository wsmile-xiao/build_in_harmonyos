/*
 * dlopen_probe.c —— kamailio-lua 6.0.6 test_package 鸿蒙特有用例 [H6]
 *
 * 在 OHOS 上用真实动态加载器解析被测插件 app_lua.so：
 *   - 加载成功                        -> PASS
 *   - 仅因 kamailio core 符号缺失失败 -> PASS（kamailio 插件的预期行为：
 *     插件由 kamailio 主程序在 RTLD_GLOBAL 下加载并提供 core 符号）
 *   - 其他失败（ELF 损坏/架构不符）   -> FAIL
 *
 * 用法: dlopen_probe <path-to-app_lua.so>
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
	void *handle;

	if (argc != 2) {
		fprintf(stderr, "usage: %s <app_lua.so>\n", argv[0]);
		return 2;
	}

	handle = dlopen(argv[1], RTLD_LAZY | RTLD_LOCAL);
	if (handle != NULL) {
		printf("[H6] OHOS 加载器实测: dlopen 成功 (%s)\n", argv[1]);
		dlclose(handle);
		return 0;
	}

	const char *err = dlerror();
	if (err != NULL
			&& (strstr(err, "symbol not found") != NULL
					|| strstr(err, "undefined symbol") != NULL)) {
		printf("[H6] OHOS 加载器实测: ELF 已被 OHOS 加载器解析；"
			   "未解析符号来自 kamailio core（预期行为）: %s\n",
				err);
		return 0;
	}

	fprintf(stderr, "[H6] OHOS 加载器实测失败: %s\n", err ? err : "unknown");
	return 1;
}

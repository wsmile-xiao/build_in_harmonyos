/*
 * consumer_dwarves.c — dwarves 1.30 消费者用例（test_package L1）
 *
 * 仅通过已安装的公开头文件 <dwarves.h> 与 libdwarves 链接目标使用该库，
 * 模拟真实第三方使用者：编译、链接、调用公开 API 并验证可观察结果。
 *
 * 调用的公开 API（dwarves.h，均经 llvm-nm 确认导出）：
 *   - dwarves__init() / dwarves__exit()      生命周期管理
 *   - dwarves_print_numeric_version(fp)      输出版本号（可观察输出）
 */
#include <dwarves.h>
#include <stdio.h>

int main(void)
{
	int rc;

	if (dwarves__init() != 0) {
		fprintf(stderr, "consumer: dwarves__init failed\n");
		return 1;
	}

	/* 公开 API：打印数值版本，验证库已正确链接且可调用 */
	printf("dwarves version: ");
	dwarves_print_numeric_version(stdout);
	printf("\n");

	dwarves__exit();
	printf("consumer: OK\n");
	return 0;
}

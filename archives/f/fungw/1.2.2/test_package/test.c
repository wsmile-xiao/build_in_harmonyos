/* fungw 1.2.2 — 消费者视角端到端测试
 *
 * 覆盖 fungw 核心公共 API 的完整工作流：
 *   1. fgw_init()/fgw_uninit()         上下文生命周期
 *   2. fgw_obj_reg()/fgw_func_reg()    宿主对象与 C 函数注册
 *   3. fgw_func_lookup()               全局函数查找
 *   4. fgw_vcall_in()                  类型化调用（FGW_INT 实参）
 *   5. fgw_scall()                     字符串化调用（走实参自动转换）
 *   6. fgw_arg_conv()/fgw_arg_free()   类型转换
 *   7. fgw_dump_ctx()                  上下文转储
 * 任何一步失败都以非 0 退出码结束（conan create 的 test_package 据此判负）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libfungw/fungw.h>

static int failures = 0;

static void check(int ok, const char *what)
{
	printf("%s %s\n", ok ? "ok  " : "FAIL", what);
	if (!ok)
		failures++;
}

/* 注册进 fungw 的宿主 C 函数：两数相加；实参可以是 FGW_INT 或 FGW_STR */
static fgw_error_t consumer_add(fgw_arg_t *res, int argc, fgw_arg_t *argv)
{
	FGW_DECL_CTX;
	long a, b;

	FGW_ARGC_REQ_MATCH(2);
	FGW_ARG_CONV(&argv[1], FGW_LONG);
	FGW_ARG_CONV(&argv[2], FGW_LONG);
	a = argv[1].val.nat_long;
	b = argv[2].val.nat_long;

	res->type = FGW_LONG;
	res->val.nat_long = a + b;
	return FGW_SUCCESS;
}

int main(void)
{
	fgw_ctx_t ctx;
	fgw_obj_t *obj;
	fgw_arg_t res, arg;
	fgw_error_t err;
	char *sres;

	printf("fungw runtime api_ver=0x%x (headers 0x%x)\n", fgw_api_ver, FGW_API_VER);
	check(fgw_api_ver == FGW_API_VER, "运行时与头文件 API 版本一致");

	fgw_init(&ctx, "conan-consumer");

	obj = fgw_obj_reg(&ctx, "math");
	check(obj != NULL, "fgw_obj_reg() 注册宿主对象 'math'");

	check(fgw_func_reg(obj, "add", consumer_add) != NULL, "fgw_func_reg() 注册 C 函数 'add'");
	check(fgw_func_lookup(&ctx, "add") != NULL, "fgw_func_lookup() 全局查到 'add'");

	/* 1) 类型化调用 */
	err = fgw_vcall_in(&ctx, &res, "math", "add", FGW_INT, 2, FGW_INT, 3, 0);
	check(err == FGW_SUCCESS, "fgw_vcall_in() 返回 FGW_SUCCESS");
	check(res.type == FGW_LONG && res.val.nat_long == 5, "vcall add(2,3) == 5");

	/* 2) 字符串化调用（实参自动转换） */
	sres = fgw_scall(&ctx, "add", "20", "22", NULL);
	check(sres != NULL && strcmp(sres, "42") == 0, "scall add(\"20\",\"22\") == \"42\"");
	free(sres);

	/* 3) 类型转换 API */
	arg.type = FGW_STR;
	arg.val.str = (char *)"1234";
	check(fgw_arg_conv(&ctx, &arg, FGW_LONG) == 0, "fgw_arg_conv(FGW_STR -> FGW_LONG) 成功");
	check(arg.val.nat_long == 1234, "转换结果 1234");
	fgw_arg_free(&ctx, &arg);

	/* 4) 上下文转储：确认对象/函数注册生效 */
	printf("--- fgw_dump_ctx ---\n");
	fgw_dump_ctx(&ctx, stdout, "  ");

	fgw_uninit(&ctx);
	fgw_atexit();

	if (failures != 0) {
		printf("%d CHECK(S) FAILED\n", failures);
		return 1;
	}
	printf("ALL CHECKS PASSED\n");
	return 0;
}

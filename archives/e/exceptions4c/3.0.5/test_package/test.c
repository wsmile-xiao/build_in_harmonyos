/*
 * exceptions4c 3.0.5 — 消费者验证用例（test_package）
 *
 * 模拟业务上层组件：仅通过库已安装的公开头文件 e4c.h 与公开 API
 * (E4C_TRY/E4C_CATCH/E4C_THROW/E4C_DEFINE_EXCEPTION/e4c_get_exception)
 * 编译、链接并运行，验证基于异常的收益计算逻辑。
 */
#include <stdio.h>
#include <string.h>
#include "e4c.h"

/* 自定义异常：负数货款 */
E4C_DEFINE_EXCEPTION(NegativeAmountException, "negative amount", RuntimeException);

static double safe_discount_price(double price, double discount) {
    double result = 0.0;
    E4C_TRY {
        if (price < 0.0 || discount < 0.0) {
            E4C_THROW(NegativeAmountException, "price or discount is negative");
        }
        result = price * discount;
    }
    E4C_CATCH(NegativeAmountException) {
        const e4c_exception *ex = e4c_get_exception();
        fprintf(stdout, "caught: %s: %s\n", ex->type->name, ex->message);
        result = -1.0;
    }
    return result;
}

int main(void) {
    e4c_context_begin(E4C_FALSE);
    /* 1) 正常路径 */
    if (safe_discount_price(100.0, 0.8) != 80.0) {
        fprintf(stderr, "FAIL: normal path\n");
        e4c_context_end();
        return 1;
    }
    /* 2) 异常路径：负数输入必须触发 NegativeAmountException 并被捕获 */
    if (safe_discount_price(-5.0, 0.5) != -1.0) {
        fprintf(stderr, "FAIL: exception path\n");
        e4c_context_end();
        return 1;
    }
    /* 3) 校验异常消息内容 */
    double r = safe_discount_price(10.0, -1.0);
    if (r != -1.0) {
        fprintf(stderr, "FAIL: second exception path\n");
        e4c_context_end();
        return 1;
    }
    e4c_context_end();
    fprintf(stdout, "exceptions4c consumer test: PASS\n");
    return 0;
}
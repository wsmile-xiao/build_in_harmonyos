// consumer.c — calceph 5.0.0 消费测试最小程序
// 调用 calceph API 证明库可被实际链接和调用（R34 非空壳）。
// calceph_getmaxsupportedorder() 无对象参数、不依赖历表数据文件，
// 返回整数阶数（>=0 即证明函数可解析、库可链接调用）。
#include <stdio.h>
#include "calceph.h"

int main(void) {
    int n = calceph_getmaxsupportedorder(0);
    // 返回值 >= 0 即证明函数可解析、库可链接调用（无数据文件也可运行）
    printf("calceph_getmaxsupportedorder(0) = %d\n", n);
    if (n < 0) {
        return 1;
    }
    return 0;
}
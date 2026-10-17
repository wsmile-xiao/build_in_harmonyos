/*
 * consumer_sensor.c — medianfilter 1.0.0 消费者验证用例
 *
 * 模拟业务上层组件「ADC 传感器读数降噪模块」：仅通过库已安装/导出的
 * 公开头文件 (MedianFilter.h)、公开 API (MEDIANFILTER_Init /
 * MEDIANFILTER_Insert) 与正常链接目标 (libmedianfilter.a) 编译、链接
 * 并运行。不包含库私有头文件、不调用内部符号、不复用库内部测试构建
 * 目录。
 *
 * 业务场景：12-bit ADC 温度传感器序列混入盐椒脉冲噪声，业务层用
 * 窗口 5 的中值滤波器实时去噪。可观察结果：原始序列的最大脉冲
 * (4095) 被完全消除，去噪后所有输出落在有效量程内且中值正确。
 */
#include <MedianFilter.h>
#include <stdio.h>

#define WINDOW 5
#define N 9

int main(void)
{
    /* 模拟 ADC 读数：正常值 1000..1010，混入两个尖峰 4095/0 */
    const int raw[N] = {1005, 1000, 4095, 1002, 1008, 1001, 0, 1006, 1004};

    sMedianFilter_t filter;
    sMedianNode_t nodes[WINDOW];
    filter.numNodes = WINDOW;
    filter.medianBuffer = nodes;
    if (MEDIANFILTER_Init(&filter) != 0) {
        fprintf(stderr, "CONSUMER_FAIL: MEDIANFILTER_Init\n");
        return 2;
    }

    int out[N];
    for (int i = 0; i < N; i++)
        out[i] = MEDIANFILTER_Insert(&filter, raw[i]);

    /* 断言 1：原始尖峰 4095 出现在去噪输出中时已被消除
       （窗口 5 满后 median 只取中间值，不可能等于 4095 或 0） */
    for (int i = WINDOW - 1; i < N; i++) {
        if (out[i] == 4095 || out[i] == 0) {
            fprintf(stderr, "CONSUMER_FAIL: spike survived at i=%d (out=%d)\n", i, out[i]);
            return 1;
        }
    }
    /* 断言 2：全窗口满后输出均落在有效量程 [1000,1010] 内 */
    for (int i = WINDOW - 1; i < N; i++) {
        if (out[i] < 1000 || out[i] > 1010) {
            fprintf(stderr, "CONSUMER_FAIL: out-of-range median at i=%d (out=%d)\n", i, out[i]);
            return 1;
        }
    }
    /* 断言 3：窗口 5 满后首个完整窗口 {1005,1000,4095,1002,1008} 的中值 = 1005 */
    if (out[WINDOW - 1] != 1005) {
        fprintf(stderr, "CONSUMER_FAIL: median of first full window = %d, expected 1005\n",
                out[WINDOW - 1]);
        return 1;
    }

    printf("consumer: ADC spike removed, all medians in [1000,1010], "
           "first-full-window median=%d -> OK\n", out[WINDOW - 1]);
    return 0;
}

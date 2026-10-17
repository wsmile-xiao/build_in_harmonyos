// 消费者用例（模拟业务上层组件/应用）：
// 仅通过 access_profiler 已安装导出的公开头文件 access_profiler.hpp 与公开 API
// （access_profiler::instrument_type<T> 模板，经其 operator new/delete 实现字段访问计数）
// 与正常链接目标（libaccess_profiler.a）使用该三方库，
// 验证第三方使用者在 OHOS PC 上可编译、链接、调用并正常运行。
//
// 业务场景：上层应用维护一个"温度传感器采样记录"结构，模拟周期采样与聚合，
// 并用 access_profiler 记录每个字段的访问热区（offset -> count）。
// 可观察结果：
//   1. stdout 打印聚合结果（由真实字段读写计算得出）；
//   2. 进程退出时库的 print_report() 自动写出 access_profile.out，
//      其中包含该业务类型的字段访问计数 —— 由外部校验脚本核对。
#include <stdio.h>
#include <string.h>

#include "access_profiler.hpp"

namespace {

// 业务类型：模拟上层组件中一个被反复读写的采样记录。
// 布局（aarch64，默认对齐）：seq 偏移 0，temperature 偏移 4，humidity 偏移 8。
struct sensor_sample : access_profiler::instrument_type<sensor_sample>
{
    sensor_sample() : seq(0), temperature(0), humidity(0) {}
    int seq;
    int temperature;
    int humidity;
};

} // namespace

int main()
{
    const int samples = 100;

    sensor_sample* s = new sensor_sample;
    if (s == nullptr) {
        fprintf(stderr, "consumer: allocation failed\n");
        return 1;
    }

    // 模拟业务负载：周期采样并聚合温度/湿度
    for (int i = 1; i <= samples; ++i) {
        s->seq = i;                  // 写 seq（偏移 0）
        s->temperature += 1;         // 写 temperature（偏移 4）
        s->humidity = s->temperature * 2 + i; // 读 temperature、写 humidity
    }

    const int expected_temp = samples;
    const int expected_humidity = expected_temp * 2 + samples;
    if (s->seq != samples || s->temperature != expected_temp
        || s->humidity != expected_humidity) {
        fprintf(stderr, "consumer: field check failed "
            "(seq=%d temp=%d hum=%d)\n", s->seq, s->temperature, s->humidity);
        delete s;
        return 1;
    }

    printf("consumer: %d samples aggregated -> "
           "seq=%d temperature=%d humidity=%d\n",
           samples, s->seq, s->temperature, s->humidity);

    delete s;

    // 依赖库静态析构自动写出 access_profile.out（字段访问热区报告）
    return 0;
}

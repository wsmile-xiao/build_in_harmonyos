// test_package 消费者验证：仅用已安装的公开头文件 access_profiler.hpp 与
// 公开 API access_profiler::instrument_type<T>，链接 libaccess_profiler.a，
// 验证包在 OHOS 上可编译、链接、调用并正常运行。
#include <stdio.h>

#include "access_profiler.hpp"

struct sensor_sample : access_profiler::instrument_type<sensor_sample>
{
    sensor_sample() : seq(0), temperature(0), humidity(0) {}
    int seq;
    int temperature;
    int humidity;
};

int main()
{
    sensor_sample* s = new sensor_sample;
    for (int i = 1; i <= 10; ++i) {
        s->seq = i;
        s->temperature += 1;
        s->humidity = s->temperature * 2 + i;
    }
    const bool ok = (s->seq == 10 && s->temperature == 10 && s->humidity == 30);
    printf(ok ? "test_access_profiler PASS (seq=%d temp=%d hum=%d)\n"
              : "test_access_profiler FAIL (seq=%d temp=%d hum=%d)\n",
           s->seq, s->temperature, s->humidity);
    delete s;
    return ok ? 0 : 1;
}

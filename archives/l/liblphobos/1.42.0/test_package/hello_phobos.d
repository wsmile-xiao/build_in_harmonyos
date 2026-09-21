import std.stdio;
import std.algorithm;
import std.range;
import std.format;
import std.conv;
import std.json;
import std.string;
import std.datetime;

/*
 * R34 反空壳消费者用例（鸿蒙新增）：只用"真实 D 编译器 + liblphobos 共享库"
 * 才能编译并跑出正确结果。本程序作为 liblphobos 包的消费者，链接
 * libphobos2-ldc-shared.so.112 + libdruntime-ldc-shared.so.112（-defaultlib
 * 覆盖为 -shared 后缀），验证 Phobos 共享库在 OHOS 上的真实可用性。
 * 覆盖模块：std.stdio/std.algorithm/std.range/std.format/std.conv/
 *           std.json/std.string/std.datetime（比 ldc 包 hello.d 覆盖更广）。
 */
void main()
{
    // ① 排序 + map + reduce（std.algorithm/std.range）
    auto nums = [3, 1, 4, 1, 5, 9, 2, 6];
    auto sorted = nums.dup.sort;
    writeln("sorted:  ", sorted.array);
    writeln("doubled: ", sorted.map!(a => a * 2).array);

    // ② 格式化 + 类型转换（std.format/std.conv）
    writeln(format("summary: n=%d max=%d", 8, 9));
    writeln("conv:    ", to!string(42));

    // ③ JSON 解析（std.json，纯 Phobos 实现）
    auto j = parseJSON(`{"name":"ohos","ver":112,"ok":true}`);
    writeln("json:    ", j["name"].str, "/", j["ver"].integer, "/", j["ok"].boolean);

    // ④ 字符串处理（std.string）
    writeln("string:  ", toUpper("phobos-on-ohos"));

    // ⑤ 时间戳（std.datetime，POSIX 路径）
    writeln("clock:   ", Clock.currTime().toUnixTime() > 0);
}

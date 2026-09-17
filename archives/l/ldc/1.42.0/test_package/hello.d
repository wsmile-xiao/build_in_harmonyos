import std.stdio;
import std.algorithm;
import std.range;
import std.format;
import std.conv;

/*
 * R34 反空壳测试程序：只用"真实编译器 + 真实运行时"才能编译并跑出正确结果。
 * 刻意使用 Phobos 的算法/区间/格式化模块（而非裸 core），以便同时验证
 * druntime 与 Phobos 都被正确构建并链接进来了。
 */
void main()
{
    auto nums = [3, 1, 4, 1, 5, 9, 2, 6];
    auto sorted = nums.dup.sort;

    writeln("sorted:  ", sorted);
    writeln("doubled: ", sorted.map!(a => a * 2).array);
    writeln(format("summary: n=%d max=%d", sorted.length, sorted.reduce!max));
    writeln("conv:    ", to!string(42));
}

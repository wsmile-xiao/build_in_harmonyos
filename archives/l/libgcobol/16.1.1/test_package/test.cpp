/* 真实断言：libgcobol 运行时核心数值接口。
 *
 * libgcobol 不对外安装 C++ 头文件——它的接口是 GCOBOL 前端（gcc/cobol）生成的
 * 代码与运行时库之间约定的 extern "C" ABI（见 libgcobol/libgcobol.h 顶部注释），
 * 故此处按 ABI 直接声明所需原型，链接 libgcobol.so 做真实计算断言。
 */
#include <cstdio>

extern "C" __int128 __gg__power_of_ten(int n);

int main() {
    __int128 p2 = __gg__power_of_ten(2);
    if (p2 != 100) {
        std::fprintf(stderr, "__gg__power_of_ten(2) 应为 100，实得 %lld\n", (long long)p2);
        return 1;
    }
    __int128 p0 = __gg__power_of_ten(0);
    if (p0 != 1) {
        std::fprintf(stderr, "__gg__power_of_ten(0) 应为 1\n");
        return 1;
    }
    __int128 p5 = __gg__power_of_ten(5);
    if (p5 != 100000) {
        std::fprintf(stderr, "__gg__power_of_ten(5) 应为 100000\n");
        return 1;
    }
    std::printf("libgcobol: __gg__power_of_ten(2)=100, (0)=1, (5)=100000 通过\n");
    return 0;
}

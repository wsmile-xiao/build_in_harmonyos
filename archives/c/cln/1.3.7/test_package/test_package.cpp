/* 消费者验证：真实调用 CLN 库 API 并断言行为。
 * 1) 乘法循环构造 2^100，与移位路径 cl_I(1)<<100 交叉核对（两条独立代码路径）；
 * 2) integer_length(2^100) == 101 位长断言；
 * 3) 精确除法 exquo(2^100, 2^50)==2^50 与 mod(2^100,5)==1 断言；
 * 4) 高精度浮点 sqrt 回乘精度断言。 */
#include <cln/integer.h>
#include <cln/float.h>
#include <cln/real.h>
#include <iostream>

using namespace std;
using namespace cln;

int main()
{
    // 1) 大整数乘法：循环乘 2 得 2^100
    cl_I two_pow_100 = (cl_I)1;
    for (int i = 0; i < 100; i++)
        two_pow_100 = two_pow_100 * 2;

    // 移位路径独立构造，与乘法路径交叉核对
    cl_I two_pow_100_shift = cl_I(1) << 100;
    if (two_pow_100 != two_pow_100_shift)
    {
        cerr << "2^100 mul-loop != shift path" << endl;
        return 1;
    }

    // 2) 位长：2^100 的二进制位长为 101
    if (integer_length(two_pow_100) != 101)
    {
        cerr << "integer_length(2^100) != 101" << endl;
        return 1;
    }

    // 3) 精确除法（2^100 / 2^50 = 2^50）与模余（2^100 ≡ 1 mod 5）
    cl_I two_pow_50 = cl_I(1) << 50;
    cl_I q = exquo(two_pow_100, two_pow_50);
    if (q != two_pow_50)
    {
        cerr << "exquo(2^100, 2^50) != 2^50" << endl;
        return 1;
    }
    cl_I r = mod(two_pow_100, (cl_I)5);
    if (r != 1)
    {
        cerr << "mod(2^100,5) != 1" << endl;
        return 1;
    }

    // 4) 双精度格式下 sqrt 回乘精度：|s^2 - 2| < 2^-40
    //    （float_format(15)≈双精度，sqrt 回乘误差约数个 ulp≈2^-51，2^-40 为
    //    有意义且可稳定通过的小容差；scale_float(1,-40) 即 2^-40）
    cl_F f = cl_float(2, float_format(15));
    cl_F s = sqrt(f);
    cl_F back = s * s;
    cl_F tol = scale_float(cl_float(1, float_format(15)), -40);
    if (!(abs(back - f) < tol))
    {
        cerr << "sqrt(2)^2 - 2 not < 2^-40" << endl;
        return 1;
    }

    cout << "cln consumer test passed (2^100 mul==shift, bitlen 101, exquo/mod ok, sqrt ok)" << endl;
    return 0;
}

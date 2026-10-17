// test_package/test_vol.cpp — Vol 1.5.4 consumer test (R34)
//
// 真实调用 libVol API 并校验结果（非空壳，对照 coin-osi osi_smoke 模式）：
//   - VOL_dvector::operator=(double)：定义于 VolVolume.cpp 的非内联符号，
//     引用它强制链接器从 libVol.a 解析真实符号——符号缺失/ABI 错配的坏包
//     在链接期即可检出
//   - VOL_dvector copy-assign（operator=(const VOL_dvector&)，非内联）
//   - VOL_dvector::cc() 凸组合并断言数值
//   - VOL_ivector::operator=(int)（非内联符号）
#include <VolVolume.hpp>
#include <cstdio>

int main()
{
    // VOL_dvector 构造 + operator=(double)（真实库符号）+ 取值校验
    VOL_dvector d(3);
    d = 2.5;
    if (d.size() != 3 || d[0] != 2.5 || d[1] != 2.5 || d[2] != 2.5) {
        std::fprintf(stderr, "FAIL: VOL_dvector operator=(double) check failed\n");
        return 2;
    }

    // copy-assign（operator=(const VOL_dvector&)，非内联符号）+ 取值校验
    VOL_dvector d2(3);
    d2 = d;
    if (d2.size() != 3 || d2[0] != 2.5 || d2[1] != 2.5 || d2[2] != 2.5) {
        std::fprintf(stderr, "FAIL: VOL_dvector copy-assign check failed\n");
        return 3;
    }

    // cc() 凸组合：d = 0.5*d + 0.5*w = 1.75
    VOL_dvector w(3);
    w = 1.0;
    d.cc(0.5, w);
    if (d[0] != 1.75 || d[1] != 1.75 || d[2] != 1.75) {
        std::fprintf(stderr, "FAIL: VOL_dvector cc() check failed\n");
        return 4;
    }

    // VOL_ivector 构造 + operator=(int)（非内联符号）
    VOL_ivector iv(4);
    iv = 7;
    if (iv.size() != 4 || iv[0] != 7 || iv[3] != 7) {
        std::fprintf(stderr, "FAIL: VOL_ivector operator=(int) check failed\n");
        return 5;
    }

    std::printf("OK: vol 1.5.4 smoke passed\n");
    return 0;
}

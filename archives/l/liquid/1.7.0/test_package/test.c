/* L1 link test — liquid 1.7.0 test_package
 * 验证头文件可用、库可链接、基本对象创建/销毁无泄漏。
 */
#include <stdio.h>
#include <stdlib.h>
#include <liquid/liquid.h>

int main(void)
{
    printf("liquid-dsp version: %s\n", liquid_version);

    /* 创建并销毁一个 AGC 对象（核心 DSP 对象） */
    agc_crcf q = agc_crcf_create();
    if (q == NULL) {
        fprintf(stderr, "FAIL: agc_crcf_create returned NULL\n");
        return 1;
    }
    agc_crcf_set_bandwidth(q, 0.01f);
    agc_crcf_destroy(q);

    /* 创建并销毁一个 NCO（数控振荡器）验证 libm 链路 */
    nco_crcf nco = nco_crcf_create(LIQUID_NCO);
    if (nco == NULL) {
        fprintf(stderr, "FAIL: nco_crcf_create returned NULL\n");
        return 1;
    }
    nco_crcf_set_frequency(nco, 0.1f * 2.0f * 3.14159265f);
    nco_crcf_pll_step(nco, 0.01f);
    nco_crcf_destroy(nco);

    printf("L1 link test PASS\n");
    return 0;
}

// test_lfortran_runtime.c — lfortran-runtime 0.61.0 消费者链接级冒烟测试
//
// 真实调用被测包的 C 运行时 API（R34 非空壳）：数值 intrinsic、数组归约、
// 运行时随机数、FPE trap 设置（覆盖本库 musl 适配补丁所在的代码路径）。
// 纯计算 + 标准输出，无外部文件/网络依赖（无头环境纪律）。
#include <lfortran/impure/lfortran_intrinsics.h>

#include <math.h>
#include <stdio.h>

int main(void) {
    int failures = 0;

    // 1) 双精度数值 intrinsic：sin(0)=0，cos(0)=1
    double s = _lfortran_dsin(0.0);
    double c = _lfortran_dcos(0.0);
    printf("_lfortran_dsin(0.0) = %.6f\n", s);
    printf("_lfortran_dcos(0.0) = %.6f\n", c);
    if (fabs(s - 0.0) > 1e-12) { failures++; }
    if (fabs(c - 1.0) > 1e-12) { failures++; }

    // 2) 数组归约：sum([1,2,3,4]) = 10
    double v[4] = {1.0, 2.0, 3.0, 4.0};
    double total = _lfortran_sum(4, v);
    printf("_lfortran_sum(4, [1,2,3,4]) = %.6f\n", total);
    if (fabs(total - 10.0) > 1e-12) { failures++; }

    // 3) 运行时随机数：设置种子后可取得 [0,1) 内的值
    _lfortran_init_random_seed(42u);
    double r = _lfortran_random();
    printf("_lfortran_random() = %.6f\n", r);
    if (!(r >= 0.0 && r < 1.0)) { failures++; }

    // 4) FPE trap 设置（mask 1 = LCOMPILERS_FE_INVALID）。
    //    该函数在 OHOS/musl 上原先引用未定义的 feenableexcept，本库补丁以
    //    ARMv8-A FPCR 直写替代；此处真实调用即验证补丁后的符号可解析、可执行。
    _lfortran_enable_fpe_traps(1);
    printf("_lfortran_enable_fpe_traps(1) ok\n");
    if (fabs(_lfortran_dsin(0.0)) > 1e-12) { failures++; }

    if (failures != 0) {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("PASS: lfortran-runtime 0.61.0 consumer smoke OK\n");
    return 0;
}

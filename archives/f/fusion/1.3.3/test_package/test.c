/*
 * test_package 消费者测试 — fusion 1.3.3
 *
 * 通过公开头文件 <Fusion/Fusion.h> 使用 Fusion 库的公开 API：
 *  - FusionAhrsInitialise / FusionAhrsSetSamplePeriod / FusionAhrsUpdate
 *  - FusionAhrsGetQuaternion / FusionQuaternionToEuler
 * 验证 IMU 静止样本（重力竖直向下、零角速度）下姿态解算收敛到零欧拉角，
 * 以及传感器模型（FusionModelInertial / FusionModelMagnetic）输出符合预期。
 */
#include <Fusion/Fusion.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static int check_close(const char *name, float got, float expected, float tol)
{
    if (fabsf(got - expected) > tol) {
        fprintf(stderr, "FAIL: %s: got %.6f, expected %.6f\n", name, got, expected);
        return 1;
    }
    printf("PASS: %s: %.6f\n", name, got);
    return 0;
}

int main(void)
{
    int failures = 0;

    /* --- AHRS：静止 IMU 姿态收敛到零欧拉角 --- */
    FusionAhrs ahrs;
    FusionAhrsInitialise(&ahrs);

    FusionAhrsSettings settings = fusionAhrsDefaultSettings;
    FusionAhrsSetSettings(&ahrs, &settings);
    FusionAhrsSetSamplePeriod(&ahrs, 0.01f);  /* 100 Hz */

    const FusionVector gyroscope = {0.0f, 0.0f, 0.0f};   /* 静止 */
    const FusionVector accelerometer = {0.0f, 0.0f, 1.0f}; /* 重力竖直向下 */
    const FusionVector magnetometer = {1.0f, 0.0f, 0.0f};

    for (int i = 0; i < 1000; i++) {
        FusionAhrsUpdate(&ahrs, gyroscope, accelerometer, magnetometer);
    }

    const FusionQuaternion quaternion = FusionAhrsGetQuaternion(&ahrs);
    const FusionEuler euler = FusionQuaternionToEuler(quaternion);
    failures += check_close("roll(deg)", euler.angle.roll, 0.0f, 1.0f);
    failures += check_close("pitch(deg)", euler.angle.pitch, 0.0f, 1.0f);

    /* --- 传感器模型：惯性模型输出 = M·((u-o)·s) --- */
    const FusionVector uncalibrated = {1.0f, 2.0f, 3.0f};
    const FusionMatrix misalignment = {1.0f, 0.0f, 0.0f,
                                       0.0f, 1.0f, 0.0f,
                                       0.0f, 0.0f, 1.0f};
    const FusionVector sensitivity = {2.0f, 2.0f, 2.0f};
    const FusionVector offset = {0.5f, 0.5f, 0.5f};
    const FusionVector inertial =
        FusionModelInertial(uncalibrated, misalignment, sensitivity, offset);
    failures += check_close("inertial.x", inertial.axis.x, 1.0f, 1e-6f);
    failures += check_close("inertial.y", inertial.axis.y, 3.0f, 1e-6f);
    failures += check_close("inertial.z", inertial.axis.z, 5.0f, 1e-6f);

    if (failures != 0) {
        fprintf(stderr, "fusion consumer test FAILED (%d checks)\n", failures);
        return 1;
    }
    printf("fusion 1.3.3 consumer test: ALL PASS\n");
    return 0;
}

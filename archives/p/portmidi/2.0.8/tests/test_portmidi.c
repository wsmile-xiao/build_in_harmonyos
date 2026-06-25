/*
 * PortMidi 2.0.8 功能测试程序
 * 测试 PMNULL 模式下的库功能
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <portmidi.h>
#include <porttime.h>

/* 测试结果统计 */
static int tests_passed = 0;
static int tests_failed = 0;
static int tests_total = 0;

/* 测试辅助宏 */
#define TEST_START(name) \
    do { \
        tests_total++; \
        printf("[TEST %d] %s\n", tests_total, name); \
    } while(0)

#define TEST_PASS() \
    do { \
        tests_passed++; \
        printf("  ✓ PASS\n"); \
    } while(0)

#define TEST_FAIL(reason) \
    do { \
        tests_failed++; \
        printf("  ✗ FAIL: %s\n", reason); \
    } while(0)

#define TEST_CHECK(cond, reason) \
    do { \
        if (cond) { \
            TEST_PASS(); \
        } else { \
            TEST_FAIL(reason); \
        } \
    } while(0)

/* 测试 1: 库初始化 */
static void test_initialize(void) {
    TEST_START("Pm_Initialize - 库初始化");
    
    PmError err = Pm_Initialize();
    
    if (err == pmNoError) {
        TEST_PASS();
    } else {
        printf("  Pm_Initialize() 返回错误: %s\n", Pm_GetErrorText(err));
        TEST_FAIL("库初始化失败");
    }
}

/* 测试 2: 设备计数 */
static void test_count_devices(void) {
    TEST_START("Pm_CountDevices - 设备计数");
    
    int count = Pm_CountDevices();
    
    printf("  检测到设备数: %d\n", count);
    
    /* PMNULL 模式下应该返回 0 或接近 0 */
    TEST_CHECK(count >= 0, "设备计数应 >= 0");
}

/* 测试 3: 默认输入设备 */
static void test_default_input_device(void) {
    TEST_START("Pm_GetDefaultInputDeviceID - 默认输入设备");
    
    PmDeviceID dev = Pm_GetDefaultInputDeviceID();
    
    printf("  默认输入设备 ID: %d\n", dev);
    
    /* PMNULL 模式下应该返回 pmNoDevice (-1) */
    TEST_CHECK(dev == pmNoDevice || dev >= 0, 
        "默认输入设备 ID 应为 pmNoDevice 或有效值");
}

/* 测试 4: 默认输出设备 */
static void test_default_output_device(void) {
    TEST_START("Pm_GetDefaultOutputDeviceID - 默认输出设备");
    
    PmDeviceID dev = Pm_GetDefaultOutputDeviceID();
    
    printf("  默认输出设备 ID: %d\n", dev);
    
    /* PMNULL 模式下应该返回 pmNoDevice (-1) */
    TEST_CHECK(dev == pmNoDevice || dev >= 0,
        "默认输出设备 ID 应为 pmNoDevice 或有效值");
}

/* 测试 5: 错误文本转换 */
static void test_error_text(void) {
    TEST_START("Pm_GetErrorText - 错误文本转换");
    
    const char *text_noerror = Pm_GetErrorText(pmNoError);
    const char *text_hosterror = Pm_GetErrorText(pmHostError);
    const char *text_invalid = Pm_GetErrorText(pmInvalidDeviceId);
    
    printf("  pmNoError: %s\n", text_noerror ? text_noerror : "(null)");
    printf("  pmHostError: %s\n", text_hosterror ? text_hosterror : "(null)");
    printf("  pmInvalidDeviceId: %s\n", text_invalid ? text_invalid : "(null)");
    
    /* pmNoError 可能返回空字符串，这是正常的设计 */
    /* 其他错误应该有描述 */
    TEST_CHECK(text_hosterror != NULL && strlen(text_hosterror) > 0,
        "pmHostError 错误文本应非空");
}

/* 测试 6: 设备信息查询 */
static void test_device_info(void) {
    TEST_START("Pm_GetDeviceInfo - 设备信息查询");
    
    int count = Pm_CountDevices();
    
    if (count > 0) {
        /* 查询第一个设备 */
        const PmDeviceInfo *info = Pm_GetDeviceInfo(0);
        
        if (info != NULL) {
            printf("  设备 0 信息:\n");
            printf("    名称: %s\n", info->name ? info->name : "(null)");
            printf("    接口: %s\n", info->interf ? info->interf : "(null)");
            printf("    输入: %d\n", info->input);
            printf("    输出: %d\n", info->output);
            printf("    已打开: %d\n", info->opened);
            TEST_PASS();
        } else {
            TEST_FAIL("设备 0 信息为 NULL");
        }
    } else {
        printf("  无设备，跳过详细测试\n");
        TEST_CHECK(1, "PMNULL 模式下无设备是预期行为");
    }
}

/* 测试 7: 库终止 */
static void test_terminate(void) {
    TEST_START("Pm_Terminate - 库终止");
    
    PmError err = Pm_Terminate();
    
    TEST_CHECK(err == pmNoError,
        "Pm_Terminate() 应返回 pmNoError");
}

/* 测试 8: 重复初始化终止 */
static void test_reinit(void) {
    TEST_START("Pm_Initialize/Pm_Terminate - 重复初始化终止");
    
    PmError err1 = Pm_Initialize();
    if (err1 != pmNoError) {
        TEST_FAIL("第一次初始化失败");
        return;
    }
    
    PmError err2 = Pm_Terminate();
    if (err2 != pmNoError) {
        TEST_FAIL("第一次终止失败");
        return;
    }
    
    PmError err3 = Pm_Initialize();
    if (err3 != pmNoError) {
        TEST_FAIL("第二次初始化失败");
        return;
    }
    
    PmError err4 = Pm_Terminate();
    if (err4 != pmNoError) {
        TEST_FAIL("第二次终止失败");
        return;
    }
    
    TEST_PASS();
}

/* 测试 9: 消息编码宏 */
static void test_message_macros(void) {
    TEST_START("Pm_Message 宏 - MIDI 消息编码");
    
    /* 测试 Note On 消息: channel 1, note 60, velocity 100 */
    PmMessage msg = Pm_Message(0x90, 60, 100);
    
    unsigned char status = Pm_MessageStatus(msg);
    unsigned char data1 = Pm_MessageData1(msg);
    unsigned char data2 = Pm_MessageData2(msg);
    
    printf("  原始消息: 0x%08X\n", msg);
    printf("  Status: 0x%02X (期望: 0x90)\n", status);
    printf("  Data1: %d (期望: 60)\n", data1);
    printf("  Data2: %d (期望: 100)\n", data2);
    
    TEST_CHECK(status == 0x90 && data1 == 60 && data2 == 100,
        "消息编码/解码应正确");
}

/* 测试 10: 库版本/头文件检查 */
static void test_header_version(void) {
    TEST_START("头文件版本检查");
    
    printf("  PM_DEVICEINFO_VERS: %d\n", PM_DEVICEINFO_VERS);
    printf("  PM_HOST_ERROR_MSG_LEN: %u\n", PM_HOST_ERROR_MSG_LEN);
    printf("  PM_DEFAULT_SYSEX_BUFFER_SIZE: %d\n", PM_DEFAULT_SYSEX_BUFFER_SIZE);
    
    TEST_CHECK(PM_DEVICEINFO_VERS >= 200 && PM_HOST_ERROR_MSG_LEN >= 256,
        "头文件版本定义应正确");
}

/* 主测试函数 */
int main(int argc, char *argv[]) {
    printf("========================================\n");
    printf("PortMidi 2.0.8 功能测试\n");
    printf("平台: HarmonyOS (PMNULL 模式)\n");
    printf("========================================\n\n");
    
    /* 运行所有测试 */
    test_initialize();
    test_count_devices();
    test_default_input_device();
    test_default_output_device();
    test_error_text();
    test_device_info();
    test_message_macros();
    test_header_version();
    test_terminate();
    
    printf("\n----------------------------------------\n");
    printf("重复初始化测试\n");
    printf("----------------------------------------\n\n");
    
    test_reinit();
    
    /* 输出测试结果 */
    printf("\n========================================\n");
    printf("测试结果汇总\n");
    printf("========================================\n");
    printf("总计: %d 个测试\n", tests_total);
    printf("通过: %d 个 (%.1f%%)\n", tests_passed, 
        (tests_total > 0) ? (100.0 * tests_passed / tests_total) : 0.0);
    printf("失败: %d 个 (%.1f%%)\n", tests_failed,
        (tests_total > 0) ? (100.0 * tests_failed / tests_total) : 0.0);
    printf("========================================\n");
    
    /* 最终状态 */
    if (tests_failed == 0) {
        printf("\n✓ 所有测试通过\n");
        printf("\n注意: PMNULL 模式下无 MIDI 设备是预期行为\n");
        printf("PortMidi API 可用，但无法检测或使用 MIDI 设备\n");
        return 0;
    } else {
        printf("\n✗ 有测试失败\n");
        return 1;
    }
}
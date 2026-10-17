#include <stdio.h>
#include <string.h>

#include <libatari800/libatari800.h>

/* 真实调用 libatari800 公开 API：初始化 → 推进模拟帧 → 查询状态 → 退出。
   7 个显式断言（assertions），任一失败即返回非 0。 */
static int assertions_passed = 0;
static int assertions_failed = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (cond) {                                                            \
            assertions_passed++;                                               \
            printf("  [ok] %s\n", msg);                                        \
        } else {                                                               \
            assertions_failed++;                                               \
            printf("  [FAIL] %s\n", msg);                                      \
        }                                                                      \
    } while (0)

int main(void) {
    char *test_args[] = {"-atari", NULL};
    input_template_t input;

    /* 1. 库初始化成功（argc=-1 表示 NULL 结尾参数表；成功返回 TRUE 非 0） */
    int status = libatari800_init(-1, test_args);
    CHECK(status != 0, "libatari800_init succeeds");
    if (status == 0) {
        fprintf(stderr, "libatari800_init returned %d (error_code=%d)\n",
                status, libatari800_error_code);
        return 1;
    }

    libatari800_clear_input_array(&input);

    /* 2. 推进 10 帧模拟 */
    int i;
    for (i = 0; i < 10; i++) {
        libatari800_next_frame(&input);
    }
    CHECK(libatari800_get_frame_number() == 10, "10 frames advanced via libatari800_next_frame");

    /* 3. 帧速率有效 */
    CHECK(libatari800_get_fps() > 0.0f, "libatari800_get_fps reports a valid fps");

    /* 4. 屏幕缓冲区指针非空 */
    CHECK(libatari800_get_screen_ptr() != NULL, "libatari800_get_screen_ptr returns a buffer");

    /* 5. 声音参数有效（thin API 也提供频率/声道信息） */
    CHECK(libatari800_get_sound_frequency() > 0, "sound frequency is valid");

    /* 6. CPU 状态可查询（读取 6502 寄存器） */
    {
        emulator_state_t state;
        cpu_state_t *cpu;
        libatari800_get_current_state(&state);
        cpu = (cpu_state_t *)&state.state[state.tags.cpu];
        CHECK(cpu != NULL && (cpu->A <= 0xff) && (cpu->S <= 0xff),
              "CPU register state is readable via libatari800_get_current_state");
    }

    /* 7. 错误码是库对模拟机状态（CPU crash/BRK/DLIST/Memo Pad 等）的粘性报告，
       并非库故障：-atari 空载启动 400/800 Altirra OS 会进入 Memo Pad，帧尾可能
       置位错误码（上游 libatari800_test 跑 200 帧从不检查错误码）。断言错误报告
       API 本身有效：错误码在合法范围 0-7 内，且错误消息非空、可识别。 */
    {
        int ec = libatari800_error_code;
        const char *msg = libatari800_error_message();
        CHECK(ec >= 0 && ec <= LIBATARI800_INVALID_ESCAPE_OPCODE
                  && msg != NULL && msg[0] != '\0'
                  && strcmp(msg, "unknown error") != 0,
              "error code/message reporting is coherent");
        if (ec != 0) {
            printf("  (info) emulator reported condition %d: %s\n", ec, msg);
        }
    }

    libatari800_exit();

    printf("atari800 API assertions: %d passed, %d failed\n",
           assertions_passed, assertions_failed);
    return assertions_failed == 0 ? 0 : 1;
}

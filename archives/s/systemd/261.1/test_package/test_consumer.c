/* test_consumer.c — systemd 261.1 消费者用例（R34/消费者硬门禁）
 *
 * 模拟业务上层组件：仅通过 systemd 已安装/导出的公开头文件
 * (systemd/sd-event.h) 与公开 API（sd_event_new/sd_event_add_time/
 * sd_event_run/sd_event_unref）使用 libsystemd 客户端库。
 * 验证第三方使用者能否编译、链接、调用并正常运行：
 *   - 创建 sd-event 事件循环；
 *   - 注册一个 100ms 的 timer 回调；
 *   - 运行循环，断言回调确实被执行（可观察结果：counter 自增 + 打印）；
 *   - 清理资源后退出 0。
 */
#include <systemd/sd-event.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

static unsigned fired = 0;

static int on_timer(sd_event_source *s, uint64_t usec, void *userdata) {
        (void) s;
        (void) usec;
        (void) userdata;
        fired++;
        return 1; /* 触发后结束事件循环 */
}

int main(void) {
        sd_event *e = NULL;
        sd_event_source *src = NULL;
        int r;

        r = sd_event_new(&e);
        if (r < 0) {
                fprintf(stderr, "CONSUMER_FAIL: sd_event_new: %s\n", strerror(-r));
                return 1;
        }

        r = sd_event_add_time(e, &src, CLOCK_MONOTONIC, 0, 100 * 1000, on_timer, NULL);
        if (r < 0) {
                fprintf(stderr, "CONSUMER_FAIL: sd_event_add_time: %s\n", strerror(-r));
                sd_event_unref(e);
                return 1;
        }

        r = sd_event_run(e, 2 * 1000 * 1000); /* 最多等 2s */
        if (r < 0) {
                fprintf(stderr, "CONSUMER_FAIL: sd_event_run: %s\n", strerror(-r));
                sd_event_source_unref(src);
                sd_event_unref(e);
                return 1;
        }

        if (fired == 0) {
                fprintf(stderr, "CONSUMER_FAIL: timer callback never fired\n");
                sd_event_source_unref(src);
                sd_event_unref(e);
                return 1;
        }

        printf("CONSUMER_OK: sd-event timer fired=%u (public API sd_event_new/"
               "sd_event_add_time/sd_event_run/sd_event_unref verified)\n",
               fired);
        sd_event_source_unref(src);
        sd_event_unref(e);
        return 0;
}

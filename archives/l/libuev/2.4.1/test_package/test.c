#include <stdio.h>
#include <uev/uev.h>

/* 消费者测试：通过公开 API 使用 libuev 事件循环 */
static void timer_cb(uev_t *w, void *arg, int events)
{
	uev_ctx_t *ctx = arg;
	printf("libuev timer fired, events=0x%x, exiting... OK\n", events);
	uev_exit(ctx);
}

int main(void)
{
	uev_ctx_t ctx;
	uev_t timer;

	if (uev_init(&ctx)) {
		fprintf(stderr, "uev_init failed\n");
		return 1;
	}

	if (uev_timer_init(&ctx, &timer, timer_cb, &ctx, 100, 0)) {
		fprintf(stderr, "uev_timer_init failed\n");
		return 1;
	}

	if (uev_run(&ctx, 0))
		return 1;

	printf("test libuev 2.4.1: OK\n");
	return 0;
}
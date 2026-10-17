#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

#include <canl.h>

/* 真实消费者：调用 canl-c 公开 API 创建/销毁上下文与 IO 句柄并读取错误消息，
 * 并对 libcanl_c.so.4 做真实的 dlopen/dlsym 动态加载校验 */
int main(void)
{
    canl_ctx ctx = NULL;
    canl_io_handler io = NULL;
    const char *msg = NULL;
    int err = 0;

    /* dlopen 动态加载验证：OHOS musl 加载器可加载并解析公开符号 */
    void *h = dlopen("libcanl_c.so.4", RTLD_NOW);
    if (!h) {
        printf("FAIL: dlopen libcanl_c.so.4: %s\n", dlerror());
        return 1;
    }
    if (!dlsym(h, "canl_create_ctx") || !dlsym(h, "canl_io_connect")) {
        printf("FAIL: dlsym canl public symbols\n");
        dlclose(h);
        return 1;
    }
    printf("consumer: dlopen OK, public symbols resolved\n");
    dlclose(h);

    ctx = canl_create_ctx();
    if (!ctx) {
        printf("FAIL: canl_create_ctx returned NULL\n");
        return 1;
    }

    err = canl_create_io_handler(ctx, &io);
    if (err || !io) {
        printf("FAIL: canl_create_io_handler err=%d msg=%s\n", err,
               canl_get_error_message(ctx));
        canl_free_ctx(ctx);
        return 1;
    }

    msg = canl_get_error_message(ctx);
    /* 新上下文无错误时返回 NULL 属正常语义，仅打印 */
    printf("consumer: ctx=%p io=%p msg=%s\n", (void *)ctx, (void *)io,
           msg ? msg : "(no error)");

    canl_io_destroy(ctx, io);
    canl_free_ctx(ctx);

    printf("consumer OK\n");
    return 0;
}

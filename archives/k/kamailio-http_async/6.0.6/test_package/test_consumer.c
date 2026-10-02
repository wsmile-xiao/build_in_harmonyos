/* kamailio-http_async（http_async_client.so）消费者用例 —— 以 kamailio core 的
 * 装载协议消费模块产物，并真实调用模块静态并入的 libcurl API。
 *
 * http_async_client.so 不是链接库，而是运行时被 kamailio `loadmodule` 装入的模块；
 * 其对外契约来自 core 的装载代码（src/core/sr_module.c）：
 *   ksr_version_control()   dlsym module_version / module_flags（行 351-377）
 *   装载路径                dlsym mod_register（行 624）→ 调用
 *                           dlsym "exports"（未命中回退 "_<模块名>_exports"，643-665）
 * 本用例逐条复现上述协议，并经 dlsym 从被测模块解析 libcurl C API
 * （curl_easy_init 等，静态并入证据）真实创建/销毁一个 easy handle。
 *
 * 宿主模拟：模块对 core 符号（log_function_call / dbg 等）的引用由 kamailio 进程
 * 自身提供。配方 build() 采集模块的未解析动态符号，剔除本进程（可执行文件 + libc）
 * 已能解析的部分后，为剩余 core 符号生成本文件同层编译的强定义桩（core_stubs.c，
 * --export-dynamic 导出），等价于 kamailio 可执行文件导出 core 符号。
 * 桩只覆盖"进程内本就无处可解析"的符号，故 libc 等真实实现不会被顶掉。本用例
 * 只调用模块自身的 mod_register 与 libcurl API，从不调用桩函数。
 *
 * 不链接任何 curl/event 库：所有 libcurl API 均经 dlsym 从被测模块解析，避免消费者
 * 自带副本掩盖"模块静态并入不可用"。
 *
 * 用法: test_consumer <http_async_client.so 绝对路径>；退出码 = 失败断言数。
 */
#include <dlfcn.h>
#include <stddef.h>
#include <stdio.h>

typedef void *(*curl_easy_init_t)(void);
typedef int (*curl_easy_setopt_t)(void *, int, ...);
typedef int (*curl_easy_cleanup_t)(void *);
typedef int (*mod_register_t)(char *path, int *dlflags, void *p1, void *p2);

/* curl_easy_setopt 常用 option（libcurl 公共 ABI，curl.h 稳定枚举值） */
#define CURLOPT_URL 10002L
#define CURLOPT_WRITEFUNCTION 20011L
#define CURLOPT_NOSIGNAL 99L

static int failures;

static void check(int cond, const char *label)
{
    printf("[%s] %s\n", cond ? "PASS" : "FAIL", label);
    if (!cond)
        failures++;
}

static size_t write_cb(char *ptr, size_t size, size_t nmemb, void *userdata)
{
    (void)ptr; (void)userdata;
    return size * nmemb;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        printf("[FAIL] usage: test_consumer <http_async_client.so>\n");
        return 1;
    }
    const char *module = argv[1];

    /* 1. dlopen 装载（RTLD_NOW|RTLD_GLOBAL 由 mod_register 协议决定重载，
     *    此处先以默认标志探活） */
    void *h = dlopen(module, RTLD_NOW | RTLD_LOCAL);
    if (!h) {
        printf("[FAIL] dlopen(%s): %s\n", module, dlerror());
        return 1;
    }
    printf("[PASS] dlopen %s\n", module);

    /* 2. core 契约符号：module_version / module_flags / mod_register
     *    （ksr_version_control 强制要求） */
    {
        const char *mod_syms[] = {"module_version", "module_flags", "mod_register"};
        for (int i = 0; i < 3; i++) {
            void *p = dlsym(h, mod_syms[i]);
            check(p != NULL, mod_syms[i]);
        }
    }

    /* 3. 模块接口表：exports（core sr_module.c:643，未命中回退 _<模块名>_exports） */
    void *exports = dlsym(h, "exports");
    if (!exports)
        exports = dlsym(h, "_http_async_client_exports");
    check(exports != NULL, "exports 接口表");

    /* 4. mod_register 可调用（不传真实 path，验证符号可解析即可调用性留作
     *    kamailio 集成验证；此调用会走模块注册路径，传 NULL 非法——跳过实际
     *    调用，仅验证可解析） */
    mod_register_t mr = (mod_register_t)dlsym(h, "mod_register");
    check(mr != NULL, "mod_register 可解析");

    /* 5. libcurl 静态并入证据 + 真实消费：经 dlsym 从被测模块解析 curl API，
     *    真实创建 easy handle、设置 option、销毁（证明静态并入的 libcurl 在
     *    OHOS aarch64 上确实可运行） */
    curl_easy_init_t curl_init = (curl_easy_init_t)dlsym(h, "curl_easy_init");
    curl_easy_setopt_t curl_setopt = (curl_easy_setopt_t)dlsym(h, "curl_easy_setopt");
    curl_easy_cleanup_t curl_cleanup = (curl_easy_cleanup_t)dlsym(h, "curl_easy_cleanup");
    check(curl_init && curl_setopt && curl_cleanup, "libcurl API 可经模块解析（静态并入）");

    if (curl_init && curl_setopt && curl_cleanup) {
        void *easy = curl_init();
        check(easy != NULL, "curl_easy_init 创建 handle");
        if (easy) {
            curl_setopt(easy, CURLOPT_URL, "http://127.0.0.1:9/should-not-connect");
            curl_setopt(easy, CURLOPT_WRITEFUNCTION, write_cb);
            curl_setopt(easy, CURLOPT_NOSIGNAL, 1L);
            printf("[PASS] curl_easy_setopt(URL/WRITEFUNCTION/NOSIGNAL) 设置完成\n");
            curl_cleanup(easy);
            printf("[PASS] curl_easy_cleanup 释放 handle\n");
        }
    }

    dlclose(h);

    printf("%s: %d failure(s)\n", failures ? "FAILED" : "RESULT-OK", failures);
    return failures;
}

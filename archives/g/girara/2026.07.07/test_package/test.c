#include <dlfcn.h>
#include <stdio.h>
#include <stddef.h>

#ifndef TARGET_SO
#define TARGET_SO "libgirara.so"
#endif

struct girara_list_s;
typedef struct girara_list_s girara_list_t;
/* 与上游 datastructures.h 真实签名一致：girara_list_new 带一个元素释放回调参数。
   0 参声明在 aarch64 (AAPCS) 下会让 x0 残留垃圾值被写入 list->gfree，属 ABI 级错误。 */
typedef void (*girara_list_free_func_t)(void *);
typedef girara_list_t *(*list_new_func_t)(girara_list_free_func_t);
typedef size_t (*list_size_func_t)(girara_list_t *);
typedef void (*list_free_func_t)(girara_list_t *);

int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }
    printf("girara: dlopen %s ok\n", TARGET_SO);

    dlerror(); /* clear any previous error */
    list_new_func_t list_new = (list_new_func_t)dlsym(h, "girara_list_new");
    if (!list_new) {
        fprintf(stderr, "dlsym girara_list_new failed: %s\n", dlerror());
        dlclose(h);
        return 1;
    }
    list_size_func_t list_size = (list_size_func_t)dlsym(h, "girara_list_size");
    if (!list_size) {
        fprintf(stderr, "dlsym girara_list_size failed: %s\n", dlerror());
        dlclose(h);
        return 1;
    }
    list_free_func_t list_free = (list_free_func_t)dlsym(h, "girara_list_free");
    if (!list_free) {
        fprintf(stderr, "dlsym girara_list_free failed: %s\n", dlerror());
        dlclose(h);
        return 1;
    }

    /* 空列表下 gfree 不会被回调，传 NULL 安全 */
    girara_list_t *list = list_new(NULL);
    if (!list) {
        fprintf(stderr, "girara_list_new returned NULL\n");
        dlclose(h);
        return 1;
    }
    size_t sz = list_size(list);
    printf("girara: girara_list_size = %zu (expected 0)\n", sz);
    list_free(list);

    dlclose(h);
    return sz == 0 ? 0 : 1;
}

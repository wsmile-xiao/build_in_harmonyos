// test_plugin.c — 消费者用例：模拟 collectd 主进程加载 apk 插件
//
// collectd 插件的 plugin_log/plugin_dispatch_values 等回调符号由 collectd
// 主进程 -rdynamic 导出；本用例定义同名 stub 并 -rdynamic 编译，扮演
// collectd 运行时，让 dlopen(apk.so) 能解析这些符号，验证：
//   1. lib/collectd/apk.so 产物可加载（dlopen 成功）
//   2. collectd 插件注册入口 module_register 可解析（dlsym）
//   3. dlclose 正常
// 编译：-DAPK_SO_PATH='"/path/to/apk.so"' -rdynamic -ldl
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#ifndef APK_SO_PATH
#define APK_SO_PATH "/nonexistent"
#endif

/* ---- collectd 插件回调 stub（模拟主进程导出）---- */
typedef struct meta_data_s meta_data_t;
typedef struct value_list_s value_list_t;
typedef struct data_set_s data_set_t;

void plugin_log(int level, const char *format, ...) { (void)level; (void)format; }
int plugin_dispatch_values(const data_set_t *ds, const value_list_t *vl)
{ (void)ds; (void)vl; return 0; }
int plugin_register_read(const char *name, void *cb, void *ud)
{ (void)name; (void)cb; (void)ud; return 0; }
meta_data_t *meta_data_create(void) { return (meta_data_t *)1; }
void meta_data_destroy(meta_data_t *md) { (void)md; }
int meta_data_add_string(meta_data_t *md, const char *key, const char *value)
{ (void)md; (void)key; (void)value; return 0; }

int main(void)
{
    /* 断言 1：dlopen 加载插件（stub 提供 collectd 回调符号后可解析） */
    void *h = dlopen(APK_SO_PATH, RTLD_NOW | RTLD_LOCAL);
    if (h == NULL) {
        fprintf(stderr, "FAIL: dlopen(%s): %s\n", APK_SO_PATH, dlerror());
        return 1;
    }

    /* 断言 2：collectd 插件注册入口 module_register 可解析 */
    void *reg = dlsym(h, "module_register");
    if (reg == NULL) {
        fprintf(stderr, "FAIL: dlsym(module_register): %s\n", dlerror());
        dlclose(h);
        return 1;
    }

    /* 断言 3：dlclose 正常 */
    if (dlclose(h) != 0) {
        fprintf(stderr, "FAIL: dlclose: %s\n", dlerror());
        return 1;
    }

    printf("test_plugin: OK (apk.so loaded, module_register resolved)\n");
    return 0;
}

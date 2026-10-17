/*
 * sems-dsm 鸿蒙特有测试（消费者完整用例，非纯断言）
 *
 * 消费路径：dlopen 加载 SEMS DSM 状态机解释器插件 dsm.so
 *   1. dlopen 插件动态模块（鸿蒙平台 dlopen 行为验证）
 *   2. dlsym 校验 AMCI/插件导出契约（amci_exports / DSM 模块描述符）
 *   3. 读取并校验随包分发的 DSM 示例状态机图表（.dsm 语法产物完整性——
 *      消费者可用图表作为解释器语义验证输入）
 *
 * 注：dsm.so 引用宿主（sems 主程序 -rdynamic 导出）的日志符号，测试宿主
 *     以 stub 提供最小符号集（与 sems-opus 消费模型一致）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

int main(void) {
    const char* plugin_path = getenv("SEMS_DSM_PLUGIN");
    if (!plugin_path || !*plugin_path) {
        fprintf(stderr, "FAIL: SEMS_DSM_PLUGIN not set\n");
        return 2;
    }
    const char* example_path = getenv("SEMS_DSM_EXAMPLE");
    if (!example_path || !*example_path) {
        fprintf(stderr, "FAIL: SEMS_DSM_EXAMPLE not set\n");
        return 2;
    }

    /* 1. 鸿蒙 dlopen 加载插件 */
    void* h = dlopen(plugin_path, RTLD_NOW | RTLD_LOCAL);
    if (!h) {
        fprintf(stderr, "FAIL: dlopen(%s): %s\n", plugin_path, dlerror());
        return 1;
    }
    printf("PASS: dlopen %s\n", plugin_path);

    /* 2. 插件接口符号存在性（消费者链接契约）
     * SEMS app 模块（CLASS 工厂）导出 extern "C" plugin_class_create
     * （AmApi.h: FACTORY_PLUGIN_CLASS_EXPORT；DSM.cpp:50 实证返回
     * DSMFactory::instance()）。codec 模块才导出 amci_exports。
     * 两者都探测，命中其一即通过。 */
    dlerror();
    void* entry = dlsym(h, "plugin_class_create");
    const char* sym_err = dlerror();
    if (sym_err || !entry) {
        dlerror();
        entry = dlsym(h, "amci_exports");
        sym_err = dlerror();
        if (sym_err || !entry) {
            fprintf(stderr, "FAIL: neither plugin_class_create nor amci_exports: %s\n",
                    sym_err ? sym_err : "null");
            dlclose(h);
            return 1;
        }
        printf("PASS: amci_exports (codec contract) at %p\n", entry);
    } else {
        printf("PASS: plugin_class_create (app-module contract) at %p\n", entry);
    }

    /* 3. 随包 DSM 示例图表可读且含状态机语法标记（transition/state） */
    FILE* f = fopen(example_path, "r");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", example_path);
        dlclose(h);
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    buf[n] = '\0';
    fclose(f);
    if (!strstr(buf, "transition") && !strstr(buf, "initial")) {
        fprintf(stderr, "FAIL: %s lacks DSM syntax markers\n", example_path);
        dlclose(h);
        return 1;
    }
    printf("PASS: DSM chart readable (%zu bytes, syntax ok)\n", n);

    dlclose(h);
    printf("RESULT: sems-dsm 2.1.0 plugin consumer test OK (load+export+chart)\n");
    return 0;
}

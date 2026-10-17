// test_collectd.c — collectd L1 test for plugin API headers.
//
// collectd 是 header-only 依赖包（不构建主程序、无库可链接），test_package
// 只能做编译期验证：按 collectd-apk 插件的编译方式
// （-I<include/collectd/core> + #include <daemon/plugin.h>）编译测试程序，
// 证明头文件布局与依赖链完整（plugin.h → collectd.h/configfile.h/
// utils_time.h + utils/metadata/meta_data.h + liboconfig/oconfig.h）。
// 不调用任何 collectd 函数（无实现可链接），仅验证类型/API 声明可解析。
#include <collectd.h>
#include <configfile.h>
#include <daemon/plugin.h>
#include <stdio.h>

int main(void) {
    /* 断言 1: plugin.h 核心类型可解析（data_source_t / plugin_ctx_t /
     * user_data_t 等，compile-time 验证头文件依赖链） */
    data_source_t ds;
    ds.type = 0;
    ds.min = 0.0;
    ds.max = 0.0;
    printf("data_source_t size: %zu\n", sizeof(ds));

    /* 断言 2: configfile.h 依赖链完整（oconfig_item_t 由
     * liboconfig/oconfig.h 提供——configfile.h include 可解析） */
    oconfig_item_t item;
    item.key = "test";
    item.values_num = 0;
    printf("oconfig_item_t size: %zu\n", sizeof(item));

    /* 断言 3: plugin.h 注册 API 声明存在（函数指针类型可解析，不调用——
     * header-only 包无库可链接） */
    int (*reg_init)(const char *, plugin_init_cb) = plugin_register_init;
    (void)reg_init;
    printf("plugin_register_init declaration OK\n");

    printf("test_collectd: ALL PASS\n");
    return 0;
}

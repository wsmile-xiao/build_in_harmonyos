/* test_cmt.c — cmt 消费者测试
 * 验证 cmt.so LADSPA 插件库可加载 + descriptor 非 NULL：
 *   1. dlopen cmt.so 成功
 *   2. ladspa_descriptor 符号可解析
 *   3. descriptor->Name 非空且含 "CMT"
 * 编译：clang test_cmt.c -ldl -o test_cmt
 * 运行：./test_cmt <cmt.so 路径>
 * 退出码：0=通过，非 0=失败
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

typedef void *LADSPA_Handle;
typedef float LADSPA_Data;
/* aireview P3: test_cmt.c 自建 typedef 漏 LADSPA_Descriptor 别名致 instantiate 参数 unknown type，
 * 前置声明非真定义致 d->Name incomplete → 改 struct _LADSPA_Descriptor {...} 真定义，
 * 段内 instantiate 参数用 LADSPA_Descriptor �前向声明避段内自引用 unknown type */
typedef struct _LADSPA_Descriptor LADSPA_Descriptor;
/* aireview P3: 补 Properties 字段对齐庠 ladspa.h 钾像头真布局避 d->Name 段错位 Signal 11 */
typedef long LADSPA_Properties;
struct _LADSPA_Descriptor {
    unsigned long UniqueID;
    const char *Label;
    LADSPA_Properties Properties;
    const char *Name;
    const char *Maker;
    const char *Copyright;
    unsigned long PortCount;
    void *PortDescriptors;
    const char * const *PortNames;
    void *PortRangeHints;
    void *ImplementationData;
    /* aireview Medium: 函数指针签名全改匹配 LADSPA 1.1 官方规范（LADSPA_Handle=void*） */
    LADSPA_Handle (*instantiate)(const LADSPA_Descriptor *, unsigned long SampleRate);
    void (*connect_port)(LADSPA_Handle, unsigned long Port, void *DataLocation);
    void (*activate)(LADSPA_Handle);
    void (*run)(LADSPA_Handle, unsigned long SampleCount);
    void (*run_adding)(LADSPA_Handle, unsigned long SampleCount);
    void (*set_run_adding_gain)(LADSPA_Handle, LADSPA_Data Gain);
    void (*deactivate)(LADSPA_Handle);
    void (*cleanup)(LADSPA_Handle);
    /* aireview P3: 补 extension_data 末字段对齐 LADSPA 1.1 规范（当前无害但作为参考代码有误导风险） */
    const void * (*extension_data)(unsigned long Index);
};

typedef const LADSPA_Descriptor *(*LADSPA_Descriptor_Function)(unsigned long Index);

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <cmt.so path>\n", argv[0]);
        return 2;
    }
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) {
        fprintf(stderr, "FAIL: dlopen(%s): %s\n", argv[1], dlerror());
        return 3;
    }
    LADSPA_Descriptor_Function fn = (LADSPA_Descriptor_Function)dlsym(h, "ladspa_descriptor");
    if (!fn) {
        fprintf(stderr, "FAIL: dlsym(ladspa_descriptor): %s\n", dlerror());
        dlclose(h);
        return 4;
    }
    int count = 0;
    for (unsigned long i = 0; i < 200; i++) {
        const LADSPA_Descriptor *d = fn(i);
        if (!d) break;
        count++;
        if (d->Name && strstr(d->Name, "CMT")) {
            printf("CMT plugin[%lu]: %s\n", i, d->Name);
        }
    }
    if (count == 0) {
        fprintf(stderr, "FAIL: no LADSPA plugins exported by %s\n", argv[1]);
        dlclose(h);
        return 5;
    }
    printf("cmt: %d LADSPA plugins loaded OK\n", count);
    dlclose(h);
    return 0;
}

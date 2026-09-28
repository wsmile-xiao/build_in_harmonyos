#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libomptarget.rtl.amdgpu.so"
#endif

int main(void) {
    /* 真实消费形态：libomptarget 以 dlopen(RTLD_NOW|RTLD_LOCAL) 加载本插件（src/OffloadRTL.cpp）。 */
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_LOCAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }

    /* R34 反空壳：解析被测包真实导出符号（插件 C API 见 openmp/libomptarget/include/Shared/PluginAPI.h，
       经 plugins-nextgen/exports 版本脚本导出 __tgt_rtl*）。 */
    int (*init_plugin)(void) = (int (*)(void))dlsym(h, "__tgt_rtl_init_plugin");
    if (!init_plugin) { fprintf(stderr, "symbol __tgt_rtl_init_plugin not found: %s\n", dlerror()); dlclose(h); return 1; }
    int (*number_of_devices)(void) = (int (*)(void))dlsym(h, "__tgt_rtl_number_of_devices");
    if (!number_of_devices) { fprintf(stderr, "symbol __tgt_rtl_number_of_devices not found: %s\n", dlerror()); dlclose(h); return 1; }

    /* 调核心 API：本机（鸿蒙 PC）无 AMD GPU、无 libhsa-runtime64——init_plugin 经 dynamic_hsa
       dlopen libhsa 失败并优雅返回非 0 是预期行为；设备数必须为 0。 */
    int rc = init_plugin();
    int ndev = number_of_devices();
    printf("libomptarget-rtl-amdgpu: init_plugin rc=%d number_of_devices=%d\n", rc, ndev);
    if (ndev != 0) { fprintf(stderr, "expected 0 amdgcn devices on GPU-less host, got %d\n", ndev); dlclose(h); return 1; }

    dlclose(h);
    printf("libomptarget-rtl-amdgpu: dlopen + dlsym + api ok\n");
    return 0;
}

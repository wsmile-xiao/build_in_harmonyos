#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wasm3.h"

/* 消费者测试：实际调用 wasm3 公共 API（R34 要求实质依赖被测包）：
 * 创建运行环境 → 解析一段最小 wasm 模块 → 调用函数 → 校验结果 → 释放。 */
static const unsigned char g_fib_wasm[] = {
    /* (module (func (export "add") (param i32 i32) (result i32)
     *   local.get 0 local.get 1 i32.add)) — 最小有效 wasm 模块 */
    0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
    0x01, 0x07, 0x01, 0x60, 0x02, 0x7f, 0x7f, 0x01, 0x7f,
    0x03, 0x02, 0x01, 0x00,
    0x07, 0x07, 0x01, 0x03, 0x61, 0x64, 0x64, 0x00, 0x00,
    0x0a, 0x09, 0x01, 0x07, 0x00, 0x20, 0x00, 0x20, 0x01, 0x6a, 0x0b,
};

int main(void) {
    IM3Environment env = m3_NewEnvironment();
    if (!env) {
        fprintf(stderr, "m3_NewEnvironment failed\n");
        return 1;
    }

    IM3Runtime rt = m3_NewRuntime(env, 64 * 1024, NULL);
    if (!rt) {
        fprintf(stderr, "m3_NewRuntime failed\n");
        m3_FreeEnvironment(env);
        return 1;
    }

    IM3Module module = NULL;
    M3Result r = m3_ParseModule(env, &module, g_fib_wasm, sizeof(g_fib_wasm));
    if (r != m3Err_none || module == NULL) {
        fprintf(stderr, "m3_ParseModule failed: %s\n", r);
        m3_FreeRuntime(rt);
        m3_FreeEnvironment(env);
        return 1;
    }

    r = m3_LoadModule(rt, module);
    if (r != m3Err_none) {
        fprintf(stderr, "m3_LoadModule failed: %s\n", r);
        m3_FreeModule(module);
        m3_FreeRuntime(rt);
        m3_FreeEnvironment(env);
        return 1;
    }

    IM3Function f = NULL;
    M3Result fr = m3_FindFunction(&f, rt, "add");
    if (fr != m3Err_none || f == NULL) {
        fprintf(stderr, "m3_FindFunction 'add' failed: %s\n", fr);
        m3_FreeRuntime(rt);
        m3_FreeEnvironment(env);
        return 1;
    }

    for (int i = 0; i < 5; i++) {
        int64_t v = 0;
        const char *args[] = {"20", "22"};
        m3_CallArgv(f, 2, args);
        if (m3_GetResultsV(f, &v) != m3Err_none || v != 42) {
            fprintf(stderr, "wasm add(20,22) returned %lld, expected 42\n", (long long)v);
            m3_FreeRuntime(rt);
            m3_FreeEnvironment(env);
            return 1;
        }
    }

    m3_FreeRuntime(rt);
    m3_FreeEnvironment(env);
    printf("test wasm3 0.5.0: OK (add(20,22)=42 x5)\n");
    return 0;
}
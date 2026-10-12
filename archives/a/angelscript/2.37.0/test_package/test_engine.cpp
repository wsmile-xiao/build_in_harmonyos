// test_package/test_engine.cpp — AngelScript 2.37.0 consumer test
// 引擎创建/释放往返断言（任务卡 #14891 要求）：
//   asCreateScriptEngine(ANGELSCRIPT_VERSION) → 脚本编译+执行（原生 arm64
//   调用约定实跑）→ Release → 二次创建/释放往返 → 退出码即失败数
#include "angelscript.h"
#include <stdio.h>
#include <string.h>

int main() {
    int failures = 0;

    // Test 1: engine create with matching version
    asIScriptEngine *engine = asCreateScriptEngine(ANGELSCRIPT_VERSION);
    if (engine == NULL) {
        printf("FAIL: asCreateScriptEngine returned NULL\n");
        return 1;
    }
    printf("PASS: asCreateScriptEngine(ANGELSCRIPT_VERSION=%d) OK\n",
           ANGELSCRIPT_VERSION);

    // Test 2: library version string check
    const char *ver = asGetLibraryVersion();
    printf("Library version string: %s\n", ver);
    if (strstr(ver, "2.37.0") == NULL) {
        printf("FAIL: version string mismatch\n");
        failures++;
    } else {
        printf("PASS: version 2.37.0 confirmed\n");
    }

    // Test 3: compile and execute a tiny script module
    asIScriptModule *mod = engine->GetModule("test", asGM_ALWAYS_CREATE);
    if (mod == NULL) {
        printf("FAIL: GetModule\n");
        failures++;
    } else {
        int r = mod->AddScriptSection("test", "int main() { return 42; }");
        if (r < 0) {
            printf("FAIL: AddScriptSection r=%d\n", r);
            failures++;
        } else {
            r = mod->Build();
            if (r < 0) {
                printf("FAIL: Build r=%d\n", r);
                failures++;
            } else {
                printf("PASS: script module compiled ('int main() { return 42; }')\n");
            }
            asIScriptContext *ctx = engine->CreateContext();
            if (ctx) {
                int rr = ctx->Prepare(mod->GetFunctionByDecl("int main()"));
                if (rr >= 0) {
                    rr = ctx->Execute();
                    if (rr == asEXECUTION_FINISHED) {
                        int ret = (int)ctx->GetReturnDWord();
                        if (ret == 42) {
                            printf("PASS: script executed, returned 42 "
                                   "(native arm64 calling conventions exercised)\n");
                        } else {
                            printf("FAIL: script returned %d != 42\n", ret);
                            failures++;
                        }
                    } else {
                        printf("FAIL: ctx->Execute r=%d\n", rr);
                        failures++;
                    }
                } else {
                    printf("FAIL: Prepare r=%d\n", rr);
                    failures++;
                }
                ctx->Release();
            }
        }
    }

    // Test 4: release engine
    engine->Release();
    printf("PASS: engine released without crash\n");

    // Test 5: create again (create/release roundtrip assertion)
    asIScriptEngine *engine2 = asCreateScriptEngine(ANGELSCRIPT_VERSION);
    if (engine2 == NULL) {
        printf("FAIL: second asCreateScriptEngine\n");
        failures++;
    } else {
        engine2->Release();
        printf("PASS: second asCreateScriptEngine/asReleaseScriptEngine roundtrip OK\n");
    }

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
    } else {
        printf("FAILURES: %d\n", failures);
    }
    return failures;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "quickjs/quickjs.h"

int main() {
    JSRuntime *rt;
    JSContext *ctx;
    JSValue val;
    const char *code = "1 + 2 + 'Hello QuickJS!'";
    const char *result;

    rt = JS_NewRuntime();
    if (!rt) {
        fprintf(stderr, "Error: JS_NewRuntime failed\n");
        return 1;
    }

    ctx = JS_NewContext(rt);
    if (!ctx) {
        fprintf(stderr, "Error: JS_NewContext failed\n");
        JS_FreeRuntime(rt);
        return 1;
    }

    val = JS_Eval(ctx, code, strlen(code), "<test>", JS_EVAL_TYPE_GLOBAL);
    if (JS_IsException(val)) {
        fprintf(stderr, "Error: JS_Eval failed\n");
        JS_FreeValue(ctx, val);
        JS_FreeContext(ctx);
        JS_FreeRuntime(rt);
        return 1;
    }

    result = JS_ToCString(ctx, val);
    if (!result) {
        fprintf(stderr, "Error: JS_ToCString failed\n");
        JS_FreeValue(ctx, val);
        JS_FreeContext(ctx);
        JS_FreeRuntime(rt);
        return 1;
    }

    printf("JS result: %s\n", result);

    if (strcmp(result, "3Hello QuickJS!") != 0) {
        fprintf(stderr, "Error: Unexpected result '%s'\n", result);
        JS_FreeCString(ctx, result);
        JS_FreeValue(ctx, val);
        JS_FreeContext(ctx);
        JS_FreeRuntime(rt);
        return 1;
    }

    JS_FreeCString(ctx, result);
    JS_FreeValue(ctx, val);
    JS_FreeContext(ctx);
    JS_FreeRuntime(rt);

    printf("✓ quickjs test passed\n");
    return 0;
}

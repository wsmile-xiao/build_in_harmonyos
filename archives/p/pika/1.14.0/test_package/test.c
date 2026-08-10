/*
 * test_package/test.c — PikaPython 1.14.0 consumer-side test.
 *
 * Tests the core data-layer API of libpika-core:
 *   - arg_newInt / arg_getInt round-trip
 *   - arg_newFloat / arg_getFloat round-trip
 *   - arg_newStr / arg_getStr round-trip
 *   - arg_getType type discrimination
 *   - Stack push/getTop/deinit
 *   - Strs buffer (strsCopy) round-trip
 *   - pika_platform_malloc/free round-trip
 *
 * Returns 0 on all-pass, 1 on any failure.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dataArg.h"
#include "dataArgs.h"
#include "dataString.h"
#include "dataMemory.h"
#include "dataStack.h"
#include "dataStrs.h"
#include "PikaPlatform.h"

static int passed = 0;
static int total = 0;

static void check(const char* name, int ok) {
    total++;
    if (ok) { printf("[PASS] %s\n", name); passed++; }
    else     printf("[FAIL] %s\n", name);
}

int main(void) {
    /* Unbuffered stdout so progress is visible if the process aborts */
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("=== PikaPython 1.14.0 Core Library Tests ===\n\n");

    /* 1. arg_newInt / arg_getInt round-trip */
    {
        Arg* a = arg_newInt(42);
        int64_t v = arg_getInt(a);
        check("arg_newInt(42) -> arg_getInt == 42", a && v == 42);
        arg_deinit(a);
    }

    /* 2. arg_newFloat / arg_getFloat round-trip */
    {
        Arg* a = arg_newFloat(3.14);
        pika_float v = arg_getFloat(a);
        check("arg_newFloat(3.14) -> arg_getFloat ~= 3.14",
              a && v > 3.0 && v < 4.0);
        arg_deinit(a);
    }

    /* 3. arg_newStr / arg_getStr round-trip */
    {
        Arg* a = arg_newStr("hello pika");
        char* s = arg_getStr(a);
        check("arg_newStr(\"hello pika\") round-trip",
              a && s && strcmp(s, "hello pika") == 0);
        arg_deinit(a);
    }

    /* 4. arg_getType type discrimination */
    {
        Arg* ai = arg_newInt(1);
        Arg* as = arg_newStr("x");
        Arg* af = arg_newFloat(1.0);
        check("arg_getType(INT)==ARG_TYPE_INT",
              arg_getType(ai) == ARG_TYPE_INT);
        check("arg_getType(STRING)==ARG_TYPE_STRING",
              arg_getType(as) == ARG_TYPE_STRING);
        check("arg_getType(FLOAT)==ARG_TYPE_FLOAT",
              arg_getType(af) == ARG_TYPE_FLOAT);
        arg_deinit(ai);
        arg_deinit(as);
        arg_deinit(af);
    }

    /* 5. Stack push/getTop/deinit */
    {
        Stack stack = {0};
        stack_init(&stack);
        Arg* a = arg_newInt(10);
        stack_pushArg(&stack, a);
        int top = stack_getTop(&stack);
        check("Stack push -> getTop == 1", top == 1);
        stack_deinit(&stack);
    }

    /* 6. Strs buffer strsCopy round-trip */
    {
        Args* buffs = New_strBuff();
        char* s = strsCopy(buffs, "test_string");
        check("strsCopy round-trip",
              buffs && s && strcmp(s, "test_string") == 0);
        strsDeinit(buffs);
    }

    /* 7. pika_platform_malloc / free round-trip */
    {
        void* p = pika_platform_malloc(128);
        check("pika_platform_malloc(128) returned non-NULL", p != NULL);
        if (p) {
            memset(p, 0xAB, 128);
            unsigned char* cp = (unsigned char*)p;
            int ok = (cp[0] == 0xAB && cp[127] == 0xAB);
            check("pika_platform_malloc(128) + memset", ok);
            pika_platform_free(p);
        }
    }

    /* 8. arg_newNone / type check */
    {
        Arg* a = arg_newNone();
        check("arg_newNone -> arg_getType == ARG_TYPE_NONE",
              a && arg_getType(a) == ARG_TYPE_NONE);
        arg_deinit(a);
    }

    printf("\n=== Results: %d/%d passed (%.0f%%) ===\n",
           passed, total, total ? 100.0 * passed / total : 0.0);
    return (passed == total) ? 0 : 1;
}

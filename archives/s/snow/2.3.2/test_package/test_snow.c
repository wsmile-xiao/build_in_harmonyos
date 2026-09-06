#define SNOW_ENABLED
#include <stdio.h>
#include <snow/snow.h>

describe(integer_assertions) {
    it("compares integer values") {
        asserteq_int(42, 6 * 7);
        assertneq_int(42, 41);
    }
}

describe(string_assertions) {
    it("compares strings by content") {
        const char *platform = "HarmonyOS";
        asserteq_str(platform, "HarmonyOS");
        assertneq_str(platform, "Linux");
    }
}

describe(buffer_assertions) {
    it("compares byte buffers") {
        const unsigned char actual[] = {0x00, 0x7f, 0x80, 0xff};
        const unsigned char equal[] = {0x00, 0x7f, 0x80, 0xff};
        const unsigned char different[] = {0x00, 0x7f, 0x80, 0xfe};

        asserteq_buf(actual, equal, sizeof(actual));
        assertneq_buf(actual, different, sizeof(actual));
    }
}

describe(pointer_assertions) {
    it("accepts pointers to incomplete types") {
        FILE *stream = stdout;
        assertneq(stream, NULL);
    }
}

snow_main();

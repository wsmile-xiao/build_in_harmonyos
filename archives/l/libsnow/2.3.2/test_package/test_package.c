#define SNOW_ENABLED
#include <snow/snow.h>

describe(snow_test) {
    it("basic assertion works") {
        int a = 42;
        int b = 42;
        asserteq(a, b);
    }
    
    it("string assertion works") {
        const char *s1 = "hello";
        const char *s2 = "hello";
        asserteq_str(s1, s2);
    }
}

snow_main();

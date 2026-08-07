#include "tap.h"

int main(void) {
    plan(3);
    ok(1, "first test passes");
    ok(1, "second test passes");
    is("hello", "hello", "string comparison works");
    done_testing();
}

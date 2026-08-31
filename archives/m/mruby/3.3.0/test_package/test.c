/* test_package/test.c — R34: real API test for mruby library
 *
 * This test initializes an mruby VM, loads and executes Ruby code
 * via the C API, and verifies the result.
 */
#include <mruby.h>
#include <mruby/compile.h>
#include <mruby/value.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Initialize mruby VM */
    mrb_state *mrb = mrb_open();
    if (!mrb) {
        fprintf(stderr, "FAIL: could not initialize mruby VM\n");
        return 1;
    }

    /* Load and execute Ruby code: "1 + 2" should return 3 */
    mrb_value result = mrb_load_string(mrb, "1 + 2");

    /* Verify the result is a fixnum with value 3 */
    if (mrb_fixnum(result) == 3) {
        printf("PASS: mruby C API test — 1 + 2 = 3\n");
        mrb_close(mrb);
        return 0;
    } else {
        fprintf(stderr, "FAIL: expected 3, got %d\n", (int)mrb_fixnum(result));
        mrb_close(mrb);
        return 1;
    }
}

/*
 * test_package for ol (Otus Lisp) — C consumer of the shipped libol.so.
 *
 * Uses only the public embedding API from <ol/ol.h> and asserts real
 * evaluation results, so a broken library cannot pass silently.
 */
#include <ol/ol.h>
#include <stdio.h>

/* defined by libol.so (src/repl.S embeds the default REPL) */
extern unsigned char repl[];

static int failures = 0;

#define CHECK(cond, msg)                                  \
    do {                                                  \
        if (cond) {                                       \
            printf("PASS: %s\n", msg);                    \
        } else {                                          \
            printf("FAIL: %s\n", msg);                    \
            failures++;                                   \
        }                                                 \
    } while (0)

int main(void)
{
    ol_t ol;
    uintptr_t r;

    OL_new(&ol, repl);

    r = OL_eval(&ol, new_string(&ol, "(* 6 7)"), 0);
    CHECK(is_number(r) && ol2int(r) == 42, "(* 6 7) evaluates to 42");

    r = OL_eval(&ol, new_string(&ol, "+"), make_integer(1), make_integer(2),
                make_integer(39), 0);
    CHECK(is_number(r) && ol2int(r) == 42, "(+ 1 2 39) evaluates to 42");

    r = OL_eval(&ol,
                new_string(&ol,
                           "(define (fact n) (if (eq? n 0) 1 (* n (fact (- n 1)))))"),
                0);
    CHECK(r != IFALSE, "defining (fact n) succeeds");

    r = OL_eval(&ol, new_string(&ol, "fact"), make_integer(5), 0);
    CHECK(is_number(r) && ol2int(r) == 120, "(fact 5) evaluates to 120");

    r = OL_eval(&ol, new_string(&ol, "(string-length \"Otus Lisp\")"), 0);
    CHECK(is_number(r) && ol2int(r) == 9, "string-length \"Otus Lisp\" == 9");

    printf("embed_test: failures=%d\n", failures);
    OL_delete(&ol);
    if (failures) {
        printf("embed_test: FAILED\n");
        return 1;
    }
    printf("embed_test: ALL PASS\n");
    return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* fontutils utility library API (libfontutils.a) */
extern char *make_suffix ();
extern unsigned atou ();

int main (void)
{
    char *s = make_suffix ("cmr10", "tfm");
    if (s == NULL) {
        fprintf (stderr, "CHECK1 FAIL: make_suffix returned NULL\n");
        return 1;
    }
    printf ("CHECK1: make_suffix returned %s\n", s);
    if (strcmp (s, "cmr10.tfm") != 0) {
        fprintf (stderr, "CHECK2 FAIL: expected cmr10.tfm got %s\n", s);
        return 2;
    }
    printf ("CHECK2: strcmp cmr10.tfm OK\n");
    if (atou ("42") != 42u) {
        fprintf (stderr, "CHECK3 FAIL: atou wrong\n");
        return 3;
    }
    printf ("CHECK3: atou OK\n");
    printf ("fontutils lib API OK\n");
    return 0;
}

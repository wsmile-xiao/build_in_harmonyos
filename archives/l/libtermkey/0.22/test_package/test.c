/*
 * test_package consumer test for libtermkey 0.22.
 *
 * Real API calls (R34 compliance — not a stub).  Avoids dependency on
 * TERMINFO data (unibilium needs TERMINFO_DIRS to resolve byte sequences),
 * mirroring upstream t/01base.c which tests lifecycle + strfkey directly:
 *   - termkey_new_abstract / termkey_free
 *   - termkey_get_buffer_size / termkey_is_started / termkey_start
 *   - termkey_strfkey with a manually-built TermKeyKey (TERMKEY_TYPE_KEYSYM)
 */
#include <stdio.h>
#include <string.h>

#include <termkey.h>

int main(void)
{
    /* Abstract instance, no tty needed.  Terminal name must be a real name
     * (e.g. "vt100") so the abstract driver is usable. */
    TermKey *tk = termkey_new_abstract("vt100", 0);
    if (!tk) {
        fprintf(stderr, "termkey_new_abstract returned NULL\n");
        return 1;
    }

    /* Lifecycle: buffer size + started state (as upstream t/01base.c). */
    if (termkey_get_buffer_size(tk) <= 0) {
        fprintf(stderr, "termkey_get_buffer_size invalid\n");
        termkey_free(tk);
        return 1;
    }
    if (!termkey_is_started(tk)) {
        fprintf(stderr, "termkey_is_started false after construction\n");
        termkey_free(tk);
        return 1;
    }

    /* strfkey on a manually built keysym key (e.g. Arrow Up).
     * Formatting a known symbol needs no terminfo data. */
    TermKeyKey key;
    memset(&key, 0, sizeof(key));
    key.type = TERMKEY_TYPE_KEYSYM;
    key.code.sym = TERMKEY_SYM_UP;
    key.modifiers = 0;

    char buf[64];
    if (termkey_strfkey(tk, buf, sizeof(buf), &key, TERMKEY_FORMAT_VIM) < 0) {
        fprintf(stderr, "termkey_strfkey failed\n");
        termkey_free(tk);
        return 1;
    }
    if (strlen(buf) == 0) {
        fprintf(stderr, "termkey_strfkey returned empty string\n");
        termkey_free(tk);
        return 1;
    }

    termkey_free(tk);
    printf("test_libtermkey: OK (%s)\n", buf);
    return 0;
}

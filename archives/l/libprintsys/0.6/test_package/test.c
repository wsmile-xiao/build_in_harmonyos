/*
 * Functional test for libprintsys: exercise the printcap parser end to end.
 *
 * lps_init() -> printcap_init() -> printcap_get_printer_list() /
 * printcap_get_printer() -> lps_pair_lookup()/lps_num_pairs() -> lps_end()
 *
 * The assertions check real parse results (printer count, alias resolution and
 * spool-directory field), so a library that links but does not work fails here.
 *
 * Note: the sample printcap is written into the current working directory, not
 * /tmp, because /tmp is read-only on HarmonyOS PC.
 */
#include <stdio.h>
#include <string.h>
#include <wchar.h>

#include <printsys.h>
#include <printcap.h>

#define SAMPLE "test_printcap.dat"

/* two printers; the first one carries three aliases.
 * Only the continuation lines may end with '\' -- the last line of an entry has
 * to end with ':' and a plain newline, otherwise the parser glues the next
 * entry onto the current one and only a single printer is ever registered. */
static const char *SAMPLE_CONTENT =
    "lp|line1|lp1:\\\n"
    "\t:sd=/var/spool/lpd/lp:sh:rw:\n"
    "desk|deskjet:\\\n"
    "\t:sd=/var/spool/lpd/desk:\n";

static int fails;

static void check(int ok, const char *what)
{
    if (ok) {
        printf("  ok   %s\n", what);
    } else {
        printf("  FAIL %s\n", what);
        fails++;
    }
}

int main(void)
{
    FILE *f = fopen(SAMPLE, "w");
    if (!f) {
        perror("fopen");
        return 1;
    }
    fputs(SAMPLE_CONTENT, f);
    fclose(f);

    LPS_System_t *sys = lps_init(NULL);
    check(sys != NULL, "lps_init() returns a system handle");
    if (!sys)
        return 1;

    /* parse the file; the interesting outcome is what the parser produced */
    printcap_init(sys, SAMPLE);

    const wchar_t **list = printcap_get_printer_list(sys);
    check(list != NULL, "printcap_get_printer_list() returns a list");

    int n = 0;
    if (list) {
        while (list[n])
            n++;
    }
    check(n == 2, "both printers from the sample printcap were parsed");

    LPS_Printer_t *lp = printcap_get_printer(sys, L"lp");
    check(lp != NULL, "printer 'lp' is found by its primary name");

    /* alias lookup: line1 must resolve to the same entry as lp.  Guarded by
     * lp != NULL so a failed primary lookup cannot "pass" by comparing two
     * NULL pointers. */
    if (lp) {
        LPS_Printer_t *alias = printcap_get_printer(sys, L"line1");
        check(alias != NULL, "printer is also found through its alias 'line1'");
        check(alias == lp, "alias resolves to the same printer object");
    } else {
        check(0, "printer is also found through its alias 'line1'");
        check(0, "alias resolves to the same printer object");
    }

    if (lp) {
        check(lp->names && lp->names[0] && wcscmp(lp->names[0], L"lp") == 0,
              "primary name of the entry is 'lp'");

        wchar_t *sd = lps_pair_lookup(lp->fields, L"sd");
        check(sd && wcscmp(sd, L"/var/spool/lpd/lp") == 0,
              "capability field 'sd' is parsed with its value");

        wchar_t *sh = lps_pair_lookup(lp->fields, L"sh");
        check(sh != NULL, "boolean flag 'sh' is present");

        check(lps_num_pairs(lp->fields) >= 3,
              "all three capability pairs of the entry are kept");
    }

    /* lps_end() already calls printcap_end() internally (printsys.c:91), which is
     * why upstream's own pcaptest only calls lps_end().  Calling printcap_end()
     * here as well would destroy name_lookup twice -- the second destroy hits
     * the NULL it just set and GLib prints a CRITICAL. */
    lps_end(sys);
    remove(SAMPLE);

    if (fails) {
        printf("libprintsys test: %d check(s) failed\n", fails);
        return 1;
    }
    printf("libprintsys test: all checks passed (%d printers parsed)\n", n);
    return 0;
}

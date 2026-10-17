/* Consumer test for uid-wrapper (LD_PRELOAD interposition).
 *
 * The program must run with LD_PRELOAD=libuid_wrapper.so and
 * UID_WRAPPER=1 UID_WRAPPER_ROOT=1 set by the Conan test recipe.
 * It verifies that the wrapper interposes the uid/gid libc family:
 *   - getuid()/geteuid()/getgid()/getegid() report 0 (fake root)
 *   - seteuid() round-trips while the saved id keeps fake root
 *   - setgid()/setgroups() succeed under fake root
 *   - setresuid() transitions obey the saved-id rules of the wrapper
 *   - an unrelated-uid transition from a non-fake-root state fails EPERM
 */
#include <errno.h>
#include <grp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

static int failures = 0;

static void expect(const char *label, long actual, long expected)
{
    if (actual != expected) {
        fprintf(stderr, "%s mismatch: got %ld, expected %ld\n",
                label, actual, expected);
        failures++;
    }
}

int main(void)
{
    uid_t ruid, euid, suid;
    gid_t rgid, egid, sgid;
    gid_t glist[8];
    int rc;
    int ngroups;

    /* Fake root environment provided by the wrapper */
    expect("getuid()==0", (long)getuid(), 0);
    expect("geteuid()==0", (long)geteuid(), 0);
    expect("getgid()==0", (long)getgid(), 0);
    expect("getegid()==0", (long)getegid(), 0);

    /* Real id queries should agree while running as fake root */
    rc = getresuid(&ruid, &euid, &suid);
    if (rc != 0) {
        fprintf(stderr, "getresuid failed: %s\n", strerror(errno));
        failures++;
    } else {
        expect("getresuid ruid==0", (long)ruid, 0);
        expect("getresuid euid==0", (long)euid, 0);
        expect("getresuid suid==0", (long)suid, 0);
    }

    rc = getresgid(&rgid, &egid, &sgid);
    if (rc != 0) {
        fprintf(stderr, "getresgid failed: %s\n", strerror(errno));
        failures++;
    } else {
        expect("getresgid rgid==0", (long)rgid, 0);
        expect("getresgid egid==0", (long)egid, 0);
        expect("getresgid sgid==0", (long)sgid, 0);
    }

    /* seteuid keeps ruid=0 and suid=0, so the transition is reversible */
    if (seteuid(0x6666) != 0) {
        fprintf(stderr, "seteuid(0x6666) failed: %s\n", strerror(errno));
        failures++;
    } else {
        expect("geteuid() after seteuid", (long)geteuid(), 0x6666);
        expect("getuid() unchanged after seteuid", (long)getuid(), 0);
        if (seteuid(0) != 0) {
            fprintf(stderr, "seteuid(0) restore failed: %s\n",
                    strerror(errno));
            failures++;
        }
    }

    /* gid transitions under fake root (while euid is still 0) */
    if (setgid(0x7777) != 0) {
        fprintf(stderr, "setgid(0x7777) failed: %s\n", strerror(errno));
        failures++;
    } else {
        expect("getgid() after setgid", (long)getgid(), 0x7777);
        expect("getegid() after setgid", (long)getegid(), 0x7777);
    }

    glist[0] = 0x7777;
    if (setgroups(1, glist) != 0) {
        fprintf(stderr, "setgroups failed: %s\n", strerror(errno));
        failures++;
    } else {
        ngroups = getgroups(8, glist);
        if (ngroups < 0) {
            fprintf(stderr, "getgroups failed: %s\n", strerror(errno));
            failures++;
        } else if (ngroups != 1 || glist[0] != 0x7777) {
            fprintf(stderr, "getgroups mismatch: n=%d g0=%ld\n",
                    ngroups, (long)glist[0]);
            failures++;
        }
    }

    /* setresuid full triple transition under fake root */
    if (setresuid(0x1111, 0x2222, 0x3333) != 0) {
        fprintf(stderr, "setresuid failed: %s\n", strerror(errno));
        failures++;
    } else {
        rc = getresuid(&ruid, &euid, &suid);
        if (rc != 0) {
            fprintf(stderr, "getresuid after setresuid failed: %s\n",
                    strerror(errno));
            failures++;
        } else {
            expect("ruid after setresuid", (long)ruid, 0x1111);
            expect("euid after setresuid", (long)euid, 0x2222);
            expect("suid after setresuid", (long)suid, 0x3333);
        }
        /* with suid=0x3333 we can only return to one of the current ids */
        if (setresuid(0x1111, 0x1111, 0x1111) != 0) {
            fprintf(stderr, "setresuid(0x1111) restore failed: %s\n",
                    strerror(errno));
            failures++;
        } else {
            expect("ruid after restore", (long)getuid(), 0x1111);
        }
    }

    /* Privilege-rule enforcement: from the unprivileged triple
     * (0x1111, 0x1111, 0x1111) a transition to an unrelated uid must
     * fail with EPERM — the wrapper faithfully simulates POSIX rules. */
    if (setuid(0x5555) == 0) {
        fprintf(stderr, "setuid(0x5555) unexpectedly succeeded\n");
        failures++;
    } else if (errno != EPERM) {
        fprintf(stderr, "setuid(0x5555) errno mismatch: got %d, want EPERM\n",
                errno);
        failures++;
    } else {
        expect("uid unchanged after denied setuid", (long)getuid(), 0x1111);
    }

    if (failures != 0) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }

    puts("uid-wrapper LD_PRELOAD uid/gid interposition checks passed");
    return 0;
}

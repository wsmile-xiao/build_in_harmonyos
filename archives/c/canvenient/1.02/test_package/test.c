// CANvenient L1 test: link against the packaged library, enumerate CAN
// interfaces through the real public API and validate API behavior.
//
// On OHOS/CI hosts without CAN netdevs can_find_interfaces() must succeed and
// report zero interfaces (SocketCAN driver reads /sys/class/net); a non-zero
// return or crash indicates a broken adaptation.
#include <CANvenient.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    /* 1. Interface enumeration must not fail. */
    int rc = can_find_interfaces();
    if (0 != rc)
    {
        fprintf(stderr, "FAIL: can_find_interfaces() returned %d\n", rc);
        char err[256] = {0};
        can_get_error(err, sizeof(err));
        fprintf(stderr, "FAIL: error: %s\n", err);
        return EXIT_FAILURE;
    }

    /* 2. Error reason must be queryable (empty after a successful call). */
    char err[256] = {0};
    can_get_error(err, sizeof(err));

    /* 3. Scan all slots.  Unassigned slots must answer -1 with a
       non-empty error reason; assigned slots must return a non-empty name. */
    int found = 0;
    int unassigned = 0;
    for (int i = 0; i < CAN_MAX_INTERFACES; i++)
    {
        char name[256] = {0};
        int nrc = can_get_name(i, name, sizeof(name));
        if (0 == nrc)
        {
            if (name[0] == '\0')
            {
                fprintf(stderr, "FAIL: can_get_name(%d) succeeded with empty name\n", i);
                return EXIT_FAILURE;
            }
            printf("info: found CAN interface %d: %s\n", i, name);
            found++;
        }
        else if (-1 == nrc)
        {
            char r[256] = {0};
            can_get_error(r, sizeof(r));
            if (r[0] == '\0')
            {
                fprintf(stderr, "FAIL: can_get_name(%d) failed with empty error reason\n", i);
                return EXIT_FAILURE;
            }
            unassigned++;
        }
        else
        {
            fprintf(stderr, "FAIL: can_get_name(%d) returned unexpected %d\n", i, nrc);
            return EXIT_FAILURE;
        }
    }
    printf("info: can_find_interfaces found %d interface(s), %d unassigned slot(s)\n",
           found, unassigned);
    if (found + unassigned != CAN_MAX_INTERFACES)
    {
        fprintf(stderr, "FAIL: slot accounting mismatch (%d + %d != %d)\n",
                found, unassigned, CAN_MAX_INTERFACES);
        return EXIT_FAILURE;
    }

    /* 4. Out-of-range access must fail cleanly (negative return, no crash). */
    int bad = can_open(CAN_MAX_INTERFACES, CAN_BAUD_1M);
    if (0 <= bad)
    {
        fprintf(stderr, "FAIL: can_open(out-of-range) unexpectedly succeeded (%d)\n", bad);
        return EXIT_FAILURE;
    }

    /* 5. Baudrate of an unassigned slot must be readable (default enum). */
    enum can_baudrate baud = CAN_BAUD_1M;
    if (0 != can_get_baudrate(0, &baud))
    {
        fprintf(stderr, "FAIL: can_get_baudrate(0) failed on fresh state\n");
        return EXIT_FAILURE;
    }

    /* 6. Release all interfaces cleanly. */
    can_release_interfaces();

    printf("PASS: canvenient L1 test\n");
    return EXIT_SUCCESS;
}

/* withinclude.c — forces splint to run its pre-processor and write a scratch file,
 * which is what exercises the TMPDIR support (see test.sh check 5). */

#include "local.h"

int main (void)
{
    return helper (0);
}

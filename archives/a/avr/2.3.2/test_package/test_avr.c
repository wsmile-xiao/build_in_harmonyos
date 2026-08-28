#include <avr/io.h>
#include <avr/version.h>
#include <math.h>
#include <stddef.h>
#include <string.h>

_Static_assert(__AVR_LIBC_MAJOR__ == 2, "unexpected AVR-LibC major version");
_Static_assert(__AVR_LIBC_MINOR__ == 3, "unexpected AVR-LibC minor version");
_Static_assert(__AVR_LIBC_REVISION__ == 2, "unexpected AVR-LibC revision");

static volatile char source_data[] = "Harmony";
static char destination[sizeof(source_data)];

int main(void)
{
    double angle = source_data[0] == 'H' ? 0.5 : 1.0;
    memcpy(destination, (const void *)source_data, sizeof(source_data));

    if (strlen(destination) != 7 || destination[6] != 'y') {
        return 1;
    }

    return sin(angle) > 0.0 ? 0 : 2;
}

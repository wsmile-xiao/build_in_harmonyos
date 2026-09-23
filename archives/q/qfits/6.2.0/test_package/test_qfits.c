#include <qfits.h>
#include <stdio.h>

int main(void)
{
    const char *version = qfits_version();

    printf("QFITS_VERSION=%s\n", version ? version : "(null)");

    return (version != NULL && version[0] != '\0') ? 0 : 1;
}

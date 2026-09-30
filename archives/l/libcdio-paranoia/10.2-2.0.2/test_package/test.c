#include <stdio.h>
#include <string.h>

#include <cdio/paranoia/cdda.h>
#include <cdio/paranoia/paranoia.h>

int main(void)
{
    const char *cdda_version_text = cdio_cddap_version();
    const char *paranoia_version_text = cdio_paranoia_version();

    if (cdda_version_text == NULL || cdda_version_text[0] == '\0') {
        fprintf(stderr, "cdio_cddap_version() returned an empty string\n");
        return 1;
    }
    if (paranoia_version_text == NULL || paranoia_version_text[0] == '\0') {
        fprintf(stderr, "cdio_paranoia_version() returned an empty string\n");
        return 1;
    }

    printf("cdda=%s\nparanoia=%s\n", cdda_version_text, paranoia_version_text);
    return 0;
}

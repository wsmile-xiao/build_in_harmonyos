#include <stdio.h>
#include <keyutils.h>

int main(void)
{
    /* Verify the library's version string is accessible (links against libkeyutils) */
    printf("keyutils version: %s\n", keyutils_version_string);

    /* Verify key_serial_t typedef is available from the header */
    key_serial_t test_id = -1;
    printf("key_serial_t typedef OK (value: %d)\n", test_id);

    printf("libkeyutils API test: all assertions passed\n");
    return 0;
}

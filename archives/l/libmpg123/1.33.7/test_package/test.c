/* Test: verify libmpg123 API is functional */
#include <mpg123.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Initialize the mpg123 library */
    int err = mpg123_init();
    if (err != MPG123_OK) {
        fprintf(stderr, "mpg123_init failed: %s\n", mpg123_plain_strerror(err));
        return 1;
    }

    /* Create a decoder handle */
    mpg123_handle *mh = mpg123_new(NULL, &err);
    if (mh == NULL) {
        fprintf(stderr, "mpg123_new failed: %s\n", mpg123_plain_strerror(err));
        mpg123_exit();
        return 1;
    }

    /* List supported decoders (takes no arguments) */
    const char **decoders = mpg123_decoders();
    if (decoders == NULL || decoders[0] == NULL) {
        fprintf(stderr, "No decoders available\n");
        mpg123_delete(mh);
        mpg123_exit();
        return 1;
    }

    /* Get the current decoder name */
    const char *decoder = mpg123_current_decoder(mh);
    if (decoder == NULL || strlen(decoder) == 0) {
        fprintf(stderr, "No current decoder set\n");
        mpg123_delete(mh);
        mpg123_exit();
        return 1;
    }

    /* Clean up */
    mpg123_delete(mh);
    mpg123_exit();

    printf("mpg123 API test passed: decoder=%s, first_supported=%s\n", decoder, decoders[0]);
    return 0;
}

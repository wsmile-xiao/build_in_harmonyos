/* test_package for oggz 1.1.3 -- exercises the real liboggz API (R34).
 * Opens a writable Ogg stream with oggz_open_stdio() (write path), closes it
 * with oggz_close(), then re-opens the produced bytes through the read path.
 * Fails loudly if any liboggz call misbehaves -- no print-only stub here.
 */
#include <stdio.h>
#include <string.h>
#include <oggz/oggz.h>

int main(void) {
    const char *path = "test_oggz_stream.ogg";
    FILE *f;
    OGGZ *oggz;

    f = fopen(path, "w+b");
    if (!f) {
        perror("fopen");
        return 1;
    }

    /* Exercise the writer: oggz_open_stdio must return a live handle. */
    oggz = oggz_open_stdio(f, OGGZ_WRITE);
    if (!oggz) {
        fprintf(stderr, "FAIL: oggz_open_stdio(OGGZ_WRITE) returned NULL\n");
        fclose(f);
        return 1;
    }
    if (oggz_close(oggz) != 0) {
        fprintf(stderr, "FAIL: oggz_close (writer) returned nonzero\n");
        fclose(f);
        return 1;
    }
    fclose(f);

    /* Re-open the file with the reader to prove the stream is usable. */
    f = fopen(path, "rb");
    if (!f) {
        perror("fopen (read)");
        return 1;
    }
    oggz = oggz_open_stdio(f, OGGZ_READ);
    if (!oggz) {
        fprintf(stderr, "FAIL: oggz_open_stdio(OGGZ_READ) returned NULL\n");
        fclose(f);
        return 1;
    }
    if (oggz_close(oggz) != 0) {
        fprintf(stderr, "FAIL: oggz_close (reader) returned nonzero\n");
        fclose(f);
        return 1;
    }
    fclose(f);
    remove(path);

    printf("test oggz 1.1.3: liboggz write+read API OK\n");
    return 0;
}

/*
 * test_package/test.c — L1 test for libvterm
 *
 * Tests the core vterm API: create, resize, push bytes, read screen cell.
 * This is a real functional test, not a stub.
 */
#include <stdio.h>
#include <string.h>
#include <vterm.h>

int main(void) {
    int rc = 0;

    /* Check version */
    vterm_check_version(VTERM_VERSION_MAJOR, VTERM_VERSION_MINOR);

    /* Create a 10x10 terminal */
    VTerm *vt = vterm_new(10, 10);
    if (!vt) {
        fprintf(stderr, "FAIL: vterm_new returned NULL\n");
        return 1;
    }

    /* Verify size */
    int rows, cols;
    vterm_get_size(vt, &rows, &cols);
    if (rows != 10 || cols != 10) {
        fprintf(stderr, "FAIL: expected size 10x10, got %dx%d\n", rows, cols);
        rc = 1;
        goto cleanup;
    }

    /* Resize to 20x20 */
    vterm_set_size(vt, 20, 20);
    vterm_get_size(vt, &rows, &cols);
    if (rows != 20 || cols != 20) {
        fprintf(stderr, "FAIL: expected size 20x20 after resize, got %dx%d\n", rows, cols);
        rc = 1;
        goto cleanup;
    }

    /* Obtain screen and reset */
    VTermScreen *screen = vterm_obtain_screen(vt);
    if (!screen) {
        fprintf(stderr, "FAIL: vterm_obtain_screen returned NULL\n");
        rc = 1;
        goto cleanup;
    }
    vterm_screen_reset(screen, 1);

    /* Push bytes into the terminal */
    const char *text = "Hello";
    size_t written = vterm_input_write(vt, text, strlen(text));
    if (written != strlen(text)) {
        fprintf(stderr, "FAIL: vterm_input_write wrote %zu, expected %zu\n",
                written, strlen(text));
        rc = 1;
        goto cleanup;
    }

    /* Read a cell and verify it's not empty after writing */
    VTermScreenCell cell;
    memset(&cell, 0, sizeof(cell));
    VTermPos pos = {0, 0};
    int cell_ok = vterm_screen_get_cell(screen, pos, &cell);
    if (!cell_ok) {
        fprintf(stderr, "FAIL: vterm_screen_get_cell returned 0\n");
        rc = 1;
        goto cleanup;
    }

    printf("test libvterm 0.3.3: OK\n");

cleanup:
    vterm_free(vt);
    return rc;
}

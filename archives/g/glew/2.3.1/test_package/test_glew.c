#include <stdio.h>
#include <string.h>

#include <GL/glew.h>

static int expect_version(GLenum selector, const char *expected,
                          const char *label) {
    const GLubyte *actual = glewGetString(selector);
    if (actual == NULL || strcmp((const char *)actual, expected) != 0) {
        fprintf(stderr, "GLEW %s mismatch: expected %s, got %s\n", label,
                expected, actual == NULL ? "(null)" : (const char *)actual);
        return 1;
    }
    return 0;
}

int main(void) {
    if (expect_version(GLEW_VERSION, "2.3.1", "version") != 0 ||
        expect_version(GLEW_VERSION_MAJOR, "2", "major version") != 0 ||
        expect_version(GLEW_VERSION_MINOR, "3", "minor version") != 0 ||
        expect_version(GLEW_VERSION_MICRO, "1", "micro version") != 0) {
        return 1;
    }
    puts("GLEW 2.3.1 consumer API test: OK");
    return 0;
}

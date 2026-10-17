// test_package/test.cpp — Consumer-side test for gles2 2.0.25
// R34: Must substantively depend on the tested package.
// Calls GL::init() and GL::getError() to verify the library links and works.

#include "gl.h"

#include <cstdio>

int main(void) {
    // Initialize the GL dummy wrapper
    GL::init();

    // The dummy wrapper returns GL_INVALID_OPERATION for getError()
    // (which is the expected behaviour for a stub implementation)
    GL::Enum err = GL::getError();
    if (err != GL::INVALID_OPERATION) {
        printf("FAIL: getError() returned %d, expected GL_INVALID_OPERATION\n", static_cast<int>(err));
        return 1;
    }

    // Test getInteger using a known constant
    GL::Int value = GL::getInteger(GL::VENDOR);
    (void)value; // dummy returns 0, just verify it links and runs

    printf("test gles2 2.0.25: OK (init + getError + getInteger)\n");
    return 0;
}

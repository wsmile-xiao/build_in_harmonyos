#include <stdio.h>
#include <GL/glxtokens.h>

int main(void) {
    /* Verify glproto headers are accessible and contain expected definitions */
    if (GLX_RGBA != 4) {
        fprintf(stderr, "glproto: unexpected GLX_RGBA value %d\n", GLX_RGBA);
        return 1;
    }
    if (GLX_DOUBLEBUFFER != 5) {
        fprintf(stderr, "glproto: unexpected GLX_DOUBLEBUFFER value %d\n", GLX_DOUBLEBUFFER);
        return 1;
    }
    printf("glproto 1.4.17: GLX tokens headers OK\n");
    return 0;
}

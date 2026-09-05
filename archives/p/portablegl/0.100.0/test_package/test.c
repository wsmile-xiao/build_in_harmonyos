/*
 * portablegl 0.100.0 test_package — offline rendering verification (R34/R40).
 *
 * Real rendering path on a memory framebuffer, no window system required:
 *   1. init_glContext  -> software rasterizer context in RAM
 *   2. glClear(blue)   -> read back pixels, assert clear color
 *   3. glDrawElements  -> rasterize a viewport-filling red quad
 *                         (vertex+index buffers, user shaders via
 *                         pglCreateProgram/pglSetUniform)
 *   4. read back pixels at center/corner/edge, assert red
 *   5. free_glContext
 *
 * Exit code 0 only if all 5 pixel assertions pass.
 */
#define PGL_EXCLUDE_STUBS
#define PORTABLEGL_IMPLEMENTATION
#include "portablegl.h"

#include <stdio.h>

#define WIDTH 320
#define HEIGHT 240

static pix_t* bbufpix = NULL;
static glContext ctx;

typedef struct My_Uniforms
{
    vec4 v_color;
} My_Uniforms;

static void identity_vs(float* vs_output, vec4* vertex_attribs,
                        Shader_Builtins* builtins, void* uniforms)
{
    (void)vs_output; (void)uniforms;
    builtins->gl_Position = vertex_attribs[0];
}

static void uniform_color_fs(float* fs_input, Shader_Builtins* builtins,
                             void* uniforms)
{
    (void)fs_input;
    builtins->gl_FragColor = ((My_Uniforms*)uniforms)->v_color;
}

static int check_pixel(const char* what, int x, int y,
                       unsigned char r, unsigned char g, unsigned char b)
{
    pix_t p = bbufpix[y * WIDTH + x];
    unsigned char pr = (unsigned char)((p & PGL_RMASK) >> PGL_RSHIFT);
    unsigned char pg = (unsigned char)((p & PGL_GMASK) >> PGL_GSHIFT);
    unsigned char pb = (unsigned char)((p & PGL_BMASK) >> PGL_BSHIFT);
    if (pr != r || pg != g || pb != b) {
        printf("FAIL %s @(x=%d,y=%d): got (R=%u,G=%u,B=%u) "
               "expected (R=%u,G=%u,B=%u)\n",
               what, x, y, pr, pg, pb, r, g, b);
        return 1;
    }
    printf("PASS %s @(x=%d,y=%d): (R=%u,G=%u,B=%u)\n",
           what, x, y, pr, pg, pb);
    return 0;
}

int main(void)
{
    int fails = 0;

    /* 1. offline GL context on a RAM framebuffer */
    if (!init_glContext(&ctx, &bbufpix, WIDTH, HEIGHT)) {
        printf("FATAL: init_glContext failed\n");
        return 1;
    }
    printf("glContext initialized (%dx%d, framebuffer=%p)\n",
           WIDTH, HEIGHT, (void*)bbufpix);

    /* 2. clear to pure blue, assert pixels */
    glClearColor(0.0f, 0.0f, 1.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    fails += check_pixel("clear color center", WIDTH / 2, HEIGHT / 2, 0, 0, 255);
    fails += check_pixel("clear color corner", 2, 2, 0, 0, 255);

    /* 3. user shader pair + viewport-filling red quad (2 triangles) */
    GLuint program = pglCreateProgram(identity_vs, uniform_color_fs,
                                      0, NULL, GL_FALSE);
    glUseProgram(program);

    My_Uniforms the_uniforms;
    the_uniforms.v_color = (vec4){ 1.0f, 0.0f, 0.0f, 1.0f };
    pglSetUniform(&the_uniforms);

    GLuint vao;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);

    float quad[] = {
        -1.0f, -1.0f, 0.0f,
         1.0f, -1.0f, 0.0f,
         1.0f,  1.0f, 0.0f,
        -1.0f,  1.0f, 0.0f,
    };
    GLubyte indices[] = { 0, 1, 2, 0, 2, 3 };

    GLuint vbo;
    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(quad), quad, GL_STATIC_DRAW);
    glEnableVertexAttribArray(PGL_ATTR_VERT);
    glVertexAttribPointer(PGL_ATTR_VERT, 3, GL_FLOAT, GL_FALSE, 0, 0);

    GLuint ibo;
    glGenBuffers(1, &ibo);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(indices),
                 indices, GL_STATIC_DRAW);

    glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_BYTE, 0);

    /* 4. whole viewport must now be red */
    fails += check_pixel("quad fill center", WIDTH / 2, HEIGHT / 2, 255, 0, 0);
    fails += check_pixel("quad fill corner", 2, 2, 255, 0, 0);
    fails += check_pixel("quad fill edge  ", WIDTH - 3, HEIGHT - 3, 255, 0, 0);

    glDeleteBuffers(1, &ibo);
    glDeleteBuffers(1, &vbo);
    glDeleteVertexArrays(1, &vao);
    glDeleteProgram(program);

    free_glContext(&ctx);
    bbufpix = NULL;

    if (fails) {
        printf("RESULT: FAILED (%d pixel assertions failed)\n", fails);
        return 1;
    }
    printf("RESULT: PASSED (all 5 pixel assertions passed, "
           "offline rendering verified)\n");
    return 0;
}

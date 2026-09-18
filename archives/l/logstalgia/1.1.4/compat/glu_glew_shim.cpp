/* GLU + GLEW runtime shim for Logstalgia 1.1.4 on HarmonyOS PC.
 *
 * gl4es ships the GLU *declarations* (GL/glu.h) but no GLU *implementations*
 * (libGL.so exports no glu* symbols). Logstalgia (src/core/display.cpp,
 * src/core/texture.cpp, src/core/gl.h) uses exactly five GLU functions:
 *   gluPerspective, gluProject, gluUnProject, gluErrorString, gluBuild2DMipmaps
 * plus the configure-time conftest symbol gluBeginCurve.
 * The matrix helpers are transcribed from Mesa GLU (SGI reference
 * implementation, MIT license): src/glu/sgi/libutil/project.c.
 * glewInit()/glewGetErrorString()/glewExperimental satisfy the GLEW shim.
 */
#include <GL/gl.h>
#include <GL/glu.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#ifndef GLEW_OK
#define GLEW_OK 0
#endif

extern "C" {

/* ---- GLEW runtime shim ---- */
GLboolean glewExperimental = GL_FALSE;

GLenum glewInit(void) {
    /* gl4es lazily initializes itself on first GL call. */
    return GLEW_OK;
}

const GLubyte* glewGetErrorString(GLenum error) {
    switch (error) {
        case GLEW_OK: return (const GLubyte*)"No error";
        default:      return (const GLubyte*)"Unknown GLEW error";
    }
}

/* ---- GLU ---- */
const GLubyte* gluErrorString(GLenum error) {
    switch (error) {
        case GL_NO_ERROR:          return (const GLubyte*)"no error";
        case GL_INVALID_ENUM:      return (const GLubyte*)"invalid enumerant";
        case GL_INVALID_VALUE:     return (const GLubyte*)"invalid value";
        case GL_INVALID_OPERATION: return (const GLubyte*)"invalid operation";
        case GL_STACK_OVERFLOW:    return (const GLubyte*)"stack overflow";
        case GL_STACK_UNDERFLOW:   return (const GLubyte*)"stack underflow";
        case GL_OUT_OF_MEMORY:     return (const GLubyte*)"out of memory";
        default:                   return (const GLubyte*)"unknown GL error";
    }
}

/* configure conftest-only symbol (never called at runtime). */
void gluBeginCurve(GLUnurbs* /*nurb*/) {}

void gluPerspective(GLdouble fovy, GLdouble aspect, GLdouble zNear, GLdouble zFar) {
    GLdouble m[16];
    GLdouble f = 1.0 / tan(fovy * 3.14159265358979323846 / 360.0);
    std::memset(m, 0, sizeof(m));
    m[0]  = f / aspect;
    m[5]  = f;
    m[10] = (zFar + zNear) / (zNear - zFar);
    m[11] = -1.0;
    m[14] = (2.0 * zFar * zNear) / (zNear - zFar);
    glMultMatrixd(m);
}

/* 4x4 matrix helpers transcribed from Mesa GLU
 * (src/glu/sgi/libutil/project.c, __gluInvertMatrixd / __gluMultMatricesd /
 * __gluMultMatrixVecd) - the canonical SGI reference implementation.
 * Fixes two defects found by AI review (PR #9149): the previous hand-rolled
 * elimination was not Gauss-Jordan and returned GL_FALSE even for the
 * identity matrix; multiply_matrix computed b*a instead of a*b. */

/* Computes r = a*b in column-major storage, i.e. the mathematical product
 * of a followed by b (r[i][j] = sum_k a[i][k] * b[k][j], stored as
 * r[i*4+j]). With column-major 4x4s and column-vector convention this
 * composes b first, then a - which is exactly what gluUnProject needs
 * (A = P*M, modelview applied before projection). Verified by
 * glu_glew_shim_selftest below (PR #9149 fix). */
static void multiply_matrix(const GLdouble a[16], const GLdouble b[16], GLdouble r[16]) {
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            r[i*4+j] =
                a[i*4+0]*b[0*4+j] +
                a[i*4+1]*b[1*4+j] +
                a[i*4+2]*b[2*4+j] +
                a[i*4+3]*b[3*4+j];
        }
    }
}

static void transform_vec(const GLdouble m[16], const GLdouble in[4], GLdouble out[4]) {
    out[0] = m[0]*in[0] + m[4]*in[1] + m[ 8]*in[2] + m[12]*in[3];
    out[1] = m[1]*in[0] + m[5]*in[1] + m[ 9]*in[2] + m[13]*in[3];
    out[2] = m[2]*in[0] + m[6]*in[1] + m[10]*in[2] + m[14]*in[3];
    out[3] = m[3]*in[0] + m[7]*in[1] + m[11]*in[2] + m[15]*in[3];
}

/* Gauss-Jordan elimination with partial pivoting (Mesa __gluInvertMatrixd). */
static int invert_matrix(const GLdouble m[16], GLdouble invOut[16]) {
    GLdouble inv[16], trans[16];
    int i, j, k;

    for (i = 0; i < 16; i++) inv[i] = 0.0;

    inv[0]  = 1.0; inv[5]  = 1.0; inv[10] = 1.0; inv[15] = 1.0;
    for (i = 0; i < 4; i++)
        for (j = 0; j < 4; j++)
            trans[i*4+j] = m[j*4+i];

    for (i = 0; i < 4; i++) {
        /* pivot: find the row with the largest magnitude in column i */
        int pivot_row = i;
        GLdouble pivot_val = trans[i*4+i];
        for (j = i + 1; j < 4; j++) {
            if (std::fabs(trans[j*4+i]) > std::fabs(pivot_val)) {
                pivot_val = trans[j*4+i];
                pivot_row = j;
            }
        }
        if (pivot_val == 0.0) return GL_FALSE; /* singular */

        if (pivot_row != i) {
            for (k = 0; k < 4; k++) {
                GLdouble t = trans[i*4+k];
                trans[i*4+k] = trans[pivot_row*4+k];
                trans[pivot_row*4+k] = t;
                t = inv[i*4+k];
                inv[i*4+k] = inv[pivot_row*4+k];
                inv[pivot_row*4+k] = t;
            }
        }

        pivot_val = trans[i*4+i];
        for (k = 0; k < 4; k++) {
            trans[i*4+k] /= pivot_val;
            inv[i*4+k]   /= pivot_val;
        }
        for (j = 0; j < 4; j++) {
            if (j != i) {
                GLdouble factor = trans[j*4+i];
                if (factor != 0.0) {
                    for (k = 0; k < 4; k++) {
                        trans[j*4+k] -= factor * trans[i*4+k];
                        inv[j*4+k]   -= factor * inv[i*4+k];
                    }
                }
            }
        }
    }
    /* The elimination above ran on the transposed system, so `inv` holds
     * (A^-1)^T in column-major storage. Transpose once more to return the
     * column-major A^-1 that transform_vec (column-vector multiply)
     * expects. (Mesa pairs its transposed inverse with a row-vector
     * multiply instead; we keep the column-vector convention here.) */
    for (i = 0; i < 4; i++) {
        for (j = 0; j < 4; j++) {
            invOut[i*4+j] = inv[j*4+i];
        }
    }
    return GL_TRUE;
}

GLint gluProject(GLdouble objX, GLdouble objY, GLdouble objZ,
                 const GLdouble model[16], const GLdouble proj[16],
                 const GLint viewport[4],
                 GLdouble* winX, GLdouble* winY, GLdouble* winZ) {
    GLdouble in[4], tmp[4], out[4];

    in[0] = objX; in[1] = objY; in[2] = objZ; in[3] = 1.0;
    transform_vec(model, in, tmp);   /* modelview first ... */
    transform_vec(proj,  tmp, out);  /* ... then projection: win = P*M*obj */
    if (out[3] == 0.0) return GL_FALSE;
    out[0] /= out[3]; out[1] /= out[3]; out[2] /= out[3];
    /* viewport mapping (viewport[3] can be negative per GL spec) */
    *winX = viewport[0] + (1.0 + out[0]) * 0.5 * viewport[2];
    *winY = viewport[1] + (1.0 + out[1]) * 0.5 * viewport[3];
    *winZ = (1.0 + out[2]) * 0.5;
    return GL_TRUE;
}

GLint gluUnProject(GLdouble winX, GLdouble winY, GLdouble winZ,
                   const GLdouble model[16], const GLdouble proj[16],
                   const GLint viewport[4],
                   GLdouble* objX, GLdouble* objY, GLdouble* objZ) {
    GLdouble m[16], A[16], in[4], out[4];

    multiply_matrix(model, proj, A);           /* A = P*M */
    if (!invert_matrix(A, m)) return GL_FALSE; /* m = (P*M)^-1 */

    in[0] = (winX - viewport[0]) / viewport[2] * 2.0 - 1.0;
    in[1] = (winY - viewport[1]) / viewport[3] * 2.0 - 1.0;
    in[2] = 2.0 * winZ - 1.0;
    in[3] = 1.0;

    transform_vec(m, in, out);
    if (out[3] == 0.0) return GL_FALSE;
    out[0] /= out[3]; out[1] /= out[3]; out[2] /= out[3];
    *objX = out[0]; *objY = out[1]; *objZ = out[2];
    return GL_TRUE;
}

GLint gluBuild2DMipmaps(GLenum target, GLint internalFormat,
                        GLsizei width, GLsizei height,
                        GLenum format, GLenum type, const void* data) {
    /* The only in-tree caller (Core texture.cpp) passes GL_ALPHA/GL_LUMINANCE/
     * GL_RGBA 8-bit data. Simple box-filtered half-scaling chain. */
    int components = (format == GL_ALPHA || format == GL_LUMINANCE) ? 1 : 4;
    GLubyte* prev = (GLubyte*)data;
    GLubyte* cur = NULL;
    GLsizei w = width, h = height;
    GLint level = 0;
    GLint r = 0;

    while (w >= 1 && h >= 1) {
        glTexImage2D(target, level, internalFormat, w, h, 0, format, type, prev);
        if (w == 1 && h == 1) break;
        GLsizei nw = w > 1 ? w / 2 : 1;
        GLsizei nh = h > 1 ? h / 2 : 1;
        cur = (GLubyte*)malloc((size_t)nw * nh * components);
        if (!cur) { r = GL_OUT_OF_MEMORY; break; }
        for (GLsizei y = 0; y < nh; y++) {
            GLsizei y0 = 2 * y, y1 = (2 * y + 1 < h) ? 2 * y + 1 : y0;
            for (GLsizei x = 0; x < nw; x++) {
                GLsizei x0 = 2 * x, x1 = (2 * x + 1 < w) ? 2 * x + 1 : x0;
                for (int c = 0; c < components; c++) {
                    unsigned v = prev[(y0 * w + x0) * components + c]
                               + prev[(y0 * w + x1) * components + c]
                               + prev[(y1 * w + x0) * components + c]
                               + prev[(y1 * w + x1) * components + c];
                    cur[(y * nw + x) * components + c] = (GLubyte)(v / 4);
                }
            }
        }
        if (prev != data) free(prev);
        prev = cur; cur = NULL;
        w = nw; h = nh; level++;
    }
    if (prev != data && prev) free(prev);
    return r;
}

/* ---- headless self-test (linked by the recipe build() probe AND by
 * test_package/test.c - see conanfile.py build() step 1.5 and
 * test_package/conanfile.py). Runs in every CI build, without any GL
 * context (pure maths).
 * Verifies the two matrix-maths defects fixed after AI review (PR #9149):
 *  1. invert_matrix must invert the identity (and a typical M*P composite)
 *     successfully - the previous implementation returned GL_FALSE even for
 *     the identity matrix.
 *  2. multiply_matrix / gluProject order must be win = P*M*obj, not M*P*obj.
 * AI review follow-up (PR #9643, 2026-09-12): the old comment claimed
 * "called by test_package" while only the build() probe linked it; the
 * self-test is now wired into test_package as well, so the consumer-side
 * test phase also fails on any matrix-maths regression. */
int glu_glew_shim_selftest(void) {
    const GLdouble eps = 1e-9;

    /* identity inverse stays identity */
    const GLdouble ident[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
    GLdouble inv[16];
    if (!invert_matrix(ident, inv)) return 1;
    for (int i = 0; i < 16; i++)
        if (std::fabs(inv[i] - ident[i]) > eps) return 2;

    /* multiply_matrix(a,b) must equal a*b (column-major, review example):
     * M = translate(1,2,3)  (col3 = 1,2,3,1)
     * P = diag(2,3,4,1)
     * P*M (column-major) = diag scaled translate: col3 = (2,6,12,1) */
    const GLdouble M[16] = {1,0,0,0, 0,1,0,0, 0,0,1,0, 1,2,3,1};
    const GLdouble P[16] = {2,0,0,0, 0,3,0,0, 0,0,4,0, 0,0,0,1};
    GLdouble A[16];
    multiply_matrix(M, P, A); /* A must be P*M */
    const GLdouble expected_PM[16] = {2,0,0,0, 0,3,0,0, 0,0,4,0, 2,6,12,1};
    for (int i = 0; i < 16; i++)
        if (std::fabs(A[i] - expected_PM[i]) > eps) return 3;

    /* gluProject: obj=(10,20,30), viewport=(0,0,1024,768)
     * clip = P*M*(10,20,30,1) = (2*11, 3*22, 4*33, 1) = (22,66,132,1) */
    const GLint vp[4] = {0, 0, 1024, 768};
    GLdouble wx, wy, wz;
    if (!gluProject(10.0, 20.0, 30.0, M, P, vp, &wx, &wy, &wz)) return 4;
    if (std::fabs(wx - (1.0 + 22.0) * 0.5 * 1024.0) > 1e-6) return 5;  /* 11776 */
    if (std::fabs(wy - (1.0 + 66.0) * 0.5 *  768.0) > 1e-6) return 6;  /* 25632 */
    if (std::fabs(wz - (1.0 + 132.0) * 0.5) > 1e-9) return 9;          /* 66.5 */

    /* gluProject/gluUnProject round-trip: project then unproject must give
     * back the original object coordinates. */
    if (!gluUnProject(wx, wy, wz, M, P, vp, &wx, &wy, &wz)) return 7;
    if (std::fabs(wx - 10.0) > 1e-6 || std::fabs(wy - 20.0) > 1e-6
        || std::fabs(wz - 30.0) > 1e-6) return 8;

    return 0; /* PASS */
}

} /* extern "C" */

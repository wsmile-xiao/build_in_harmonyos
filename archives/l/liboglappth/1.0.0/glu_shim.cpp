// glu_shim.cpp — minimal GLU implementation for liboglappth on OHOS.
//
// gl4es declares gluLookAt/gluPerspective/gluPickMatrix in <GL/glu.h> but
// ships no implementation, and no libGLU exists on OpenHarmony. liboglappth
// calls exactly these three functions (ogl_camera.cpp); this file implements
// them with plain GL 1.1 calls (the same reference formulas as Mesa's
// src/glu/sgi) and is compiled into the library.

#include <GL/gl.h>
#include <GL/glu.h>
#include <math.h>

extern "C" {

void GLAPIENTRY gluPerspective(GLdouble fovy, GLdouble aspect,
                               GLdouble zNear, GLdouble zFar)
{
    GLdouble left, right, bottom, top;

    top = zNear * tan(fovy * M_PI / 360.0);
    bottom = -top;
    left = bottom * aspect;
    right = top * aspect;

    glFrustum(left, right, bottom, top, zNear, zFar);
}

void GLAPIENTRY gluLookAt(GLdouble eyex, GLdouble eyey, GLdouble eyez,
                          GLdouble centerx, GLdouble centery, GLdouble centerz,
                          GLdouble upx, GLdouble upy, GLdouble upz)
{
    GLdouble m[16];
    GLdouble x[3], y[3], z[3];
    GLdouble mag;

    /* Make rotation matrix: Z = eye - center (normalized) */
    z[0] = eyex - centerx;
    z[1] = eyey - centery;
    z[2] = eyez - centerz;
    mag = sqrt(z[0] * z[0] + z[1] * z[1] + z[2] * z[2]);
    if (mag > 0.0) {
        z[0] /= mag;
        z[1] /= mag;
        z[2] /= mag;
    }

    /* Y = up (normalized) */
    y[0] = upx;
    y[1] = upy;
    y[2] = upz;

    /* X = Y cross Z */
    x[0] = y[1] * z[2] - y[2] * z[1];
    x[1] = y[2] * z[0] - y[0] * z[2];
    x[2] = y[0] * z[1] - y[1] * z[0];

    /* Y = Z cross X (re-orthogonalize) */
    y[0] = z[1] * x[2] - z[2] * x[1];
    y[1] = z[2] * x[0] - z[0] * x[2];
    y[2] = z[0] * x[1] - z[1] * x[0];

    mag = sqrt(x[0] * x[0] + x[1] * x[1] + x[2] * x[2]);
    if (mag > 0.0) {
        x[0] /= mag;
        x[1] /= mag;
        x[2] /= mag;
    }
    mag = sqrt(y[0] * y[0] + y[1] * y[1] + y[2] * y[2]);
    if (mag > 0.0) {
        y[0] /= mag;
        y[1] /= mag;
        y[2] /= mag;
    }

#define M(row, col) m[(col) * 4 + (row)]
    M(0, 0) = x[0]; M(0, 1) = y[0]; M(0, 2) = z[0]; M(0, 3) = 0.0;
    M(1, 0) = x[1]; M(1, 1) = y[1]; M(1, 2) = z[1]; M(1, 3) = 0.0;
    M(2, 0) = x[2]; M(2, 1) = y[2]; M(2, 2) = z[2]; M(2, 3) = 0.0;
    M(3, 0) = 0.0;  M(3, 1) = 0.0;  M(3, 2) = 0.0;  M(3, 3) = 1.0;
#undef M

    glMultMatrixd(m);

    /* Translate eye to origin */
    glTranslated(-eyex, -eyey, -eyez);
}

void GLAPIENTRY gluPickMatrix(GLdouble x, GLdouble y,
                              GLdouble width, GLdouble height,
                              GLint * viewport)
{
    GLfloat m[16];
    GLfloat sx, sy;
    GLfloat tx, ty;

    sx = (GLfloat)(viewport[2] / width);
    sy = (GLfloat)(viewport[3] / height);
    tx = (GLfloat)((viewport[2] + 2.0 * (viewport[0] - x)) / width);
    ty = (GLfloat)((viewport[3] + 2.0 * (viewport[1] - y)) / height);

#define PICKM(row, col) m[(col) * 4 + (row)]
    PICKM(0, 0) = sx;  PICKM(0, 1) = 0.0f; PICKM(0, 2) = 0.0f; PICKM(0, 3) = tx;
    PICKM(1, 0) = 0.0f; PICKM(1, 1) = sy;  PICKM(1, 2) = 0.0f; PICKM(1, 3) = ty;
    PICKM(2, 0) = 0.0f; PICKM(2, 1) = 0.0f; PICKM(2, 2) = 0.0f; PICKM(2, 3) = 0.0f;
    PICKM(3, 0) = 0.0f; PICKM(3, 1) = 0.0f; PICKM(3, 2) = 0.0f; PICKM(3, 3) = 1.0f;
#undef PICKM

    glMultMatrixf(m);
}

} // extern "C"

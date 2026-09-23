/* OHOS GLEW compatibility shim for Logstalgia 1.1.4.
 *
 * OHOS has no native GLEW package. Logstalgia only uses a tiny subset of
 * the GLEW API surface: glewInit(), glewGetErrorString(), glewExperimental
 * and the GLEW_VERSION_2_0 / GLEW_ERROR_NO_GLX_DISPLAY macros.
 *
 * gl4es (conan package gl4es/1.1.6) provides the desktop-GL 1.5/2.1
 * compatible <GL/gl.h> and <GL/glu.h> headers plus libGL.so, translating
 * the fixed-function pipeline to GLES2 at runtime. The GLEW runtime
 * functions are provided by glu_glew_shim.cpp (compiled into libGLU.a
 * and linked via GLU_LIBS).
 */
#ifndef OHOS_GLEW_SHIM_H
#define OHOS_GLEW_SHIM_H

#ifndef GL_GLEXT_PROTOTYPES
#define GL_GLEXT_PROTOTYPES 1
#endif
#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glu.h>

#define GLEW_OK 0
#define GLEW_ERROR_NO_GLX_DISPLAY 4
/* gl4es targets desktop GL 2.1 (shaders + FFP emulation): report 2.0. */
#define GLEW_VERSION_2_0 1

/* GLEW's real headers define every GL version constant regardless of the
 * runtime context. Core's shader.cpp references GL_COMPUTE_SHADER (GL 4.3,
 * only reached at runtime if a compute shader file exists - none ship with
 * logstalgia). gl4es' glext.h stops at GL 2.1, so provide the constant. */
#ifndef GL_COMPUTE_SHADER
#define GL_COMPUTE_SHADER 0x91B9
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned char GLbooleanShim;
extern GLbooleanShim glewExperimental;
const GLubyte* glewGetErrorString(GLenum error);
GLenum glewInit(void);

#ifdef __cplusplus
}
#endif

#endif /* OHOS_GLEW_SHIM_H */

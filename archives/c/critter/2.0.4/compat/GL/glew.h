/*
 * Minimal GLEW compatibility shim for OpenHarmony PC (OHOS).
 *
 * gl4es provides the GL 1.x/2.x entry points used by Critter, but the OHOS
 * platform ships no GLEW (neither headers nor library).  Critter's actual GLEW
 * surface is tiny: glewInit() and glewGetString(GLEW_VERSION); GLEW_ARB_* is
 * referenced only from a comment.  This header therefore re-exports the real
 * gl4es GL declarations and declares the two GLEW entry points, which are
 * implemented in glew-shim.c.
 */
#ifndef __OHOS_GLEW_SHIM_H__
#define __OHOS_GLEW_SHIM_H__

/* gl4es guards the GL 2.0/3.0 entry-point prototypes behind
 * GL_GLEXT_PROTOTYPES, which its GL/gl.h only sets for Emscripten and Apple.
 * Upstream GLEW declares those functions itself, so force the glext.h
 * prototype block on for OHOS as well. */
#ifndef GL_GLEXT_PROTOTYPES
#define GL_GLEXT_PROTOTYPES 1
#endif

#include <GL/gl.h>

#ifdef __cplusplus
extern "C" {
#endif

/* GLEW string index used by glewGetString(); mirrors the upstream value. */
#define GLEW_VERSION 1

#define GLEW_VERSION_1_1 1
#define GLEW_VERSION_1_2 1
#define GLEW_VERSION_1_3 1
#define GLEW_VERSION_1_4 1
#define GLEW_VERSION_1_5 1
#define GLEW_VERSION_2_0 1
#define GLEW_VERSION_2_1 1

#define GLEW_OK 0
#define GLEW_ERROR_NO_GL_VERSION 1
#define GLEW_ERROR_GL_VERSION_10_ONLY 2
#define GLEW_ERROR_GLX_VERSION_11_ONLY 3
#define GLEW_ERROR_NO_GLX_DISPLAY 4

/* GL_KHR_debug enums.  gl4es defines none of them and exports no
 * glDebugMessageCallback entry point, so the callback registered by
 * game/Video.cpp is a no-op (see glew-shim.c). */
#define GL_DEBUG_OUTPUT_SYNCHRONOUS 0x8242
#define GL_DEBUG_NEXT_LOGGED_MESSAGE_LENGTH 0x8243
#define GL_DEBUG_CALLBACK_FUNCTION 0x8244
#define GL_DEBUG_CALLBACK_USER_PARAM 0x8245
#define GL_DEBUG_SOURCE_API 0x8246
#define GL_DEBUG_SOURCE_WINDOW_SYSTEM 0x8247
#define GL_DEBUG_SOURCE_SHADER_COMPILER 0x8248
#define GL_DEBUG_SOURCE_THIRD_PARTY 0x8249
#define GL_DEBUG_SOURCE_APPLICATION 0x824A
#define GL_DEBUG_SOURCE_OTHER 0x824B
#define GL_DEBUG_TYPE_ERROR 0x824C
#define GL_DEBUG_TYPE_DEPRECATED_BEHAVIOR 0x824D
#define GL_DEBUG_TYPE_UNDEFINED_BEHAVIOR 0x824E
#define GL_DEBUG_TYPE_PORTABILITY 0x824F
#define GL_DEBUG_TYPE_PERFORMANCE 0x8250
#define GL_DEBUG_TYPE_OTHER 0x8251
#define GL_DEBUG_TYPE_MARKER 0x8268
#define GL_DEBUG_TYPE_PUSH_GROUP 0x8269
#define GL_DEBUG_TYPE_POP_GROUP 0x826A
#define GL_DEBUG_SEVERITY_HIGH 0x9146
#define GL_DEBUG_SEVERITY_MEDIUM 0x9147
#define GL_DEBUG_SEVERITY_LOW 0x9148
#define GL_DEBUG_SEVERITY_NOTIFICATION 0x826B
#define GL_DEBUG_OUTPUT 0x92E0

typedef void(GLAPIENTRY *GLDEBUGPROC)(GLenum source, GLenum type, GLuint id,
                                      GLenum severity, GLsizei length,
                                      const GLchar *message, const void *userParam);

GLenum glewInit(void);
const GLubyte *glewGetString(GLenum name);
GLAPI void GLAPIENTRY glDebugMessageCallback(GLDEBUGPROC callback, const void *userParam);
extern GLboolean glewExperimental;

#ifdef __cplusplus
}
#endif

#endif /* __OHOS_GLEW_SHIM_H__ */

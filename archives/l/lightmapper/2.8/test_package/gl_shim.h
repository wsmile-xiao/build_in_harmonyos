/* gl_shim.h — minimal OpenGL declarations for lightmapper test_package.
 *
 * lightmapper.h is a single-header library whose public API and
 * implementation section reference desktop-GL constants and functions; the
 * upstream design is that the consumer brings its own OpenGL.  The package
 * itself ships only the header and links nothing GL-related.
 *
 * This shim provides exactly the GL constants and function prototypes the
 * header needs to compile, and gl_shim.c provides link-time stub bodies.  The
 * test below only calls lightmapper's CPU-side image API, so none of these GL
 * stubs is ever executed at runtime.
 */
#ifndef GL_SHIM_H
#define GL_SHIM_H

/* --- types --- */
typedef unsigned int GLenum;
typedef unsigned int GLuint;
typedef int GLint;
typedef int GLsizei;
typedef float GLfloat;
typedef float GLclampf;
typedef unsigned int GLbitfield;
typedef char GLchar;
typedef unsigned char GLboolean;

/* --- constants used by lightmapper.h --- */
#define GL_FALSE 0
#define GL_TRUE  1
#define GL_UNSIGNED_BYTE  0x1401
#define GL_UNSIGNED_SHORT 0x1403
#define GL_UNSIGNED_INT   0x1405
#define GL_FLOAT          0x1406
#define GL_RG             0x8227
#define GL_RGB            0x1907
#define GL_RGBA           0x1908
#define GL_RG32F          0x8230
#define GL_RGBA32F        0x8814
#define GL_DEPTH_COMPONENT24 0x81A6
#define GL_COLOR_BUFFER_BIT  0x00004000
#define GL_DEPTH_BUFFER_BIT  0x00000100
#define GL_DEPTH_TEST        0x0B71
#define GL_TEXTURE_2D        0x0DE1
#define GL_TEXTURE0          0x84C0
#define GL_TEXTURE1          0x84C1
#define GL_TEXTURE_MAG_FILTER 0x2800
#define GL_TEXTURE_MIN_FILTER 0x2801
#define GL_TEXTURE_WRAP_S     0x2802
#define GL_TEXTURE_WRAP_T     0x2803
#define GL_CLAMP_TO_EDGE     0x812F
#define GL_REPEAT            0x2901
#define GL_NEAREST           0x2600
#define GL_TRIANGLE_STRIP    0x0005
#define GL_FRAMEBUFFER       0x8D40
#define GL_READ_FRAMEBUFFER  0x8CA8
#define GL_DRAW_FRAMEBUFFER  0x8CA9
#define GL_RENDERBUFFER      0x8D41
#define GL_COLOR_ATTACHMENT0 0x8CE0
#define GL_DEPTH_ATTACHMENT  0x8D00
#define GL_FRAMEBUFFER_COMPLETE 0x8CD5
#define GL_PIXEL_PACK_BUFFER 0x88EB
#define GL_VERTEX_SHADER     0x8B31
#define GL_FRAGMENT_SHADER   0x8B30
#define GL_COMPILE_STATUS    0x8B81
#define GL_LINK_STATUS       0x8B82
#define GL_INFO_LOG_LENGTH   0x8B84

/* --- function prototypes --- */
GLenum glCheckFramebufferStatus(GLenum target);
GLuint glCreateProgram(void);
GLuint glCreateShader(GLenum type);
GLint  glGetUniformLocation(GLuint program, const GLchar *name);
void glActiveTexture(GLenum texture);
void glAttachShader(GLuint program, GLuint shader);
void glBindBuffer(GLenum target, GLuint buffer);
void glBindFramebuffer(GLenum target, GLuint framebuffer);
void glBindRenderbuffer(GLenum target, GLuint renderbuffer);
void glBindTexture(GLenum target, GLuint texture);
void glBindVertexArray(GLuint array);
void glClear(GLbitfield mask);
void glClearColor(GLfloat r, GLfloat g, GLfloat b, GLfloat a);
void glCompileShader(GLuint shader);
void glCopyTexSubImage2D(GLenum target, GLint level, GLint xoffset, GLint yoffset, GLint x, GLint y, GLsizei width, GLsizei height);
void glDeleteFramebuffers(GLsizei n, const GLuint *framebuffers);
void glDeleteProgram(GLuint program);
void glDeleteRenderbuffers(GLsizei n, const GLuint *renderbuffers);
void glDeleteShader(GLuint shader);
void glDeleteTextures(GLsizei n, const GLuint *textures);
void glDeleteVertexArrays(GLsizei n, const GLuint *arrays);
void glDisable(GLenum cap);
void glDrawArrays(GLenum mode, GLint first, GLsizei count);
void glEnable(GLenum cap);
void glFramebufferRenderbuffer(GLenum target, GLenum attachment, GLenum renderbuffertarget, GLuint renderbuffer);
void glFramebufferTexture2D(GLenum target, GLenum attachment, GLenum textarget, GLuint texture, GLint level);
void glGenFramebuffers(GLsizei n, GLuint *framebuffers);
void glGenRenderbuffers(GLsizei n, GLuint *renderbuffers);
void glGenTextures(GLsizei n, GLuint *textures);
void glGenVertexArrays(GLsizei n, GLuint *arrays);
void glGetProgramInfoLog(GLuint program, GLsizei bufSize, GLsizei *length, GLchar *infoLog);
void glGetProgramiv(GLuint program, GLenum pname, GLint *params);
void glGetShaderInfoLog(GLuint shader, GLsizei bufSize, GLsizei *length, GLchar *infoLog);
void glGetShaderiv(GLuint shader, GLenum pname, GLint *params);
void glGetTexImage(GLenum target, GLint level, GLenum format, GLenum type, void *pixels);
void glLinkProgram(GLuint program);
void glReadBuffer(GLenum src);
void glReadPixels(GLint x, GLint y, GLsizei width, GLsizei height, GLenum format, GLenum type, void *pixels);
void glRenderbufferStorage(GLenum target, GLenum internalformat, GLsizei width, GLsizei height);
void glShaderSource(GLuint shader, GLsizei count, const GLchar *const *string, const GLint *length);
void glTexImage2D(GLenum target, GLint level, GLint internalformat, GLsizei width, GLsizei height, GLint border, GLenum format, GLenum type, const void *pixels);
void glTexParameteri(GLenum target, GLenum pname, GLint param);
void glUniform1i(GLint location, GLint v0);
void glUseProgram(GLuint program);
void glViewport(GLint x, GLint y, GLsizei width, GLsizei height);

#endif /* GL_SHIM_H */
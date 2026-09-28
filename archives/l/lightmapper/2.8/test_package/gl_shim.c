/* gl_shim.c — link-time stubs for the GL symbols referenced by lightmapper.h.
 *
 * The single-header implementation section references desktop-GL functions,
 * but the consumer test below never executes any GL path (it calls only the
 * CPU-side lmImage* API).  These stubs exist purely so the object file links;
 * they are never invoked at runtime.
 */
#include "gl_shim.h"

GLenum glCheckFramebufferStatus(GLenum target) { (void)target; return GL_FRAMEBUFFER_COMPLETE; }
GLuint glCreateProgram(void) { return 0; }
GLuint glCreateShader(GLenum type) { (void)type; return 0; }
GLint  glGetUniformLocation(GLuint program, const GLchar *name) { (void)program; (void)name; return 0; }
void glActiveTexture(GLenum texture) { (void)texture; }
void glAttachShader(GLuint program, GLuint shader) { (void)program; (void)shader; }
void glBindBuffer(GLenum target, GLuint buffer) { (void)target; (void)buffer; }
void glBindFramebuffer(GLenum target, GLuint framebuffer) { (void)target; (void)framebuffer; }
void glBindRenderbuffer(GLenum target, GLuint renderbuffer) { (void)target; (void)renderbuffer; }
void glBindTexture(GLenum target, GLuint texture) { (void)target; (void)texture; }
void glBindVertexArray(GLuint array) { (void)array; }
void glClear(GLbitfield mask) { (void)mask; }
void glClearColor(GLfloat r, GLfloat g, GLfloat b, GLfloat a) { (void)r; (void)g; (void)b; (void)a; }
void glCompileShader(GLuint shader) { (void)shader; }
void glCopyTexSubImage2D(GLenum target, GLint level, GLint xoffset, GLint yoffset, GLint x, GLint y, GLsizei width, GLsizei height) { (void)target; (void)level; (void)xoffset; (void)yoffset; (void)x; (void)y; (void)width; (void)height; }
void glDeleteFramebuffers(GLsizei n, const GLuint *framebuffers) { (void)n; (void)framebuffers; }
void glDeleteProgram(GLuint program) { (void)program; }
void glDeleteRenderbuffers(GLsizei n, const GLuint *renderbuffers) { (void)n; (void)renderbuffers; }
void glDeleteShader(GLuint shader) { (void)shader; }
void glDeleteTextures(GLsizei n, const GLuint *textures) { (void)n; (void)textures; }
void glDeleteVertexArrays(GLsizei n, const GLuint *arrays) { (void)n; (void)arrays; }
void glDisable(GLenum cap) { (void)cap; }
void glDrawArrays(GLenum mode, GLint first, GLsizei count) { (void)mode; (void)first; (void)count; }
void glEnable(GLenum cap) { (void)cap; }
void glFramebufferRenderbuffer(GLenum target, GLenum attachment, GLenum renderbuffertarget, GLuint renderbuffer) { (void)target; (void)attachment; (void)renderbuffertarget; (void)renderbuffer; }
void glFramebufferTexture2D(GLenum target, GLenum attachment, GLenum textarget, GLuint texture, GLint level) { (void)target; (void)attachment; (void)textarget; (void)texture; (void)level; }
void glGenFramebuffers(GLsizei n, GLuint *framebuffers) { if (framebuffers) { GLsizei i; for (i = 0; i < n; ++i) framebuffers[i] = 0; } }
void glGenRenderbuffers(GLsizei n, GLuint *renderbuffers) { if (renderbuffers) { GLsizei i; for (i = 0; i < n; ++i) renderbuffers[i] = 0; } }
void glGenTextures(GLsizei n, GLuint *textures) { if (textures) { GLsizei i; for (i = 0; i < n; ++i) textures[i] = 0; } }
void glGenVertexArrays(GLsizei n, GLuint *arrays) { if (arrays) { GLsizei i; for (i = 0; i < n; ++i) arrays[i] = 0; } }
void glGetProgramInfoLog(GLuint program, GLsizei bufSize, GLsizei *length, GLchar *infoLog) { (void)program; (void)bufSize; (void)length; (void)infoLog; }
void glGetProgramiv(GLuint program, GLenum pname, GLint *params) { (void)program; (void)pname; if (params) *params = GL_TRUE; }
void glGetShaderInfoLog(GLuint shader, GLsizei bufSize, GLsizei *length, GLchar *infoLog) { (void)shader; (void)bufSize; (void)length; (void)infoLog; }
void glGetShaderiv(GLuint shader, GLenum pname, GLint *params) { (void)shader; (void)pname; if (params) *params = GL_TRUE; }
void glGetTexImage(GLenum target, GLint level, GLenum format, GLenum type, void *pixels) { (void)target; (void)level; (void)format; (void)type; (void)pixels; }
void glLinkProgram(GLuint program) { (void)program; }
void glReadBuffer(GLenum src) { (void)src; }
void glReadPixels(GLint x, GLint y, GLsizei width, GLsizei height, GLenum format, GLenum type, void *pixels) { (void)x; (void)y; (void)width; (void)height; (void)format; (void)type; (void)pixels; }
void glRenderbufferStorage(GLenum target, GLenum internalformat, GLsizei width, GLsizei height) { (void)target; (void)internalformat; (void)width; (void)height; }
void glShaderSource(GLuint shader, GLsizei count, const GLchar *const *string, const GLint *length) { (void)shader; (void)count; (void)string; (void)length; }
void glTexImage2D(GLenum target, GLint level, GLint internalformat, GLsizei width, GLsizei height, GLint border, GLenum format, GLenum type, const void *pixels) { (void)target; (void)level; (void)internalformat; (void)width; (void)height; (void)border; (void)format; (void)type; (void)pixels; }
void glTexParameteri(GLenum target, GLenum pname, GLint param) { (void)target; (void)pname; (void)param; }
void glUniform1i(GLint location, GLint v0) { (void)location; (void)v0; }
void glUseProgram(GLuint program) { (void)program; }
void glViewport(GLint x, GLint y, GLsizei width, GLsizei height) { (void)x; (void)y; (void)width; (void)height; }
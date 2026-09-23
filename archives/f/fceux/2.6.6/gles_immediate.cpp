// gles_immediate.cpp — See gles_immediate.h for rationale.
//
// Implements the exact fixed-pipeline subset used by
// src/drivers/Qt/ConsoleViewerGL.cpp::paintGL():
//   glMatrixMode / glLoadIdentity / glOrtho
//   glBegin(GL_QUADS) / glTexCoord2f / glVertex2f / glEnd
// on top of GLES2 + one GLSL program. Everything else in that TU
// (glGenTextures/glBindTexture/glTexImage2D/glTexSubImage2D/glViewport/
// glClear/glEnable/glBlendFunc/glGetString/glGetIntegerv/...) is already
// core GLES2 and keeps linking against libGLESv2.
//
// Notes:
// - GL functions use C linkage (matching <GL/gl.h> declarations) so the
//   C++ caller resolves them at link time.
// - glOrtho records bounds; glEnd maps buffered pixel coords to NDC with
//   those bounds (paintGL always uses glOrtho(0, rw, 0, rh)).
// - The quad is drawn as GL_TRIANGLE_FAN (4 verts), the GLES equivalent of
//   a single GL_QUADS.
// - The program is (re)created when missing or when the GL context changed
//   (QOpenGLWidget may recreate the context; glIsProgram guards that).
// - Texture state (binding, blend func) is left to the caller, exactly as
//   with desktop GL: the shim only issues the draw.

#include <GLES2/gl2.h>

#ifndef GL_QUADS
#define GL_QUADS 0x0007
#endif
#ifndef GL_MODELVIEW
#define GL_MODELVIEW 0x1700
#endif
#ifndef GL_PROJECTION
#define GL_PROJECTION 0x1701
#endif
#ifndef GLAPIENTRY
#define GLAPIENTRY
#endif

typedef double GLdouble;

extern "C" {

static GLenum g_imm_mode = GL_MODELVIEW;
static GLdouble g_ortho_l = 0.0, g_ortho_r = 1.0;
static GLdouble g_ortho_b = 0.0, g_ortho_t = 1.0;

static int g_in_begin = 0;
static GLenum g_begin_mode = 0;
static float g_vtx[8][2];
static float g_tex[8][2];
static int g_n = 0;
static float g_pend_s = 0.0f, g_pend_t = 0.0f;
static int g_have_pend = 0;

static GLuint g_prog = 0;
static GLint g_a_pos = -1;
static GLint g_a_uv = -1;
static GLint g_u_tex = -1;

static const char *kVertSrc =
    "attribute vec2 a_pos;\n"
    "attribute vec2 a_uv;\n"
    "varying vec2 v_uv;\n"
    "void main() {\n"
    "  gl_Position = vec4(a_pos, 0.0, 1.0);\n"
    "  v_uv = a_uv;\n"
    "}\n";

static const char *kFragSrc =
    "precision mediump float;\n"
    "varying vec2 v_uv;\n"
    "uniform sampler2D u_tex;\n"
    "void main() {\n"
    "  gl_FragColor = texture2D(u_tex, v_uv);\n"
    "}\n";

static GLuint imm_compile(GLenum type, const char *src) {
  GLuint sh = glCreateShader(type);
  glShaderSource(sh, 1, &src, 0);
  glCompileShader(sh);
  return sh;
}

static void imm_ensure_program(void) {
  if (g_prog != 0 && glIsProgram(g_prog)) return;
  g_prog = 0;
  GLuint vs = imm_compile(GL_VERTEX_SHADER, kVertSrc);
  GLuint fs = imm_compile(GL_FRAGMENT_SHADER, kFragSrc);
  GLuint pr = glCreateProgram();
  glAttachShader(pr, vs);
  glAttachShader(pr, fs);
  glBindAttribLocation(pr, 0, "a_pos");
  glBindAttribLocation(pr, 1, "a_uv");
  glLinkProgram(pr);
  GLint linked = 0;
  glGetProgramiv(pr, GL_LINK_STATUS, &linked);
  if (linked != 0) {
    g_prog = pr;
    g_a_pos = 0;
    g_a_uv = 1;
    g_u_tex = glGetUniformLocation(pr, "u_tex");
  } else {
    glDeleteProgram(pr);
  }
  glDeleteShader(vs);
  glDeleteShader(fs);
}

void GLAPIENTRY glMatrixMode(GLenum mode) {
  g_imm_mode = mode;
}

void GLAPIENTRY glLoadIdentity(void) {
  // NDC mapping is derived from glOrtho bounds at glEnd time;
  // identity setup needs no action for the single-quad use.
}

void GLAPIENTRY glOrtho(GLdouble left, GLdouble right, GLdouble bottom,
                        GLdouble top, GLdouble zNear, GLdouble zFar) {
  (void)zNear;
  (void)zFar;
  g_ortho_l = left;
  g_ortho_r = right;
  g_ortho_b = bottom;
  g_ortho_t = top;
}

void GLAPIENTRY glBegin(GLenum mode) {
  g_in_begin = 1;
  g_begin_mode = mode;
  g_n = 0;
  g_have_pend = 0;
}

void GLAPIENTRY glTexCoord2f(GLfloat s, GLfloat t) {
  g_pend_s = s;
  g_pend_t = t;
  g_have_pend = 1;
}

void GLAPIENTRY glVertex2f(GLfloat x, GLfloat y) {
  if (!g_in_begin || g_n >= 8) return;
  g_vtx[g_n][0] = x;
  g_vtx[g_n][1] = y;
  if (g_have_pend) {
    g_tex[g_n][0] = g_pend_s;
    g_tex[g_n][1] = g_pend_t;
  } else {
    g_tex[g_n][0] = 0.0f;
    g_tex[g_n][1] = 0.0f;
  }
  g_n++;
}

void GLAPIENTRY glEnd(void) {
  if (!g_in_begin) return;
  g_in_begin = 0;
  if (g_n < 3) {
    g_n = 0;
    return;
  }
  imm_ensure_program();
  if (g_prog == 0) {
    g_n = 0;
    return;
  }
  double w = g_ortho_r - g_ortho_l;
  double h = g_ortho_t - g_ortho_b;
  if (w == 0.0) w = 1.0;
  if (h == 0.0) h = 1.0;
  float ndc[8][2];
  for (int i = 0; i < g_n; i++) {
    ndc[i][0] = (float)(((g_vtx[i][0] - g_ortho_l) / w) * 2.0 - 1.0);
    ndc[i][1] = (float)(((g_vtx[i][1] - g_ortho_b) / h) * 2.0 - 1.0);
  }
  glUseProgram(g_prog);
  glActiveTexture(GL_TEXTURE0);
  if (g_u_tex >= 0) glUniform1i(g_u_tex, 0);
  glEnableVertexAttribArray((GLuint)g_a_pos);
  glEnableVertexAttribArray((GLuint)g_a_uv);
  glVertexAttribPointer((GLuint)g_a_pos, 2, GL_FLOAT, GL_FALSE, 0, ndc);
  glVertexAttribPointer((GLuint)g_a_uv, 2, GL_FLOAT, GL_FALSE, 0, g_tex);
  // Single GL_QUADS (4 verts) -> TRIANGLE_FAN; anything else draws as fan.
  glDrawArrays(GL_TRIANGLE_FAN, 0, g_n);
  glDisableVertexAttribArray((GLuint)g_a_pos);
  glDisableVertexAttribArray((GLuint)g_a_uv);
  g_n = 0;
}

} // extern "C"

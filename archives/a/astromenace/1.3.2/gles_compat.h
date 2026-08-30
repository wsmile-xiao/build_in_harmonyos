// gles_compat.h — GLES2 compatibility header for AstroMenace 1.3.2
// Declares the desktop GL fixed-pipeline API surface used by the game,
// backed by a GLES2 implementation in gles_compat.cpp (fixed-function
// emulation via a GLSL shader, CPU matrix stacks, vertex attribute arrays,
// and tracked lighting/state).
//
// Part of the OHOS GLES rendering-port adaptation. Same license as
// AstroMenace (GPLv3 / CC-BY-NC-SA 3.0).
#ifndef GLES_COMPAT_H
#define GLES_COMPAT_H

#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>

#ifdef __cplusplus
extern "C" {
#endif

// ===== Desktop GL types not in GLES2 =====
typedef double GLdouble;
typedef double GLclampd;
typedef float GLclampf;
#ifndef GLAPIENTRY
#define GLAPIENTRY
#endif

// ===== Fixed-pipeline / desktop GL constants absent from GLES2 =====
#define GL_NEAREST_MIPMAP_NEAREST  0x2700
#define GL_LINEAR_MIPMAP_NEAREST   0x2701
#define GL_NEAREST_MIPMAP_LINEAR   0x2702
#define GL_LINEAR_MIPMAP_LINEAR    0x2703
#define GL_CLAMP                   0x2900  // GLES2: use GL_CLAMP_TO_EDGE
#define GL_BGR                     0x80E0
#define GL_BGRA_EXT                0x80E1

// Client state enums
#define GL_VERTEX_ARRAY            0x8074
#define GL_NORMAL_ARRAY            0x8075
#define GL_COLOR_ARRAY             0x8076
#define GL_TEXTURE_COORD_ARRAY     0x8078
#define GL_INDEX_ARRAY             0x8077
#define GL_EDGE_FLAG_ARRAY         0x8079

// Matrix mode enums
#define GL_MODELVIEW               0x1700
#define GL_PROJECTION              0x1701
#define GL_TEXTURE                 0x1702
#define GL_COLOR                   0x1800

// Fixed-pipeline / lighting enums
#define GL_LIGHTING                0x0B50
#define GL_LIGHT0                  0x4000
#define GL_LIGHT1                  0x4001
#define GL_LIGHT2                  0x4002
#define GL_LIGHT3                  0x4003
#define GL_LIGHT4                  0x4004
#define GL_LIGHT5                  0x4005
#define GL_LIGHT6                  0x4006
#define GL_LIGHT7                  0x4007
#define GL_POSITION                0x1203
#define GL_AMBIENT                 0x1200
#define GL_DIFFUSE                 0x1201
#define GL_SPECULAR                0x1202
#define GL_SPOT_DIRECTION          0x1204
#define GL_SPOT_EXPONENT           0x1205
#define GL_SPOT_CUTOFF             0x1206
#define GL_CONSTANT_ATTENUATION    0x1207
#define GL_LINEAR_ATTENUATION      0x1208
#define GL_QUADRATIC_ATTENUATION   0x1209
#define GL_EMISSION                0x1600
#define GL_SHININESS               0x1601
#define GL_AMBIENT_AND_DIFFUSE     0x1602
#define GL_COLOR_INDEXES           0x1603
#define GL_MODELVIEW_MATRIX        0x0BA6
#define GL_PROJECTION_MATRIX       0x0BA7
#define GL_MODELVIEW_STACK_DEPTH   0x0BA3
#define GL_PROJECTION_STACK_DEPTH  0x0BA4
#define GL_MAX_MODELVIEW_STACK_DEPTH  0x0D36
#define GL_MAX_PROJECTION_STACK_DEPTH 0x0D30
#define GL_MAX_ATTRIB_STACK_DEPTH  0x0D35
#define GL_LIGHT_MODEL_AMBIENT     0x0B53
#define GL_LIGHT_MODEL_TWO_SIDE    0x0B52
#define GL_MAX_LIGHTS              0x0D31
#define GL_FLAT                    0x1D00
#define GL_SMOOTH                  0x1D01
#define GL_POINT_SMOOTH            0x0B10
#define GL_LINE_SMOOTH             0x0B20
#define GL_POLYGON_SMOOTH          0x0B41
#define GL_POINT_SMOOTH_HINT       0x0C51
#define GL_LINE_SMOOTH_HINT        0x0C52
#define GL_POLYGON_SMOOTH_HINT     0x0C53
#define GL_PERSPECTIVE_CORRECTION_HINT 0x0C50
#define GL_POINT_SIZE              0x0B11
#define GL_LINE_WIDTH              0x0B21
#define GL_CULL_FACE               0x0B44
#define GL_FRONT                   0x0404
#define GL_BACK                    0x0405
#define GL_FRONT_AND_BACK          0x0408
#define GL_NORMALIZE               0x0BA1
#define GL_RESCALE_NORMAL          0x803A
#define GL_TEXTURE_2D              0x0DE1
#define GL_TEXTURE_GEN_S           0x0C60
#define GL_TEXTURE_GEN_T           0x0C61
#define GL_TEXTURE_GEN_R           0x0C62
#define GL_TEXTURE_GEN_Q           0x0C63
#define GL_TEXTURE_GEN_MODE        0x2500
#define GL_OBJECT_PLANE            0x2501
#define GL_EYE_PLANE               0x2502
#define GL_ALPHA_TEST              0x0BC0
#define GL_ALPHA_TEST_FUNC         0x0BC1
#define GL_ALPHA_TEST_REF          0x0BC2
#define GL_COLOR_MATERIAL          0x0B57
#define GL_COLOR_MATERIAL_FACE     0x0B55
#define GL_COLOR_MATERIAL_PARAMETER 0x0B56
// TexEnv combine / blend constants (desktop)
#define GL_ADD                    0x0104
#define GL_ADD_SIGNED             0x8574
#define GL_SUBTRACT               0x84E7
#define GL_INTERPOLATE            0x8575
#define GL_RGB_SCALE              0x8573
#define GL_ALPHA_SCALE            0x0D1C
#define GL_ONE_MINUS_SRC_ALPHA    0x0303
#define GL_SRC_ALPHA              0x0302
#define GL_DST_ALPHA              0x0304
#define GL_ONE_MINUS_DST_ALPHA    0x0305
// GL_FILL / polygon mode
#define GL_POINT                  0x1B00
#define GL_LINE                   0x1B01
#define GL_FILL                   0x1B02
// GLES2-practical sized format constants (GLES2 uses GL_RGBA etc.)
#define GL_RGBA8                 0x8058
#define GL_RGB8                  0x8051
#define GL_RGBA4                 0x8056
#define GL_RGB5_A1               0x8057
#define GL_DEPTH_COMPONENT24     0x81A6
#define GL_DEPTH_COMPONENT16     0x81A5
#define GL_STENCIL_INDEX8        0x8D48
#define GL_DEPTH24_STENCIL8      0x88F0
#define GL_QUADS                   0x0007
#define GL_POLYGON                 0x0009
#define GL_TEXTURE_PRIORITY        0x8066
#define GL_INTENSITY               0x8049
#define GL_TEXTURE_ENV             0x2300
#define GL_TEXTURE_ENV_MODE        0x2200
#define GL_MODULATE                0x2100
#define GL_REPLACE                 0x1E01
#define GL_DECAL                   0x2101
#define GL_NEVER                   0x0200
#define GL_LESS                    0x0201
#define GL_EQUAL                   0x0202
#define GL_LEQUAL                  0x0203
#define GL_GREATER                 0x0204
#define GL_NOTEQUAL                0x0205
#define GL_GEQUAL                  0x0206
#define GL_ALWAYS                  0x0207
#define GL_AUTO_NORMAL             0x0D80
#define GL_MAP1_COLOR_4            0x0D90
#define GL_MAP1_INDEX              0x0D91
#define GL_MAP1_NORMAL             0x0D92
#define GL_MAP1_TEXTURE_COORD_1    0x0D93
#define GL_MAP1_TEXTURE_COORD_2    0x0D94
#define GL_MAP1_TEXTURE_COORD_3    0x0D95
#define GL_MAP1_TEXTURE_COORD_4    0x0D96
#define GL_MAP1_VERTEX_3           0x0D97
#define GL_MAP1_VERTEX_4           0x0D98
#define GL_MAP2_COLOR_4            0x0DB0
#define GL_MAP2_INDEX              0x0DB1
#define GL_MAP2_NORMAL             0x0DB2
#define GL_MAP2_TEXTURE_COORD_1    0x0DB3
#define GL_MAP2_TEXTURE_COORD_2    0x0DB4
#define GL_MAP2_TEXTURE_COORD_3    0x0DB5
#define GL_MAP2_TEXTURE_COORD_4    0x0DB6
#define GL_MAP2_VERTEX_3           0x0DB7
#define GL_MAP2_VERTEX_4           0x0DB8
#define GL_COLOR_MATERIAL          0x0B57

// PushAttrib bits
#define GL_ACCUM_BUFFER_BIT        0x00000200
#define GL_COLOR_BUFFER_BIT        0x00004000
#define GL_CURRENT_BIT             0x00000001
#define GL_DEPTH_BUFFER_BIT        0x00000100
#define GL_ENABLE_BIT              0x00002000
#define GL_EVAL_BIT                0x00010000
#define GL_FOG_BIT                 0x00000080
#define GL_HINT_BIT                0x00008000
#define GL_LIGHTING_BIT            0x00000040
#define GL_LINE_BIT                0x00000004
#define GL_LIST_BIT                0x00020000
#define GL_PIXEL_MODE_BIT          0x00000020
#define GL_POINT_BIT               0x00000002
#define GL_POLYGON_BIT             0x00000008
#define GL_POLYGON_STIPPLE_BIT     0x00000010
#define GL_SCISSOR_BIT             0x00080000
#define GL_STENCIL_BUFFER_BIT      0x00000400
#define GL_TEXTURE_BIT             0x00040000
#define GL_TRANSFORM_BIT           0x00001000
#define GL_VIEWPORT_BIT            0x00000800
#define GL_ALL_ATTRIB_BITS         0x000FFFFF

// ===== Desktop GL fixed-pipeline function declarations =====

// --- Matrix stack operations (desktop GL, no GLES2 equivalent) ---
void glMatrixMode(GLenum mode);
void glLoadIdentity(void);
void glPushMatrix(void);
void glPopMatrix(void);
void glOrtho(GLdouble left, GLdouble right, GLdouble bottom, GLdouble top,
             GLdouble zNear, GLdouble zFar);
void glRotatef(GLfloat angle, GLfloat x, GLfloat y, GLfloat z);
void glMultMatrixd(const GLdouble* m);
void glMultMatrixf(const GLfloat* m);
void glTranslated(GLdouble x, GLdouble y, GLdouble z);
void glTranslatef(GLfloat x, GLfloat y, GLfloat z);
void glScalef(GLfloat x, GLfloat y, GLfloat z);
void glLoadMatrixf(const GLfloat* m);
void glFrustum(GLdouble left, GLdouble right, GLdouble bottom, GLdouble top,
               GLdouble zNear, GLdouble zFar);
void glGetFloatv(GLenum pname, GLfloat* params);

// --- Client-side vertex array state ---
void glEnableClientState(GLenum cap);
void glDisableClientState(GLenum cap);
void glVertexPointer(GLint size, GLenum type, GLsizei stride, const void* ptr);
void glNormalPointer(GLenum type, GLsizei stride, const void* ptr);
void glColorPointer(GLint size, GLenum type, GLsizei stride, const void* ptr);
void glTexCoordPointer(GLint size, GLenum type, GLsizei stride, const void* ptr);

// --- State management ---
void glPushAttrib(GLbitfield mask);
void glPopAttrib(void);

// --- Fixed-pipeline lighting ---
void glEnable(GLenum cap);
void glDisable(GLenum cap);
void glLightf(GLenum light, GLenum pname, GLfloat param);
void glLightfv(GLenum light, GLenum pname, const GLfloat* params);
void glGetLightfv(GLenum light, GLenum pname, GLfloat* params);
void glMaterialfv(GLenum face, GLenum pname, const GLfloat* params);
void glGetMaterialfv(GLenum face, GLenum pname, GLfloat* params);
void glColorMaterial(GLenum face, GLenum mode);
void glLightModelfv(GLenum pname, const GLfloat* params);

// --- Other desktop GL functions ---
void glAlphaFunc(GLenum func, GLclampf ref);
void glPrioritizeTextures(GLsizei n, const GLuint* textures, const GLclampf* priorities);
void glTexEnvi(GLenum target, GLenum pname, GLint param);
void glTexEnvf(GLenum target, GLenum pname, GLfloat param);
void glPolygonMode(GLenum face, GLenum mode);
void glShadeModel(GLenum mode);
void glClearDepth(GLclampd depth);
void glDepthRange(GLclampd n, GLclampd f);
void glColor4f(GLfloat r, GLfloat g, GLfloat b, GLfloat a);
void glGetTexImage(GLenum target, GLint level, GLenum format, GLenum type, void* pixels);

// --- GLU replacements (implemented with matrix math) ---
void gluLookAt(GLdouble eyeX, GLdouble eyeY, GLdouble eyeZ,
               GLdouble centerX, GLdouble centerY, GLdouble centerZ,
               GLdouble upX, GLdouble upY, GLdouble upZ);
void gluPerspective(GLdouble fovy, GLdouble aspect, GLdouble zNear, GLdouble zFar);
const GLubyte* gluErrorString(GLenum error);
int gluBuild2DMipmaps(GLenum target, GLint components, GLsizei width,
                      GLsizei height, GLenum format, GLenum type, const void* data);

// ===== gles_compat runtime helpers =====
void gles_init(void);
void gles_apply_matrices(void);
void gles_apply_vertex_arrays(void);
void gles_apply_lighting(void);
void gles_apply_state(void);

// ===== Intercept draw calls to apply state before each draw =====
void gles_glDrawElements(GLenum mode, GLsizei count, GLenum type, const void* indices);
void gles_glDrawArrays(GLenum mode, GLint first, GLsizei count);

// Intercept glTexImage2D to track texture dimensions used by glGetTexImage
// (GLES2 lacks glGetTexImage and glGetTexLevelParameteriv).
void gles_glTexImage2D(GLenum target, GLint level, GLint internalformat,
                       GLsizei width, GLsizei height, GLint border,
                       GLenum format, GLenum type, const void* pixels);

// In the implementation .cpp, define GLES_COMPAT_IMPLEMENTATION before
// including this header to suppress these macros and access the real
// GLES2 function symbols directly.
#ifndef GLES_COMPAT_IMPLEMENTATION
#define glDrawElements gles_glDrawElements
#define glDrawArrays gles_glDrawArrays
#define glTexImage2D gles_glTexImage2D
#endif

#ifdef __cplusplus
}
#endif

#endif // GLES_COMPAT_H
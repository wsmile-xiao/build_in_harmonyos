// gles_compat.cpp — GLES2 fixed-pipeline emulation implementation
// See gles_compat.h for declarations.
// Compiles as a single translation unit; state is file-static.

// Define BEFORE including the header to suppress the draw-call macro
// redirects, so we can reference the real GLES2 function symbols directly.
#define GLES_COMPAT_IMPLEMENTATION

#include "gles_compat.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <EGL/egl.h>

// ===== Internal state =====

#define GLES_MAX_MATRIX_STACK   32
#define GLES_MAX_ATTRIB_STACK   16
#define GLES_MAX_LIGHTS          8
#define GLES_MATRIX_SIZE        16

// Texture dimension registry (GLES2 has no glGetTexLevelParameteriv; we
// track sizes from every glTexImage2D so glGetTexImage can FBO-readback).
#define GLES_MAX_TRACKED_TEXTURES 512
static GLuint    g_tracked_tex[GLES_MAX_TRACKED_TEXTURES];
static GLsizei   g_tracked_tex_w[GLES_MAX_TRACKED_TEXTURES];
static GLsizei   g_tracked_tex_h[GLES_MAX_TRACKED_TEXTURES];
static int       g_tracked_tex_count = 0;

// Current matrix mode
static GLenum g_matrix_mode = GL_MODELVIEW;

// Matrix stacks
static float g_modelview_stack[GLES_MAX_MATRIX_STACK][GLES_MATRIX_SIZE];
static int   g_modelview_depth = 0;
static float g_projection_stack[GLES_MAX_MATRIX_STACK][GLES_MATRIX_SIZE];
static int   g_projection_depth = 0;
static float g_texture_stack[GLES_MAX_MATRIX_STACK][GLES_MATRIX_SIZE];
static int   g_texture_depth = 0;

// Current matrix pointer
static float* g_current_matrix = g_modelview_stack[0];

// Vertex array state
static GLboolean g_vertex_array_enabled = GL_FALSE;
static GLboolean g_normal_array_enabled = GL_FALSE;
static GLboolean g_color_array_enabled = GL_FALSE;
static GLboolean g_texcoord_array_enabled = GL_FALSE;

static GLint     g_vertex_size = 0;
static GLenum    g_vertex_type = GL_FLOAT;
static GLsizei   g_vertex_stride = 0;
static const void* g_vertex_pointer = NULL;

static GLint     g_normal_size = 3;
static GLenum    g_normal_type = GL_FLOAT;
static GLsizei   g_normal_stride = 0;
static const void* g_normal_pointer = NULL;

static GLint     g_color_size = 0;
static GLenum    g_color_type = GL_FLOAT;
static GLsizei   g_color_stride = 0;
static const void* g_color_pointer = NULL;

static GLint     g_texcoord_size = 0;
static GLenum    g_texcoord_type = GL_FLOAT;
static GLsizei   g_texcoord_stride = 0;
static const void* g_texcoord_pointer = NULL;

// Attribute locations in the fixed-function shader
static const GLint ATTR_VERTEX = 0;
static const GLint ATTR_NORMAL = 1;
static const GLint ATTR_COLOR = 2;
static const GLint ATTR_TEXCOORD = 3;

// Current color
static float g_current_color[4] = {1.0f, 1.0f, 1.0f, 1.0f};

// Lighting state
static GLboolean g_lighting_enabled = GL_FALSE;
static GLboolean g_light_enabled[GLES_MAX_LIGHTS] = {GL_FALSE};
static float g_light_ambient[GLES_MAX_LIGHTS][4] = {{0.0f, 0.0f, 0.0f, 1.0f}};
static float g_light_diffuse[GLES_MAX_LIGHTS][4] = {{1.0f, 1.0f, 1.0f, 1.0f}};
static float g_light_specular[GLES_MAX_LIGHTS][4] = {{1.0f, 1.0f, 1.0f, 1.0f}};
static float g_light_position[GLES_MAX_LIGHTS][4] = {{0.0f, 0.0f, 1.0f, 0.0f}};
static float g_light_spot_direction[GLES_MAX_LIGHTS][3] = {{0.0f, 0.0f, -1.0f}};
static float g_light_spot_exponent[GLES_MAX_LIGHTS] = {0.0f};
static float g_light_spot_cutoff[GLES_MAX_LIGHTS] = {180.0f};
static float g_light_const_atten[GLES_MAX_LIGHTS] = {1.0f};
static float g_light_linear_atten[GLES_MAX_LIGHTS] = {0.0f};
static float g_light_quad_atten[GLES_MAX_LIGHTS] = {0.0f};

// Material state
static float g_material_ambient[4] = {0.2f, 0.2f, 0.2f, 1.0f};
static float g_material_diffuse[4] = {0.8f, 0.8f, 0.8f, 1.0f};
static float g_material_specular[4] = {0.0f, 0.0f, 0.0f, 1.0f};
static float g_material_emission[4] = {0.0f, 0.0f, 0.0f, 1.0f};
static float g_material_shininess = 0.0f;
static GLenum g_color_material_face = GL_FRONT_AND_BACK;
static GLenum g_color_material_mode = GL_AMBIENT_AND_DIFFUSE;
static GLboolean g_color_material_enabled = GL_FALSE;

// Light model
static float g_light_model_ambient[4] = {0.2f, 0.2f, 0.2f, 1.0f};
static GLboolean g_light_model_two_side = GL_FALSE;

// Alpha test state
static GLenum  g_alpha_test_func = GL_ALWAYS;
static GLfloat g_alpha_test_ref = 0.0f;

// Texture environment
static GLenum g_tex_env_mode = GL_MODULATE;

// ===== Matrix utility functions =====

static void mat_identity(float* m) {
    int i;
    for (i = 0; i < 16; i++) m[i] = 0.0f;
    m[0] = m[5] = m[10] = m[15] = 1.0f;
}

static void mat_multiply(float* dst, const float* a, const float* b) {
    float res[16];
    int i, j, k;
    for (i = 0; i < 4; i++) {
        for (j = 0; j < 4; j++) {
            float sum = 0.0f;
            for (k = 0; k < 4; k++)
                sum += a[i + k*4] * b[k + j*4];
            res[i + j*4] = sum;
        }
    }
    for (i = 0; i < 16; i++) dst[i] = res[i];
}

static void mat_ortho(float* m, float l, float r, float b, float t, float n, float f) {
    int i;
    for (i = 0; i < 16; i++) m[i] = 0.0f;
    m[0] = 2.0f / (r - l);
    m[5] = 2.0f / (t - b);
    m[10] = -2.0f / (f - n);
    m[12] = -(r + l) / (r - l);
    m[13] = -(t + b) / (t - b);
    m[14] = -(f + n) / (f - n);
    m[15] = 1.0f;
}

static void mat_rotate(float* m, float angle, float x, float y, float z) {
    float rad = angle * 3.1415926535f / 180.0f;
    float c = cosf(rad), s = sinf(rad);
    float len = sqrtf(x*x + y*y + z*z);
    if (len < 1e-6f) return;
    x /= len; y /= len; z /= len;
    float u[3] = {x, y, z};
    float r[16];
    int i;
    for (i = 0; i < 16; i++) r[i] = 0.0f;
    r[0] = c + u[0]*u[0]*(1-c);
    r[1] = u[1]*u[0]*(1-c) + u[2]*s;
    r[2] = u[2]*u[0]*(1-c) - u[1]*s;
    r[4] = u[0]*u[1]*(1-c) - u[2]*s;
    r[5] = c + u[1]*u[1]*(1-c);
    r[6] = u[2]*u[1]*(1-c) + u[0]*s;
    r[8] = u[0]*u[2]*(1-c) + u[1]*s;
    r[9] = u[1]*u[2]*(1-c) - u[0]*s;
    r[10] = c + u[2]*u[2]*(1-c);
    r[15] = 1.0f;
    mat_multiply(m, m, r);
}

static void mat_translate(float* m, float x, float y, float z) {
    float t[16];
    mat_identity(t);
    t[12] = x; t[13] = y; t[14] = z;
    mat_multiply(m, m, t);
}

static void mat_scale(float* m, float x, float y, float z) {
    float s[16];
    mat_identity(s);
    s[0] = x; s[5] = y; s[10] = z;
    mat_multiply(m, m, s);
}

// ===== Attribute stack =====

typedef struct {
    GLboolean vertex_array_enabled;
    GLboolean normal_array_enabled;
    GLboolean color_array_enabled;
    GLboolean texcoord_array_enabled;
    GLboolean lighting_enabled;
    GLboolean color_material_enabled;
    GLboolean blend_enabled;
    GLboolean depth_test_enabled;
    GLboolean cull_face_enabled;
    GLboolean texture_2d_enabled;
    GLboolean alpha_test_enabled;
    GLenum    alpha_test_func;
    GLfloat   alpha_test_ref;
    GLint viewport[4];
} AttribState;

static AttribState g_attrib_stack[GLES_MAX_ATTRIB_STACK];
static int g_attrib_depth = 0;

// ===== Shader program =====

static GLuint g_ff_program = 0;

// Uniform locations
static GLint g_unif_mvp = -1;
static GLint g_unif_mv = -1;
static GLint g_unif_normal_matrix = -1;
static GLint g_unif_tex0 = -1;
static GLint g_unif_lighting_enabled = -1;
static GLint g_unif_current_color = -1;
static GLint g_unif_light_model_ambient = -1;
static GLint g_unif_material_ambient = -1;
static GLint g_unif_material_diffuse = -1;
static GLint g_unif_material_specular = -1;
static GLint g_unif_material_emission = -1;
static GLint g_unif_material_shininess = -1;
static GLint g_unif_light_positions[GLES_MAX_LIGHTS];
static GLint g_unif_light_ambients[GLES_MAX_LIGHTS];
static GLint g_unif_light_diffuses[GLES_MAX_LIGHTS];
static GLint g_unif_light_speculars[GLES_MAX_LIGHTS];
static GLint g_unif_light_enables[GLES_MAX_LIGHTS];
static GLint g_unif_has_texcoord = -1;
static GLint g_unif_has_color = -1;
static GLint g_unif_alpha_test_enabled = -1;
static GLint g_unif_alpha_test_func = -1;
static GLint g_unif_alpha_test_ref = -1;
static GLint g_unif_tex_env_mode = -1;

// ===== Real GLES2 function pointers (saved to avoid macro recursion) =====
// We capture the real GLES2 functions at init time.
static void (*g_real_glDrawElements)(GLenum, GLsizei, GLenum, const void*) = NULL;
static void (*g_real_glDrawArrays)(GLenum, GLint, GLsizei) = NULL;

// ===== Vertex shader: fixed-function lighting emulation =====
static const char* g_vert_src =
    "attribute vec4 a_position;\n"
    "attribute vec3 a_normal;\n"
    "attribute vec4 a_color;\n"
    "attribute vec2 a_texcoord;\n"
    "uniform mat4 u_mvp;\n"
    "uniform mat4 u_mv;\n"
    "uniform mat3 u_normal_matrix;\n"
    "uniform int u_lighting_enabled;\n"
    "uniform vec4 u_current_color;\n"
    "uniform vec4 u_light_model_ambient;\n"
    "uniform vec4 u_material_ambient;\n"
    "uniform vec4 u_material_diffuse;\n"
    "uniform vec4 u_material_specular;\n"
    "uniform vec4 u_material_emission;\n"
    "uniform float u_material_shininess;\n"
    "uniform vec4 u_light_positions[8];\n"
    "uniform vec4 u_light_ambients[8];\n"
    "uniform vec4 u_light_diffuses[8];\n"
    "uniform vec4 u_light_speculars[8];\n"
    "uniform int u_light_enables[8];\n"
    "uniform int u_has_texcoord;\n"
    "uniform int u_has_color;\n"
    "varying vec4 v_color;\n"
    "varying vec2 v_texcoord;\n"
    "void main() {\n"
    "    gl_Position = u_mvp * a_position;\n"
    "    vec4 eye_vertex = u_mv * a_position;\n"
    "    v_texcoord = a_texcoord;\n"
    "    vec4 color;\n"
    "    if (u_has_color != 0) color = a_color;\n"
    "    else if (u_lighting_enabled == 0) color = u_current_color;\n"
    "    else color = u_material_diffuse;\n"
    "    if (u_lighting_enabled == 0) { v_color = color; return; }\n"
    "    vec3 normal = normalize(u_normal_matrix * a_normal);\n"
    "    vec4 accum = u_light_model_ambient * u_material_ambient + u_material_emission;\n"
    "    for (int i = 0; i < 8; i++) {\n"
    "        if (u_light_enables[i] == 0) continue;\n"
    "        vec3 light_dir;\n"
    "        vec4 pos = u_light_positions[i];\n"
    "        if (pos.w == 0.0) light_dir = normalize(pos.xyz);\n"
    "        else { light_dir = normalize(pos.xyz / pos.w - eye_vertex.xyz / eye_vertex.w); }\n"
    "        float ndotl = max(dot(normal, light_dir), 0.0);\n"
    "        accum += u_light_ambients[i] * u_material_ambient;\n"
    "        accum += ndotl * u_light_diffuses[i] * color;\n"
    "        vec3 view_dir = vec3(0.0, 0.0, 1.0);\n"
    "        vec3 half_vec = normalize(light_dir + view_dir);\n"
    "        float ndoth = max(dot(normal, half_vec), 0.0);\n"
    "        float spec = pow(ndoth, u_material_shininess);\n"
    "        if (ndotl <= 0.0) spec = 0.0;\n"
    "        accum += spec * u_light_speculars[i] * u_material_specular;\n"
    "    }\n"
    "    v_color = clamp(accum, 0.0, 1.0);\n"
    "    v_color.a = color.a;\n"
    "}\n";

// ===== Fragment shader: texture + alpha test + tex env =====
static const char* g_frag_src =
    "precision mediump float;\n"
    "varying vec4 v_color;\n"
    "varying vec2 v_texcoord;\n"
    "uniform sampler2D u_tex0;\n"
    "uniform int u_has_texcoord;\n"
    "uniform int u_alpha_test_enabled;\n"
    "uniform int u_alpha_test_func;\n"
    "uniform float u_alpha_test_ref;\n"
    "uniform int u_tex_env_mode;\n"
    "void main() {\n"
    "    vec4 color = v_color;\n"
    "    if (u_has_texcoord != 0) {\n"
    "        vec4 texel = texture2D(u_tex0, v_texcoord);\n"
    "        if (u_tex_env_mode == 1) color = texel;\n"         // GL_REPLACE
    "        else if (u_tex_env_mode == 2) color = color * texel;\n"    // GL_MODULATE
    "        else color = color * texel;\n"                     // default modulate
    "    }\n"
    "    if (u_alpha_test_enabled != 0) {\n"
    "        float a = color.a;\n"
    "        bool pass = false;\n"
    "        int func = u_alpha_test_func;\n"
    "        float ref = u_alpha_test_ref;\n"
    "        if (func == 0) pass = false;\n"                    // GL_NEVER
    "        else if (func == 1) pass = a < ref;\n"             // GL_LESS
    "        else if (func == 2) pass = abs(a - ref) < 0.005;\n" // GL_EQUAL
    "        else if (func == 3) pass = a <= ref;\n"            // GL_LEQUAL
    "        else if (func == 4) pass = a > ref;\n"             // GL_GREATER
    "        else if (func == 5) pass = abs(a - ref) >= 0.005;\n" // GL_NOTEQUAL
    "        else if (func == 6) pass = a >= ref;\n"            // GL_GEQUAL
    "        else if (func == 7) pass = true;\n"                // GL_ALWAYS
    "        if (!pass) discard;\n"
    "    }\n"
    "    gl_FragColor = color;\n"
    "}\n";

// ===== GLES2 function pointer wrappers =====
// We define inline wrappers that call apply_state then the real GLES2 functions.
// To avoid macro recursion, the real pointers are saved in gles_init.
// These are non-static because gles_compat.h declares them as extern and
// the macro redirects glDrawElements → gles_glDrawElements in all TUs.

void gles_glDrawElements(GLenum mode, GLsizei count, GLenum type, const void* indices) {
    gles_apply_state();
    if (g_real_glDrawElements == NULL) return; // fail safely if real GLES2 fn not captured
    g_real_glDrawElements(mode, count, type, indices);
}

void gles_glDrawArrays(GLenum mode, GLint first, GLsizei count) {
    gles_apply_state();
    if (g_real_glDrawArrays == NULL) return; // fail safely if real GLES2 fn not captured
    g_real_glDrawArrays(mode, first, count);
}

// glTexImage2D wrapper: records (target, level-0 size) so glGetTexImage can
// read back the texture via an FBO, then forwards to the real GLES2 call.
void gles_glTexImage2D(GLenum target, GLint level, GLint internalformat,
                       GLsizei width, GLsizei height, GLint border,
                       GLenum format, GLenum type, const void* pixels) {
    if (target == GL_TEXTURE_2D && level == 0) {
        GLint bound = 0;
        glGetIntegerv(GL_TEXTURE_BINDING_2D, &bound);
        int i;
        int found = -1;
        for (i = 0; i < g_tracked_tex_count; i++) {
            if (g_tracked_tex[i] == (GLuint)bound) { found = i; break; }
        }
        if (found < 0 && g_tracked_tex_count < GLES_MAX_TRACKED_TEXTURES) {
            found = g_tracked_tex_count++;
            g_tracked_tex[found] = (GLuint)bound;
        }
        if (found >= 0) {
            g_tracked_tex_w[found] = width;
            g_tracked_tex_h[found] = height;
        }
    }
    glTexImage2D(target, level, internalformat, width, height, border, format, type, pixels);
}

// ===== Public API implementations =====

// --- Matrix operations ---

void glMatrixMode(GLenum mode) {
    g_matrix_mode = mode;
    switch (mode) {
        case GL_MODELVIEW:  g_current_matrix = g_modelview_stack[g_modelview_depth]; break;
        case GL_PROJECTION: g_current_matrix = g_projection_stack[g_projection_depth]; break;
        case GL_TEXTURE:    g_current_matrix = g_texture_stack[g_texture_depth]; break;
        default: break;
    }
}

void glLoadIdentity(void) {
    mat_identity(g_current_matrix);
}

void glPushMatrix(void) {
    float* src = g_current_matrix;
    int new_depth;
    switch (g_matrix_mode) {
        case GL_MODELVIEW:
            new_depth = g_modelview_depth + 1;
            if (new_depth < GLES_MAX_MATRIX_STACK) {
                memcpy(g_modelview_stack[new_depth], src, sizeof(float) * 16);
                g_modelview_depth = new_depth;
                g_current_matrix = g_modelview_stack[new_depth];
            }
            break;
        case GL_PROJECTION:
            new_depth = g_projection_depth + 1;
            if (new_depth < GLES_MAX_MATRIX_STACK) {
                memcpy(g_projection_stack[new_depth], src, sizeof(float) * 16);
                g_projection_depth = new_depth;
                g_current_matrix = g_projection_stack[new_depth];
            }
            break;
        case GL_TEXTURE:
            new_depth = g_texture_depth + 1;
            if (new_depth < GLES_MAX_MATRIX_STACK) {
                memcpy(g_texture_stack[new_depth], src, sizeof(float) * 16);
                g_texture_depth = new_depth;
                g_current_matrix = g_texture_stack[new_depth];
            }
            break;
        default: break;
    }
}

void glPopMatrix(void) {
    switch (g_matrix_mode) {
        case GL_MODELVIEW:
            if (g_modelview_depth > 0) {
                g_modelview_depth--;
                g_current_matrix = g_modelview_stack[g_modelview_depth];
            }
            break;
        case GL_PROJECTION:
            if (g_projection_depth > 0) {
                g_projection_depth--;
                g_current_matrix = g_projection_stack[g_projection_depth];
            }
            break;
        case GL_TEXTURE:
            if (g_texture_depth > 0) {
                g_texture_depth--;
                g_current_matrix = g_texture_stack[g_texture_depth];
            }
            break;
        default: break;
    }
}

void glOrtho(GLdouble left, GLdouble right, GLdouble bottom, GLdouble top,
             GLdouble zNear, GLdouble zFar) {
    float ortho[16];
    mat_ortho(ortho, (float)left, (float)right, (float)bottom,
              (float)top, (float)zNear, (float)zFar);
    mat_multiply(g_current_matrix, g_current_matrix, ortho);
}

void glRotatef(GLfloat angle, GLfloat x, GLfloat y, GLfloat z) {
    mat_rotate(g_current_matrix, angle, x, y, z);
}

void glMultMatrixd(const GLdouble* m) {
    float mf[16];
    int i;
    for (i = 0; i < 16; i++) mf[i] = (float)m[i];
    mat_multiply(g_current_matrix, g_current_matrix, mf);
}

void glMultMatrixf(const GLfloat* m) {
    mat_multiply(g_current_matrix, g_current_matrix, m);
}

void glTranslated(GLdouble x, GLdouble y, GLdouble z) {
    mat_translate(g_current_matrix, (float)x, (float)y, (float)z);
}

void glTranslatef(GLfloat x, GLfloat y, GLfloat z) {
    mat_translate(g_current_matrix, x, y, z);
}

void glScalef(GLfloat x, GLfloat y, GLfloat z) {
    mat_scale(g_current_matrix, x, y, z);
}

void glLoadMatrixf(const GLfloat* m) {
    memcpy(g_current_matrix, m, sizeof(float) * 16);
}

void glFrustum(GLdouble left, GLdouble right, GLdouble bottom, GLdouble top,
               GLdouble zNear, GLdouble zFar) {
    float frustum[16];
    int i;
    for (i = 0; i < 16; i++) frustum[i] = 0.0f;
    frustum[0] = 2.0f * (float)zNear / (float)(right - left);
    frustum[5] = 2.0f * (float)zNear / (float)(top - bottom);
    frustum[8] = (float)(right + left) / (float)(right - left);
    frustum[9] = (float)(top + bottom) / (float)(top - bottom);
    frustum[10] = -((float)zFar + (float)zNear) / ((float)zFar - (float)zNear);
    frustum[11] = -1.0f;
    frustum[14] = -2.0f * (float)zFar * (float)zNear / ((float)zFar - (float)zNear);
    mat_multiply(g_current_matrix, g_current_matrix, frustum);
}

void glGetFloatv(GLenum pname, GLfloat* params) {
    int i;
    switch (pname) {
        case GL_MODELVIEW_MATRIX:
            for (i = 0; i < 16; i++) params[i] = g_modelview_stack[g_modelview_depth][i];
            break;
        case GL_PROJECTION_MATRIX:
            for (i = 0; i < 16; i++) params[i] = g_projection_stack[g_projection_depth][i];
            break;
        case GL_MODELVIEW_STACK_DEPTH:  params[0] = (float)g_modelview_depth; break;
        case GL_PROJECTION_STACK_DEPTH: params[0] = (float)g_projection_depth; break;
        case GL_MAX_MODELVIEW_STACK_DEPTH:  params[0] = (float)GLES_MAX_MATRIX_STACK; break;
        case GL_MAX_PROJECTION_STACK_DEPTH: params[0] = (float)GLES_MAX_MATRIX_STACK; break;
        default: break;
    }
}

// --- Vertex array operations ---

void glEnableClientState(GLenum cap) {
    switch (cap) {
        case GL_VERTEX_ARRAY:        g_vertex_array_enabled = GL_TRUE; break;
        case GL_NORMAL_ARRAY:        g_normal_array_enabled = GL_TRUE; break;
        case GL_COLOR_ARRAY:         g_color_array_enabled = GL_TRUE; break;
        case GL_TEXTURE_COORD_ARRAY: g_texcoord_array_enabled = GL_TRUE; break;
        default: break;
    }
}

void glDisableClientState(GLenum cap) {
    switch (cap) {
        case GL_VERTEX_ARRAY:        g_vertex_array_enabled = GL_FALSE; break;
        case GL_NORMAL_ARRAY:        g_normal_array_enabled = GL_FALSE; break;
        case GL_COLOR_ARRAY:         g_color_array_enabled = GL_FALSE; break;
        case GL_TEXTURE_COORD_ARRAY: g_texcoord_array_enabled = GL_FALSE; break;
        default: break;
    }
}

void glVertexPointer(GLint size, GLenum type, GLsizei stride, const void* ptr) {
    g_vertex_size = size;
    g_vertex_type = type;
    g_vertex_stride = stride;
    g_vertex_pointer = ptr;
}

void glNormalPointer(GLenum type, GLsizei stride, const void* ptr) {
    g_normal_size = 3;
    g_normal_type = type;
    g_normal_stride = stride;
    g_normal_pointer = ptr;
}

void glColorPointer(GLint size, GLenum type, GLsizei stride, const void* ptr) {
    g_color_size = size;
    g_color_type = type;
    g_color_stride = stride;
    g_color_pointer = ptr;
}

void glTexCoordPointer(GLint size, GLenum type, GLsizei stride, const void* ptr) {
    g_texcoord_size = size;
    g_texcoord_type = type;
    g_texcoord_stride = stride;
    g_texcoord_pointer = ptr;
}

// --- State operations ---

void glPushAttrib(GLbitfield mask) {
    (void)mask;
    if (g_attrib_depth >= GLES_MAX_ATTRIB_STACK) return;
    AttribState* s = &g_attrib_stack[g_attrib_depth++];
    s->vertex_array_enabled = g_vertex_array_enabled;
    s->normal_array_enabled = g_normal_array_enabled;
    s->color_array_enabled = g_color_array_enabled;
    s->texcoord_array_enabled = g_texcoord_array_enabled;
    s->lighting_enabled = g_lighting_enabled;
    s->color_material_enabled = g_color_material_enabled;
    s->blend_enabled = glIsEnabled(GL_BLEND);
    s->depth_test_enabled = glIsEnabled(GL_DEPTH_TEST);
    s->cull_face_enabled = glIsEnabled(GL_CULL_FACE);
    s->texture_2d_enabled = glIsEnabled(GL_TEXTURE_2D);
    s->alpha_test_enabled = (g_alpha_test_func != GL_ALWAYS);
    s->alpha_test_func    = g_alpha_test_func;
    s->alpha_test_ref     = g_alpha_test_ref;
    glGetIntegerv(GL_VIEWPORT, s->viewport);
}

void glPopAttrib(void) {
    if (g_attrib_depth <= 0) return;
    AttribState* s = &g_attrib_stack[--g_attrib_depth];
    g_vertex_array_enabled = s->vertex_array_enabled;
    g_normal_array_enabled = s->normal_array_enabled;
    g_color_array_enabled = s->color_array_enabled;
    g_texcoord_array_enabled = s->texcoord_array_enabled;
    g_lighting_enabled = s->lighting_enabled;
    g_color_material_enabled = s->color_material_enabled;
    if (s->blend_enabled) glEnable(GL_BLEND); else glDisable(GL_BLEND);
    if (s->depth_test_enabled) glEnable(GL_DEPTH_TEST); else glDisable(GL_DEPTH_TEST);
    if (s->cull_face_enabled) glEnable(GL_CULL_FACE); else glDisable(GL_CULL_FACE);
    if (s->texture_2d_enabled) glEnable(GL_TEXTURE_2D); else glDisable(GL_TEXTURE_2D);
    g_alpha_test_func = s->alpha_test_func;
    g_alpha_test_ref  = s->alpha_test_ref;
    glViewport(s->viewport[0], s->viewport[1], s->viewport[2], s->viewport[3]);
}

// --- Lighting operations ---

static int light_index(GLenum light) {
    int idx = (int)(light - GL_LIGHT0);
    if (idx >= 0 && idx < GLES_MAX_LIGHTS) return idx;
    return -1;
}

// --- Capability enable/disable interception ---
// GLES2 has no fixed-pipeline lighting; intercept the desktop GL lighting
// capabilities (GL_LIGHTING, GL_LIGHT0..7, GL_COLOR_MATERIAL) into the
// tracked software state, and forward every unrelated capability to the
// real GLES2 driver so native enable/disable semantics are preserved.

#include <dlfcn.h>
typedef void (GLAPIENTRY *GL_EnableProc)(GLenum);
typedef void (GLAPIENTRY *GL_DisableProc)(GLenum);

static GL_EnableProc  g_real_glEnable  = NULL;
static GL_DisableProc g_real_glDisable = NULL;

static void gles_resolve_enable_procs(void) {
    if (g_real_glEnable && g_real_glDisable) return;
    g_real_glEnable  = (GL_EnableProc)dlsym(RTLD_NEXT, "glEnable");
    g_real_glDisable = (GL_DisableProc)dlsym(RTLD_NEXT, "glDisable");
    if (!g_real_glEnable)
        g_real_glEnable  = (GL_EnableProc)eglGetProcAddress("glEnable");
    if (!g_real_glDisable)
        g_real_glDisable = (GL_DisableProc)eglGetProcAddress("glDisable");
}

void glEnable(GLenum cap) {
    switch (cap) {
        case GL_LIGHTING:
            g_lighting_enabled = GL_TRUE;
            return;
        case GL_COLOR_MATERIAL:
            g_color_material_enabled = GL_TRUE;
            return;
        default: {
            int idx = light_index(cap);   // GL_LIGHT0 .. GL_LIGHT7
            if (idx >= 0) {
                g_light_enabled[idx] = GL_TRUE;
                return;
            }
            break;
        }
    }
    gles_resolve_enable_procs();
    if (g_real_glEnable) g_real_glEnable(cap);
}

void glDisable(GLenum cap) {
    switch (cap) {
        case GL_LIGHTING:
            g_lighting_enabled = GL_FALSE;
            return;
        case GL_COLOR_MATERIAL:
            g_color_material_enabled = GL_FALSE;
            return;
        default: {
            int idx = light_index(cap);   // GL_LIGHT0 .. GL_LIGHT7
            if (idx >= 0) {
                g_light_enabled[idx] = GL_FALSE;
                return;
            }
            break;
        }
    }
    gles_resolve_enable_procs();
    if (g_real_glDisable) g_real_glDisable(cap);
}

// glGetString: forward to the real GLES2 implementation when a GL context is
// available; otherwise safely return NULL instead of dereferencing a NULL
// function pointer (no GL context on the local OHOS build host).
static const GLubyte* (*g_real_glGetString)(GLenum) = NULL;

const GLubyte* glGetString(GLenum name) {
    // No GL context on this build host: return NULL safely instead of
    // forwarding to a real glGetString call that would crash (SIGSEGV).
    if (!eglGetCurrentContext()) {
        return NULL;
    }
    if (!g_real_glGetString) {
        g_real_glGetString = (const GLubyte* (*)(GLenum))dlsym(RTLD_NEXT, "glGetString");
        if (!g_real_glGetString) {
            g_real_glGetString = (const GLubyte* (*)(GLenum))eglGetProcAddress("glGetString");
        }
    }
    if (g_real_glGetString) {
        return g_real_glGetString(name);
    }
    return NULL;
}

void glLightf(GLenum light, GLenum pname, GLfloat param) {
    int idx = light_index(light);
    if (idx < 0) return;
    switch (pname) {
        case GL_SPOT_EXPONENT:     g_light_spot_exponent[idx] = param; break;
        case GL_SPOT_CUTOFF:       g_light_spot_cutoff[idx] = param; break;
        case GL_CONSTANT_ATTENUATION: g_light_const_atten[idx] = param; break;
        case GL_LINEAR_ATTENUATION:   g_light_linear_atten[idx] = param; break;
        case GL_QUADRATIC_ATTENUATION: g_light_quad_atten[idx] = param; break;
        default: break;
    }
}

void glLightfv(GLenum light, GLenum pname, const GLfloat* params) {
    int idx = light_index(light);
    if (idx < 0) return;
    int i;
    switch (pname) {
        case GL_AMBIENT:   for (i = 0; i < 4; i++) g_light_ambient[idx][i] = params[i]; break;
        case GL_DIFFUSE:   for (i = 0; i < 4; i++) g_light_diffuse[idx][i] = params[i]; break;
        case GL_SPECULAR:  for (i = 0; i < 4; i++) g_light_specular[idx][i] = params[i]; break;
        case GL_POSITION:  for (i = 0; i < 4; i++) g_light_position[idx][i] = params[i]; break;
        case GL_SPOT_DIRECTION: for (i = 0; i < 3; i++) g_light_spot_direction[idx][i] = params[i]; break;
        default: break;
    }
}

void glGetLightfv(GLenum light, GLenum pname, GLfloat* params) {
    int idx = light_index(light);
    if (idx < 0) return;
    int i;
    switch (pname) {
        case GL_AMBIENT:   for (i = 0; i < 4; i++) params[i] = g_light_ambient[idx][i]; break;
        case GL_DIFFUSE:   for (i = 0; i < 4; i++) params[i] = g_light_diffuse[idx][i]; break;
        case GL_SPECULAR:  for (i = 0; i < 4; i++) params[i] = g_light_specular[idx][i]; break;
        case GL_POSITION:  for (i = 0; i < 4; i++) params[i] = g_light_position[idx][i]; break;
        case GL_SPOT_DIRECTION: for (i = 0; i < 3; i++) params[i] = g_light_spot_direction[idx][i]; break;
        default: break;
    }
}

void glMaterialfv(GLenum face, GLenum pname, const GLfloat* params) {
    (void)face;
    int i;
    switch (pname) {
        case GL_AMBIENT:   for (i = 0; i < 4; i++) g_material_ambient[i] = params[i]; break;
        case GL_DIFFUSE:   for (i = 0; i < 4; i++) g_material_diffuse[i] = params[i]; break;
        case GL_SPECULAR:  for (i = 0; i < 4; i++) g_material_specular[i] = params[i]; break;
        case GL_EMISSION:  for (i = 0; i < 4; i++) g_material_emission[i] = params[i]; break;
        case GL_SHININESS: g_material_shininess = params[0]; break;
        case GL_AMBIENT_AND_DIFFUSE:
            for (i = 0; i < 4; i++) { g_material_ambient[i] = params[i]; g_material_diffuse[i] = params[i]; }
            break;
        default: break;
    }
}

void glGetMaterialfv(GLenum face, GLenum pname, GLfloat* params) {
    (void)face;
    int i;
    switch (pname) {
        case GL_AMBIENT:   for (i = 0; i < 4; i++) params[i] = g_material_ambient[i]; break;
        case GL_DIFFUSE:   for (i = 0; i < 4; i++) params[i] = g_material_diffuse[i]; break;
        case GL_SPECULAR:  for (i = 0; i < 4; i++) params[i] = g_material_specular[i]; break;
        case GL_EMISSION:  for (i = 0; i < 4; i++) params[i] = g_material_emission[i]; break;
        case GL_SHININESS: params[0] = g_material_shininess; break;
        default: break;
    }
}

void glColorMaterial(GLenum face, GLenum mode) {
    g_color_material_face = face;
    g_color_material_mode = mode;
}

void glLightModelfv(GLenum pname, const GLfloat* params) {
    int i;
    switch (pname) {
        case GL_LIGHT_MODEL_AMBIENT: for (i = 0; i < 4; i++) g_light_model_ambient[i] = params[i]; break;
        case GL_LIGHT_MODEL_TWO_SIDE: g_light_model_two_side = (params[0] != 0.0f); break;
        default: break;
    }
}

void glAlphaFunc(GLenum func, GLclampf ref) {
    g_alpha_test_func = func;
    g_alpha_test_ref = ref;
}

void glPrioritizeTextures(GLsizei n, const GLuint* textures, const GLclampf* priorities) {
    (void)n; (void)textures; (void)priorities;
}

void glTexEnvi(GLenum target, GLenum pname, GLint param) {
    if (target == GL_TEXTURE_ENV && pname == GL_TEXTURE_ENV_MODE)
        g_tex_env_mode = (GLenum)param;
}

void glTexEnvf(GLenum target, GLenum pname, GLfloat param) {
    if (target == GL_TEXTURE_ENV && pname == GL_TEXTURE_ENV_MODE)
        g_tex_env_mode = (GLenum)((int)param);
}

void glPolygonMode(GLenum face, GLenum mode) {
    // GLES2 does not support polygon mode; polygons are always filled.
    (void)face; (void)mode;
}

static GLenum g_shade_model = GL_SMOOTH;

void glShadeModel(GLenum mode) {
    // GLES2 shaders always interpolate per-vertex attributes (smooth shading);
    // desktop GL_FLAT has no GLES2 equivalent (would need GLSL ES 3.00 flat
    // varying qualifier).  The game only requests GL_SMOOTH, which is the
    // GLES2 default behavior.
    g_shade_model = mode;
}

void glClearDepth(GLclampd depth) {
    glClearDepthf((GLclampf)depth);
}

void glDepthRange(GLclampd n, GLclampd f) {
    glDepthRangef((GLclampf)n, (GLclampf)f);
}

void glColor4f(GLfloat r, GLfloat g, GLfloat b, GLfloat a) {
    g_current_color[0] = r;
    g_current_color[1] = g;
    g_current_color[2] = b;
    g_current_color[3] = a;
}

// glGetTexImage: not available in GLES2.  Read back texture content via
// FBO attachment + glReadPixels.  Dimensions are tracked from every
// glTexImage2D call (see gles_glTexImage2D).
// GLES2 glReadPixels only accepts a small set of (format,type) pairs and
// always returns rows in bottom-up order (texel v=0 first), which matches
// glGetTexImage's convention, so row order is preserved.  For any requested
// desktop GL format/type (RGB, LUMINANCE, ALPHA, LUMINANCE_ALPHA, packed
// shorts) we read GL_RGBA/GL_UNSIGNED_BYTE and convert, honoring
// GL_PACK_ALIGNMENT in both the readback and the output buffers.
void glGetTexImage(GLenum target, GLint level, GLenum format, GLenum type, void* pixels) {
    if (target != GL_TEXTURE_2D || level != 0 || pixels == NULL) return;

    GLint bound = 0;
    glGetIntegerv(GL_TEXTURE_BINDING_2D, &bound);
    GLuint tex = (GLuint)bound;

    int i;
    for (i = 0; i < g_tracked_tex_count; i++) {
        if (g_tracked_tex[i] == tex) break;
    }
    if (i >= g_tracked_tex_count) return;    // not tracked
    GLsizei w = g_tracked_tex_w[i];
    GLsizei h = g_tracked_tex_h[i];
    if (w <= 0 || h <= 0) return;

    GLint pack_align = 4;
    glGetIntegerv(GL_PACK_ALIGNMENT, &pack_align);
    if (pack_align != 1 && pack_align != 2 && pack_align != 4 && pack_align != 8)
        pack_align = 4;
    int align_rows = (pack_align > 0) ? pack_align : 4;

    GLint prev_fbo = 0;
    glGetIntegerv(GL_FRAMEBUFFER_BINDING, &prev_fbo);

    GLuint fbo = 0;
    glGenFramebuffers(1, &fbo);
    glBindFramebuffer(GL_FRAMEBUFFER, fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, level);

    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE) {
        // Intermediate GL_RGBA/GL_UNSIGNED_BYTE readback.
        int row_in = w * 4;
        int row_pad_in = (align_rows - (row_in % align_rows)) % align_rows;
        int src_row = row_in + row_pad_in;
        int dst_ch = 0, dst_bpp = 0;
        switch (format) {
            case GL_RGBA:            dst_ch = 4; dst_bpp = (type == GL_UNSIGNED_BYTE) ? 1 : 2; break;
            case GL_RGB:             dst_ch = 3; dst_bpp = (type == GL_UNSIGNED_BYTE) ? 1 : 2; break;
            case GL_LUMINANCE:       dst_ch = 1; dst_bpp = (type == GL_UNSIGNED_BYTE) ? 1 : 2; break;
            case GL_ALPHA:           dst_ch = 1; dst_bpp = (type == GL_UNSIGNED_BYTE) ? 1 : 2; break;
            case GL_LUMINANCE_ALPHA: dst_ch = 2; dst_bpp = (type == GL_UNSIGNED_BYTE) ? 1 : 2; break;
            default: break;
        }
        if (dst_ch > 0 && dst_bpp > 0) {
            unsigned char* rgba = (unsigned char*)malloc((size_t)src_row * (size_t)h);
            if (rgba) {
                glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
                int bytes_pp = 0;
                // Row stride must use the actual bytes per pixel: a plain
                // GL_UNSIGNED_BYTE format stores dst_ch bytes per pixel, while
                // 16-bit packed formats (565 / 4444 / 5551) pack a whole pixel
                // into a single unsigned short (2 bytes) regardless of dst_ch.
                if (type == GL_UNSIGNED_BYTE) {
                    bytes_pp = dst_ch;
                } else if (type == GL_UNSIGNED_SHORT_5_6_5 ||
                           type == GL_UNSIGNED_SHORT_4_4_4_4 ||
                           type == GL_UNSIGNED_SHORT_5_5_5_1) {
                    bytes_pp = 2; // one unsigned short per pixel
                } else {
                    bytes_pp = dst_ch * dst_bpp;
                }
                if (bytes_pp <= 0 || w <= 0 || h <= 0) { free(rgba); return; }
                int out_pix = w * bytes_pp;
                int out_row = out_pix + ((align_rows - (out_pix % align_rows)) % align_rows);
                unsigned char* dst = (unsigned char*)pixels;
                int y;
                for (y = 0; y < h; y++) {
                    const unsigned char* sp = rgba + (size_t)y * src_row;
                    unsigned char* dp = dst + (size_t)y * out_row;
                    int x;
                    for (x = 0; x < w; x++) {
                        unsigned char r = sp[x*4+0], g = sp[x*4+1], b = sp[x*4+2], a = sp[x*4+3];
                        if (type == GL_UNSIGNED_BYTE) {
                            switch (format) {
                                case GL_RGBA:
                                    dp[x*4+0] = r; dp[x*4+1] = g; dp[x*4+2] = b; dp[x*4+3] = a; break;
                                case GL_RGB:
                                    dp[x*3+0] = r; dp[x*3+1] = g; dp[x*3+2] = b; break;
                                case GL_LUMINANCE:
                                    dp[x] = r; break;
                                case GL_ALPHA:
                                    dp[x] = a; break;
                                case GL_LUMINANCE_ALPHA:
                                    dp[x*2+0] = r; dp[x*2+1] = a; break;
                                default: break;
                            }
                        } else if (type == GL_UNSIGNED_SHORT_5_6_5 && format == GL_RGB) {
                            unsigned short v = (unsigned short)(((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3));
                            ((unsigned short*)dp)[x] = v;
                        } else if (type == GL_UNSIGNED_SHORT_4_4_4_4 && format == GL_RGBA) {
                            unsigned short v = (unsigned short)((r >> 4) << 12 | (g >> 4) << 8 | (b >> 4) << 4 | (a >> 4));
                            ((unsigned short*)dp)[x] = v;
                        } else if (type == GL_UNSIGNED_SHORT_5_5_5_1 && format == GL_RGBA) {
                            unsigned short v = (unsigned short)((r >> 3) << 11 | (g >> 3) << 6 | (b >> 3) << 1 | (a >> 7));
                            ((unsigned short*)dp)[x] = v;
                        }
                    }
                }
                free(rgba);
            }
        } else {
            // Unrecognized combination: hand through directly (GLES2 will
            // reject truly unsupported pairs the same way desktop GL would).
            glReadPixels(0, 0, w, h, format, type, pixels);
        }
    }

    glBindFramebuffer(GL_FRAMEBUFFER, (GLuint)prev_fbo);
    glDeleteFramebuffers(1, &fbo);
}

// ===== GLU functions =====

void gluLookAt(GLdouble eyeX, GLdouble eyeY, GLdouble eyeZ,
               GLdouble centerX, GLdouble centerY, GLdouble centerZ,
               GLdouble upX, GLdouble upY, GLdouble upZ) {
    GLdouble forward[3], side[3], up[3];
    GLdouble m[16];
    int i;
    forward[0] = centerX - eyeX;
    forward[1] = centerY - eyeY;
    forward[2] = centerZ - eyeZ;
    GLdouble fwdLen = sqrt(forward[0]*forward[0] + forward[1]*forward[1] + forward[2]*forward[2]);
    if (fwdLen != 0.0) { forward[0] /= fwdLen; forward[1] /= fwdLen; forward[2] /= fwdLen; }
    up[0] = upX; up[1] = upY; up[2] = upZ;
    GLdouble upLen = sqrt(up[0]*up[0] + up[1]*up[1] + up[2]*up[2]);
    if (upLen != 0.0) { up[0] /= upLen; up[1] /= upLen; up[2] /= upLen; }
    side[0] = forward[1]*up[2] - forward[2]*up[1];
    side[1] = forward[2]*up[0] - forward[0]*up[2];
    side[2] = forward[0]*up[1] - forward[1]*up[0];
    GLdouble sideLen = sqrt(side[0]*side[0] + side[1]*side[1] + side[2]*side[2]);
    if (sideLen != 0.0) { side[0] /= sideLen; side[1] /= sideLen; side[2] /= sideLen; }
    up[0] = side[1]*forward[2] - side[2]*forward[1];
    up[1] = side[2]*forward[0] - side[0]*forward[2];
    up[2] = side[0]*forward[1] - side[1]*forward[0];
    for (i = 0; i < 16; i++) m[i] = 0.0;
    m[0] = side[0];  m[4] = side[1];  m[8]  = side[2];  m[12] = 0.0;
    m[1] = up[0];    m[5] = up[1];    m[9]  = up[2];    m[13] = 0.0;
    m[2] = -forward[0]; m[6] = -forward[1]; m[10] = -forward[2]; m[14] = 0.0;
    m[3] = 0.0;      m[7] = 0.0;      m[11] = 0.0;      m[15] = 1.0;
    glMultMatrixd(m);
    glTranslated(-eyeX, -eyeY, -eyeZ);
}

void gluPerspective(GLdouble fovy, GLdouble aspect, GLdouble zNear, GLdouble zFar) {
    GLdouble f = 1.0 / tan(fovy * 3.14159265358979323846 / 360.0);
    GLdouble m[16];
    int i;
    for (i = 0; i < 16; i++) m[i] = 0.0;
    m[0] = f / aspect;
    m[5] = f;
    m[10] = (zFar + zNear) / (zNear - zFar);
    m[11] = -1.0;
    m[14] = (2.0 * zFar * zNear) / (zNear - zFar);
    glMultMatrixd(m);
}

const GLubyte* gluErrorString(GLenum error) {
    switch (error) {
        case GL_NO_ERROR:          return (const GLubyte*)"no error";
        case GL_INVALID_ENUM:      return (const GLubyte*)"invalid enumerant";
        case GL_INVALID_VALUE:     return (const GLubyte*)"invalid value";
        case GL_INVALID_OPERATION: return (const GLubyte*)"invalid operation";
        case GL_OUT_OF_MEMORY:     return (const GLubyte*)"out of memory";
        default:                   return (const GLubyte*)"unknown error";
    }
}

int gluBuild2DMipmaps(GLenum target, GLint components, GLsizei width,
                      GLsizei height, GLenum format, GLenum type, const void* data) {
    // Upload the top-level mipmap, then let GLES2 generate the chain.
    // GLES2 minimum: must have a valid internal format.
    GLint internal = components;
    if (internal == 3) internal = GL_RGB;
    if (internal == 4) internal = GL_RGBA;
    glTexImage2D(target, 0, internal, width, height, 0, format, type, data);
    glGenerateMipmap(target);
    return 0;
}

// ===== gles_init =====

void gles_init(void) {
    static int initialized = 0;
    if (initialized) return;
    initialized = 1;

    // Initialize matrix stacks
    mat_identity(g_modelview_stack[0]);
    mat_identity(g_projection_stack[0]);
    mat_identity(g_texture_stack[0]);
    g_modelview_depth = 0;
    g_projection_depth = 0;
    g_texture_depth = 0;
    g_current_matrix = g_modelview_stack[0];

    // Save real GLES2 draw function pointers
    g_real_glDrawElements = glDrawElements;
    g_real_glDrawArrays = glDrawArrays;

    // Compile shaders
    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &g_vert_src, NULL);
    glCompileShader(vs);
    {
        GLint status = GL_FALSE;
        glGetShaderiv(vs, GL_COMPILE_STATUS, &status);
        if (status != GL_TRUE) {
            char log[1024];
            GLsizei logLen = 0;
            glGetShaderInfoLog(vs, sizeof(log) - 1, &logLen, log);
            log[logLen < sizeof(log) ? logLen : sizeof(log) - 1] = '\0';
            fprintf(stderr, "[gles_compat] vertex shader compile FAILED:\n%s\n", log);
        }
    }

    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &g_frag_src, NULL);
    glCompileShader(fs);
    {
        GLint status = GL_FALSE;
        glGetShaderiv(fs, GL_COMPILE_STATUS, &status);
        if (status != GL_TRUE) {
            char log[1024];
            GLsizei logLen = 0;
            glGetShaderInfoLog(fs, sizeof(log) - 1, &logLen, log);
            log[logLen < sizeof(log) ? logLen : sizeof(log) - 1] = '\0';
            fprintf(stderr, "[gles_compat] fragment shader compile FAILED:\n%s\n", log);
        }
    }

    g_ff_program = glCreateProgram();
    glAttachShader(g_ff_program, vs);
    glAttachShader(g_ff_program, fs);
    glBindAttribLocation(g_ff_program, ATTR_VERTEX, "a_position");
    glBindAttribLocation(g_ff_program, ATTR_NORMAL, "a_normal");
    glBindAttribLocation(g_ff_program, ATTR_COLOR, "a_color");
    glBindAttribLocation(g_ff_program, ATTR_TEXCOORD, "a_texcoord");
    glLinkProgram(g_ff_program);
    {
        GLint status = GL_FALSE;
        glGetProgramiv(g_ff_program, GL_LINK_STATUS, &status);
        if (status != GL_TRUE) {
            char log[1024];
            GLsizei logLen = 0;
            glGetProgramInfoLog(g_ff_program, sizeof(log) - 1, &logLen, log);
            log[logLen < sizeof(log) ? logLen : sizeof(log) - 1] = '\0';
            fprintf(stderr, "[gles_compat] program link FAILED:\n%s\n", log);
        }
    }
    glUseProgram(g_ff_program);

    // Get uniform locations
    g_unif_mvp = glGetUniformLocation(g_ff_program, "u_mvp");
    g_unif_mv = glGetUniformLocation(g_ff_program, "u_mv");
    g_unif_normal_matrix = glGetUniformLocation(g_ff_program, "u_normal_matrix");
    g_unif_tex0 = glGetUniformLocation(g_ff_program, "u_tex0");
    g_unif_lighting_enabled = glGetUniformLocation(g_ff_program, "u_lighting_enabled");
    g_unif_current_color = glGetUniformLocation(g_ff_program, "u_current_color");
    g_unif_light_model_ambient = glGetUniformLocation(g_ff_program, "u_light_model_ambient");
    g_unif_material_ambient = glGetUniformLocation(g_ff_program, "u_material_ambient");
    g_unif_material_diffuse = glGetUniformLocation(g_ff_program, "u_material_diffuse");
    g_unif_material_specular = glGetUniformLocation(g_ff_program, "u_material_specular");
    g_unif_material_emission = glGetUniformLocation(g_ff_program, "u_material_emission");
    g_unif_material_shininess = glGetUniformLocation(g_ff_program, "u_material_shininess");
    g_unif_has_texcoord = glGetUniformLocation(g_ff_program, "u_has_texcoord");
    g_unif_has_color = glGetUniformLocation(g_ff_program, "u_has_color");
    g_unif_alpha_test_enabled = glGetUniformLocation(g_ff_program, "u_alpha_test_enabled");
    g_unif_alpha_test_func = glGetUniformLocation(g_ff_program, "u_alpha_test_func");
    g_unif_alpha_test_ref = glGetUniformLocation(g_ff_program, "u_alpha_test_ref");
    g_unif_tex_env_mode = glGetUniformLocation(g_ff_program, "u_tex_env_mode");

    for (int i = 0; i < GLES_MAX_LIGHTS; i++) {
        char name[32];
        sprintf(name, "u_light_positions[%d]", i);
        g_unif_light_positions[i] = glGetUniformLocation(g_ff_program, name);
        sprintf(name, "u_light_ambients[%d]", i);
        g_unif_light_ambients[i] = glGetUniformLocation(g_ff_program, name);
        sprintf(name, "u_light_diffuses[%d]", i);
        g_unif_light_diffuses[i] = glGetUniformLocation(g_ff_program, name);
        sprintf(name, "u_light_speculars[%d]", i);
        g_unif_light_speculars[i] = glGetUniformLocation(g_ff_program, name);
        sprintf(name, "u_light_enables[%d]", i);
        g_unif_light_enables[i] = glGetUniformLocation(g_ff_program, name);
    }

    // Set texture unit 0
    if (g_unif_tex0 >= 0)
        glUniform1i(g_unif_tex0, 0);
}

// ===== gles_apply_* =====

void gles_apply_matrices(void) {
    float mvp[16];
    mat_multiply(mvp, g_projection_stack[g_projection_depth],
                 g_modelview_stack[g_modelview_depth]);
    if (g_unif_mvp >= 0)
        glUniformMatrix4fv(g_unif_mvp, 1, GL_FALSE, mvp);
    if (g_unif_mv >= 0)
        glUniformMatrix4fv(g_unif_mv, 1, GL_FALSE, g_modelview_stack[g_modelview_depth]);

    float normal_mat[9];
    float* mv = g_modelview_stack[g_modelview_depth];
    normal_mat[0] = mv[0]; normal_mat[1] = mv[1]; normal_mat[2] = mv[2];
    normal_mat[3] = mv[4]; normal_mat[4] = mv[5]; normal_mat[5] = mv[6];
    normal_mat[6] = mv[8]; normal_mat[7] = mv[9]; normal_mat[8] = mv[10];
    if (g_unif_normal_matrix >= 0)
        glUniformMatrix3fv(g_unif_normal_matrix, 1, GL_FALSE, normal_mat);
}

void gles_apply_vertex_arrays(void) {
    if (g_vertex_array_enabled && g_vertex_pointer) {
        glEnableVertexAttribArray(ATTR_VERTEX);
        glVertexAttribPointer(ATTR_VERTEX, g_vertex_size, g_vertex_type, GL_FALSE,
                              g_vertex_stride, g_vertex_pointer);
    } else {
        glDisableVertexAttribArray(ATTR_VERTEX);
    }

    if (g_normal_array_enabled && g_normal_pointer) {
        glEnableVertexAttribArray(ATTR_NORMAL);
        glVertexAttribPointer(ATTR_NORMAL, g_normal_size, g_normal_type, GL_TRUE,
                              g_normal_stride, g_normal_pointer);
    } else {
        glDisableVertexAttribArray(ATTR_NORMAL);
    }

    if (g_color_array_enabled && g_color_pointer) {
        glEnableVertexAttribArray(ATTR_COLOR);
        glVertexAttribPointer(ATTR_COLOR, g_color_size, g_color_type, GL_TRUE,
                              g_color_stride, g_color_pointer);
    } else {
        glDisableVertexAttribArray(ATTR_COLOR);
    }

    if (g_texcoord_array_enabled && g_texcoord_pointer) {
        glEnableVertexAttribArray(ATTR_TEXCOORD);
        glVertexAttribPointer(ATTR_TEXCOORD, g_texcoord_size, g_texcoord_type, GL_FALSE,
                              g_texcoord_stride, g_texcoord_pointer);
    } else {
        glDisableVertexAttribArray(ATTR_TEXCOORD);
    }

    if (g_unif_has_texcoord >= 0)
        glUniform1i(g_unif_has_texcoord,
                    (g_texcoord_array_enabled && g_texcoord_pointer) ? 1 : 0);
    if (g_unif_has_color >= 0)
        glUniform1i(g_unif_has_color,
                    (g_color_array_enabled && g_color_pointer) ? 1 : 0);
}

void gles_apply_lighting(void) {
    if (g_unif_lighting_enabled >= 0)
        glUniform1i(g_unif_lighting_enabled, g_lighting_enabled ? 1 : 0);
    if (g_unif_light_model_ambient >= 0)
        glUniform4fv(g_unif_light_model_ambient, 1, g_light_model_ambient);
    // GL_COLOR_MATERIAL: when enabled, the current color drives the material
    // ambient/diffuse component selected by g_color_material_mode (face must
    // cover the front side). Default state is GL_AMBIENT_AND_DIFFUSE.
    int cm_face = (g_color_material_face == GL_FRONT ||
                   g_color_material_face == GL_FRONT_AND_BACK);
    int cm_ambient = g_color_material_enabled && cm_face &&
                     (g_color_material_mode == GL_AMBIENT ||
                      g_color_material_mode == GL_AMBIENT_AND_DIFFUSE);
    int cm_diffuse = g_color_material_enabled && cm_face &&
                     (g_color_material_mode == GL_DIFFUSE ||
                      g_color_material_mode == GL_AMBIENT_AND_DIFFUSE);
    if (g_unif_material_ambient >= 0)
        glUniform4fv(g_unif_material_ambient, 1, cm_ambient ? g_current_color : g_material_ambient);
    if (g_unif_material_diffuse >= 0)
        glUniform4fv(g_unif_material_diffuse, 1, cm_diffuse ? g_current_color : g_material_diffuse);
    if (g_unif_current_color >= 0)
        glUniform4fv(g_unif_current_color, 1, g_current_color);
    if (g_unif_material_specular >= 0)
        glUniform4fv(g_unif_material_specular, 1, g_material_specular);
    if (g_unif_material_emission >= 0)
        glUniform4fv(g_unif_material_emission, 1, g_material_emission);
    if (g_unif_material_shininess >= 0)
        glUniform1f(g_unif_material_shininess, g_material_shininess);

    for (int i = 0; i < GLES_MAX_LIGHTS; i++) {
        float eye_pos[4];
        float* mv = g_modelview_stack[g_modelview_depth];
        for (int j = 0; j < 4; j++) {
            eye_pos[j] = mv[j*4] * g_light_position[i][0]
                       + mv[j*4+1] * g_light_position[i][1]
                       + mv[j*4+2] * g_light_position[i][2]
                       + mv[j*4+3] * g_light_position[i][3];
        }
        if (g_unif_light_positions[i] >= 0)
            glUniform4fv(g_unif_light_positions[i], 1, eye_pos);
        if (g_unif_light_ambients[i] >= 0)
            glUniform4fv(g_unif_light_ambients[i], 1, g_light_ambient[i]);
        if (g_unif_light_diffuses[i] >= 0)
            glUniform4fv(g_unif_light_diffuses[i], 1, g_light_diffuse[i]);
        if (g_unif_light_speculars[i] >= 0)
            glUniform4fv(g_unif_light_speculars[i], 1, g_light_specular[i]);
        if (g_unif_light_enables[i] >= 0)
            glUniform1i(g_unif_light_enables[i], g_light_enabled[i] ? 1 : 0);
    }

    // Alpha test
    if (g_unif_alpha_test_enabled >= 0)
        glUniform1i(g_unif_alpha_test_enabled, (g_alpha_test_func != GL_ALWAYS) ? 1 : 0);
    if (g_unif_alpha_test_func >= 0)
        // Map desktop GL_NEVER..GL_ALWAYS enums (0x0200..0x0207) to shader
        // func indices 0..7: 0=NEVER 1=LESS 2=EQUAL 3=LEQUAL 4=GREATER
        // 5=NOTEQUAL 6=GEQUAL 7=ALWAYS, matching the fragment shader branch.
        glUniform1i(g_unif_alpha_test_func,
                    g_alpha_test_func == GL_NEVER    ? 0 :
                    g_alpha_test_func == GL_LESS     ? 1 :
                    g_alpha_test_func == GL_EQUAL    ? 2 :
                    g_alpha_test_func == GL_LEQUAL   ? 3 :
                    g_alpha_test_func == GL_GREATER  ? 4 :
                    g_alpha_test_func == GL_NOTEQUAL ? 5 :
                    g_alpha_test_func == GL_GEQUAL   ? 6 :
                                                      7); // GL_ALWAYS
    if (g_unif_alpha_test_ref >= 0)
        glUniform1f(g_unif_alpha_test_ref, g_alpha_test_ref);

    // Tex env mode
    if (g_unif_tex_env_mode >= 0) {
        int mode_val = 2; // default modulate
        if (g_tex_env_mode == GL_REPLACE) mode_val = 1;
        else if (g_tex_env_mode == GL_MODULATE) mode_val = 2;
        glUniform1i(g_unif_tex_env_mode, mode_val);
    }
}

void gles_apply_state(void) {
    glUseProgram(g_ff_program);
    gles_apply_matrices();
    gles_apply_vertex_arrays();
    gles_apply_lighting();
}
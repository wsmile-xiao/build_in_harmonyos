cmake_minimum_required(VERSION 3.15)
project(test_vao C)

# Pull in the tested package (mupdf-gl) and the freeglut header deps via CMakeDeps.
find_package(mupdf-gl REQUIRED)
find_package(freeglut REQUIRED)

# Locate the mupdf-gl package root from the CMakeDeps data file, which sets
# <name>_PACKAGE_FOLDER_<CONFIG> per build type. Do NOT derive it from
# INTERFACE_INCLUDE_DIRECTORIES: conan wraps that property in a
# $<$<CONFIG:...>:...> generator expression that get_target_property returns
# unevaluated.
string(TOUPPER "${CMAKE_BUILD_TYPE}" _MGL_BT)
set(MUPDFGL_PKGROOT "${mupdf-gl_PACKAGE_FOLDER_${_MGL_BT}}")
if(NOT MUPDFGL_PKGROOT)
    message(FATAL_ERROR "cannot locate mupdf-gl package folder (expected variable mupdf-gl_PACKAGE_FOLDER_${_MGL_BT})")
endif()

# GL header shims for compiling the package's real gl-ui.c in the test:
#
# The freeglut package defines FREEGLUT_GLES, which makes freeglut_std.h take
# its GLES branch: it includes <GLES2/gl2.h> and NOT <GL/gl.h>/<GL/glu.h>.
# gl-ui.c (unpatched functions) still references fixed-function identifiers
# that the pure-ES2 header lacks, and the patched VAO path calls ES3 entry
# points (glGenVertexArrays ...) that gl2.h alone does not declare.
#
# gl_ohos_compat.h (force-included below) supplies both:
#   * <GLES3/gl3.h> for the ES3 declarations used by the retained VAO path
#   * the five fixed-function constants referenced by non-retained functions
#     (ui_begin matrix setup, overlay display lists, glErrorString); standard
#     GL values, and those functions are the subject of the full-viewer
#     follow-up port (they are garbage-collected at link time).
#
# GL/glu.h stub: kept for the non-GLES include branch of freeglut_std.h, which
# does #include <GL/glu.h> unconditionally (the OHOS sysroot has GL/gl.h but
# no GL/glu.h; mupdf-gl has zero glu* references, so the stub is behavior-
# neutral).
set(GLSTUB_DIR "${CMAKE_BINARY_DIR}/glstub")
file(MAKE_DIRECTORY "${GLSTUB_DIR}/GL")
file(WRITE "${GLSTUB_DIR}/GL/glu.h"
  "/* Minimal GL/glu.h stub for OHOS: mupdf-gl does not use GLU; the stub\n"
  "   exists only to satisfy freeglut_std.h's unconditional #include\n"
  "   <GL/glu.h> (the OHOS sysroot ships GL/gl.h but not GL/glu.h). */\n"
  "#ifndef GL_GLU_H_STUB\n"
  "#define GL_GLU_H_STUB\n"
  "#include <GL/gl.h>\n"
  "#endif\n")
file(WRITE "${GLSTUB_DIR}/gl_ohos_compat.h"
  "/* OHOS compile-time compat for mupdf-gl platform/gl/gl-ui.c (test only).\n"
  "   ES3 entry points used by the retained VAO render path: */\n"
  "#include <GLES3/gl3.h>\n"
  "/* Fixed-function constants referenced by non-retained functions\n"
  "   (ui_begin, overlay display lists, glErrorString). Standard GL values;\n"
  "   the GLES2 header does not define them. */\n"
  "#ifndef GL_MODELVIEW\n"
  "#define GL_MODELVIEW 0x1700\n"
  "#endif\n"
  "#ifndef GL_PROJECTION\n"
  "#define GL_PROJECTION 0x1701\n"
  "#endif\n"
  "#ifndef GL_COMPILE\n"
  "#define GL_COMPILE 0x0F00\n"
  "#endif\n"
  "#ifndef GL_STACK_OVERFLOW\n"
  "#define GL_STACK_OVERFLOW 0x0503\n"
  "#endif\n"
  "#ifndef GL_STACK_UNDERFLOW\n"
  "#define GL_STACK_UNDERFLOW 0x0504\n"
  "#endif\n")

# The executable is: this test + the REAL patched gl-ui.c shipped in the
# package (include/mupdf-gl-ohos/gl-ui.c). Compiling the package's own
# adapted source and calling ui_draw_image() is what makes this a
# substantive test of the tested package (R34) rather than a shell.
#
# -ffunction-sections/-fdata-sections + --gc-sections: gl-ui.c contains many
# other ui_* functions that reference MuPDF/GLUT symbols not present in this
# test; only the ui_draw_image closure (ui_draw_image + ui_draw_image_vao +
# ui_ensure_vao, which reference only GL entry points) is retained and
# linked, so no MuPDF core symbols are needed at link time.
add_executable(test_vao
  src/test_vao.c
  "${MUPDFGL_PKGROOT}/include/mupdf-gl-ohos/gl-ui.c")

# Include dirs: the package's adapted GL sources (for #include "gl-app.h")
# plus the GL/glu.h stub dir. NOTE: keep no inline comments inside the
# unclosed command below — CMake 3.16 miscounts ')' inside such comments.
target_include_directories(test_vao PRIVATE
  "${MUPDFGL_PKGROOT}/include/mupdf-gl-ohos"
  "${GLSTUB_DIR}")

# Force-include the compat header before any source file (resolves via the
# GLSTUB_DIR include path). Guarded includes/defines make it harmless for the
# test main too.
target_compile_options(test_vao PRIVATE
  -ffunction-sections -fdata-sections
  -include gl_ohos_compat.h)
target_link_options(test_vao PRIVATE -Wl,--gc-sections)

# Link: the tested package (static core libs — nothing pulled unless
# referenced, but present per the conan test convention), freeglut (headers;
# .so available for any retained GLUT reference), and the OHOS client libs.
#
# IMPORTANT — GLESv3 only, NOT GLESv2: on OHOS, every symbol in
# libGLESv2.so (673 of them) is aliased to a single dispatcher entry that
# does not actually work, while libGLESv3.so's dispatcher (2942 symbols, a
# strict superset of the ES2 core) works (probe-direct-gl.c). Measured in
# this test: with both libs linked, the GL symbols bind to libGLESv2.so
# (first match), glGetString returns NULL, and the render produces nothing.
target_link_libraries(test_vao PRIVATE mupdf-gl::mupdf-gl freeglut::freeglut EGL GLESv3)

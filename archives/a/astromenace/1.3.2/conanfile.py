#!/usr/bin/env python3
"""Conan recipe for AstroMenace 1.3.2 on HarmonyOS PC.

AstroMenace is a hardcore 3D space scroll-shooter with spaceship upgrade
possibilities.
"""

import os, shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.build import can_run


class AstroMenaceConan(ConanFile):
    name = "astromenace"
    version = "1.3.2"
    exports = "gles_compat.h", "gles_compat.cpp"
    description = "Hardcore 3D space scroll-shooter with spaceship upgrade possibilities"
    license = "GPL-3.0"
    homepage = "https://viewizard.com/"
    url = "https://github.com/viewizard/astromenace"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # SDL 1.2 compatibility layer on top of SDL2
        self.requires("sdl12-compat/1.2.68")
        # OpenAL for audio output
        self.requires("openal/1.25.2")
        # Freetype for font rendering
        self.requires("freetype/2.14.3")
        # Ogg/Vorbis for audio decoding
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        # Fontconfig for system font discovery (optional in upstream)
        self.requires("fontconfig/2.18.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # R39: official source URL
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # Point CMake to the OHOS sysroot for FIND_LIBRARY/FIND_PATH
        tc.variables["CMAKE_SYSROOT"] = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
        tc.variables["CMAKE_FIND_ROOT_PATH"] = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        """Apply adaptations for HarmonyOS platform."""
        src = self.source_folder
        # --- ALUT shim ---
        # Upstream uses ALUT (freealut) which is deprecated and not available
        # on OHOS. Provide a minimal replacement that uses OpenAL directly.
        alut_h = os.path.join(src, "AstroMenaceSource", "Core", "Sound", "alut_shim.h")
        with open(alut_h, "w") as f:
            f.write("""#ifndef ALUT_SHIM_H
#define ALUT_SHIM_H

#include <AL/al.h>
#include <AL/alc.h>
#include <stdio.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ALUT_ERROR_NO_ERROR 0
#define ALUT_ERROR_OUT_OF_MEMORY 0x200
#define ALUT_ERROR_INVALID_OPERATION 0x201
#define ALUT_ERROR_NO_CURRENT_CONTEXT 0x202
#define ALUT_ERROR_AL_ERROR_ON_ENTRY 0x203
#define ALUT_ERROR_ALC_ERROR_ON_ENTRY 0x204
#define ALUT_ERROR_GEN_BUFFERS 0x205
#define ALUT_ERROR_BUFFER_DATA 0x206
#define ALUT_ERROR_CLOSE_DEVICE 0x207
#define ALUT_ERROR_CREATE_CONTEXT 0x208
#define ALUT_ERROR_DESTROY_CONTEXT 0x209
#define ALUT_ERROR_MAKE_CONTEXT_CURRENT 0x20A

static ALenum alut_state = ALUT_ERROR_NO_ERROR;
static ALint alut_major = 1;
static ALint alut_minor = 1;

static void alutInitWithoutContext(ALCint *pargc, ALCchar **argv) {
    (void)pargc; (void)argv;
    alut_state = ALUT_ERROR_NO_ERROR;
}

static ALenum alutGetError(void) {
    ALenum e = alut_state;
    alut_state = ALUT_ERROR_NO_ERROR;
    return e;
}

static const ALchar* alutGetErrorString(ALenum error) {
    switch (error) {
        case ALUT_ERROR_NO_ERROR: return "No error";
        case ALUT_ERROR_OUT_OF_MEMORY: return "Out of memory";
        case ALUT_ERROR_INVALID_OPERATION: return "Invalid operation";
        case ALUT_ERROR_NO_CURRENT_CONTEXT: return "No current context";
        case ALUT_ERROR_GEN_BUFFERS: return "Gen buffers failed";
        case ALUT_ERROR_BUFFER_DATA: return "Buffer data failed";
        default: return "Unknown ALUT error";
    }
}

static ALint alutGetMajorVersion(void) { return alut_major; }
static ALint alutGetMinorVersion(void) { return alut_minor; }

static ALuint alutCreateBufferFromFileImage(const ALvoid *data, ALsizei length) {
    ALuint buffer = 0;
    ALenum format = AL_FORMAT_STEREO16;
    ALsizei freq = 44100;
    alGenBuffers(1, &buffer);
    if (alGetError() != AL_NO_ERROR) {
        alut_state = ALUT_ERROR_GEN_BUFFERS;
        return 0;
    }
    // Determine format from first bytes (simple heuristic)
    if (length > 44) {
        const unsigned char *d = (const unsigned char *)data;
        // WAV header: "RIFF"
        if (d[0] == 'R' && d[1] == 'I' && d[2] == 'F' && d[3] == 'F') {
            unsigned short channels = d[22] | (d[23] << 8);
            unsigned short bits = d[34] | (d[35] << 8);
            unsigned int sample_rate = (unsigned int)(d[24] | (d[25] << 8) | (d[26] << 16) | (d[27] << 24));
            freq = (ALsizei)sample_rate;
            if (channels == 1) {
                format = (bits == 8) ? AL_FORMAT_MONO8 : AL_FORMAT_MONO16;
            } else {
                format = (bits == 8) ? AL_FORMAT_STEREO8 : AL_FORMAT_STEREO16;
            }
            // Skip WAV header (44 bytes)
            alBufferData(buffer, format, (const ALvoid*)(d + 44), (ALsizei)(length - 44), freq);
        } else {
            // Assume raw PCM stereo16 at 44100
            alBufferData(buffer, format, data, length, freq);
        }
    } else {
        alBufferData(buffer, format, data, length, freq);
    }
    if (alGetError() != AL_NO_ERROR) {
        alut_state = ALUT_ERROR_BUFFER_DATA;
        alDeleteBuffers(1, &buffer);
        return 0;
    }
    return buffer;
}

static void alutExit(void) {
    alut_state = ALUT_ERROR_NO_ERROR;
}

#ifdef __cplusplus
}
#endif
#endif /* ALUT_SHIM_H */
""")
        # --- GLU shim (gluLookAt) ---
        # --- GLES2 compatibility shim (replaces desktop GL fixed-pipeline) ---
        gles_h_dir = os.path.join(src, "AstroMenaceSource", "Core", "RendererInterface")
        os.makedirs(gles_h_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.recipe_folder, "gles_compat.h"), os.path.join(gles_h_dir, "gles_compat.h"))
        shutil.copy2(os.path.join(self.recipe_folder, "gles_compat.cpp"), os.path.join(gles_h_dir, "gles_compat.cpp"))

        # glu_shim.h is no longer needed — gles_compat.h provides all GLU functions
        glu_h = os.path.join(src, "AstroMenaceSource", "Core", "glu_shim.h")
        with open(glu_h, "w") as f:
            f.write("""#ifndef GLU_SHIM_H
#define GLU_SHIM_H

#include <GL/gl.h>
#include <math.h>
#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

static void gluLookAt(GLdouble eyeX, GLdouble eyeY, GLdouble eyeZ,
                      GLdouble centerX, GLdouble centerY, GLdouble centerZ,
                      GLdouble upX, GLdouble upY, GLdouble upZ) {
    GLdouble forward[3], side[3], up[3];
    GLdouble m[16];
    int i;

    forward[0] = centerX - eyeX;
    forward[1] = centerY - eyeY;
    forward[2] = centerZ - eyeZ;
    GLdouble fwdLen = sqrt(forward[0]*forward[0] + forward[1]*forward[1] + forward[2]*forward[2]);
    if (fwdLen != 0.0) {
        forward[0] /= fwdLen; forward[1] /= fwdLen; forward[2] /= fwdLen;
    }

    up[0] = upX; up[1] = upY; up[2] = upZ;
    GLdouble upLen = sqrt(up[0]*up[0] + up[1]*up[1] + up[2]*up[2]);
    if (upLen != 0.0) {
        up[0] /= upLen; up[1] /= upLen; up[2] /= upLen;
    }

    // side = forward × up
    side[0] = forward[1]*up[2] - forward[2]*up[1];
    side[1] = forward[2]*up[0] - forward[0]*up[2];
    side[2] = forward[0]*up[1] - forward[1]*up[0];
    GLdouble sideLen = sqrt(side[0]*side[0] + side[1]*side[1] + side[2]*side[2]);
    if (sideLen != 0.0) {
        side[0] /= sideLen; side[1] /= sideLen; side[2] /= sideLen;
    }

    // up = side × forward
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

static void gluPerspective(GLdouble fovy, GLdouble aspect,
                           GLdouble zNear, GLdouble zFar) {
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

static const GLubyte* gluErrorString(GLenum error) {
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

static GLint gluScaleImage(GLenum format, GLsizei widthIn, GLsizei heightIn,
                           GLenum typeIn, const void *dataIn,
                           GLsizei widthOut, GLsizei heightOut,
                           GLenum typeOut, void *dataOut) {
    int components = 0;
    switch (format) {
        case GL_ALPHA: case GL_LUMINANCE: components = 1; break;
        case GL_LUMINANCE_ALPHA: components = 2; break;
        case GL_RGB: components = 3; break;
        case GL_RGBA: components = 4; break;
        default: return GL_INVALID_ENUM;
    }
    if (typeIn != GL_UNSIGNED_BYTE || typeOut != GL_UNSIGNED_BYTE) {
        return GL_INVALID_ENUM;
    }
    const unsigned char *src = (const unsigned char *)dataIn;
    unsigned char *dst = (unsigned char *)dataOut;
    int x, y, c;
    for (y = 0; y < heightOut; y++) {
        float fy = (float)y / (float)heightOut;
        int y0 = (int)(fy * (float)heightIn);
        if (y0 >= heightIn) y0 = heightIn - 1;
        int y1 = y0 + 1;
        if (y1 >= heightIn) y1 = y0;
        float wy = fy * (float)heightIn - (float)y0;
        if (wy < 0.0f) wy = 0.0f;
        if (wy > 1.0f) wy = 1.0f;
        for (x = 0; x < widthOut; x++) {
            float fx = (float)x / (float)widthOut;
            int x0 = (int)(fx * (float)widthIn);
            if (x0 >= widthIn) x0 = widthIn - 1;
            int x1 = x0 + 1;
            if (x1 >= widthIn) x1 = x0;
            float wx = fx * (float)widthIn - (float)x0;
            if (wx < 0.0f) wx = 0.0f;
            if (wx > 1.0f) wx = 1.0f;
            for (c = 0; c < components; c++) {
                float v00 = src[(y0*widthIn + x0)*components + c];
                float v10 = src[(y0*widthIn + x1)*components + c];
                float v01 = src[(y1*widthIn + x0)*components + c];
                float v11 = src[(y1*widthIn + x1)*components + c];
                float v = v00*(1.0f-wx)*(1.0f-wy) + v10*wx*(1.0f-wy)
                        + v01*(1.0f-wx)*wy + v11*wx*wy;
                dst[(y*widthOut + x)*components + c] = (unsigned char)(v + 0.5f);
            }
        }
    }
    return 0;
}

static GLint gluBuild2DMipmaps(GLenum target, GLint internalFormat,
                               GLsizei width, GLsizei height,
                               GLenum format, GLenum type,
                               const void *data) {
    GLsizei w = width, h = height;
    int level = 0;
    GLint err;
    void *prevData = NULL;
    while (w >= 1 && h >= 1) {
        void *levelData = NULL;
        if (level == 0) {
            glTexImage2D(target, level, internalFormat, w, h, 0, format, type, data);
        } else {
            // downscale previous level by 2 using gluScaleImage
            levelData = malloc((size_t)w * h * 4);
            if (!levelData) return GL_OUT_OF_MEMORY;
            err = gluScaleImage(format, w*2, h*2, type,
                                prevData, w, h, type, levelData);
            if (err != 0) { free(levelData); levelData = NULL; prevData = NULL; return err; }
            glTexImage2D(target, level, internalFormat, w, h, 0, format, type, levelData);
            free(levelData);
            levelData = NULL;
        }
        GLenum glerr = glGetError();
        if (glerr != GL_NO_ERROR) return glerr;
        if (w == 1 && h == 1) break;
        // keep a copy of the current level for next iteration's source
        if (w / 2 >= 1) {
            levelData = malloc((size_t)w * h * 4);
            if (!levelData) return GL_OUT_OF_MEMORY;
            glGetTexImage(target, level, format, type, levelData);
            if (prevData) free(prevData);
            prevData = levelData;
            w = w / 2; h = h / 2; level++;
        } else {
            w = 1; h = 1; level++;
        }
    }
    if (prevData) { free(prevData); prevData = NULL; }
    return 0;
}

#ifdef __cplusplus
}
#endif
#endif /* GLU_SHIM_H */
""")

        # --- Patch CMakeLists.txt ---
        cmake_path = os.path.join(src, "CMakeLists.txt")
        with open(cmake_path, "r") as f:
            cmake_content = f.read()

        # 1. Replace sdl-config with CMakeDeps target (sdl12-compat provides SDL::SDL)
        cmake_content = cmake_content.replace(
            "EXEC_PROGRAM(${SDL_CONFIG} ARGS \"--cflags\" OUTPUT_VARIABLE SDL_CFLAGS)\nADD_DEFINITIONS(${SDL_CFLAGS})\nEXEC_PROGRAM(${SDL_CONFIG} ARGS \"--libs\" OUTPUT_VARIABLE SDL_LIBS)",
            "FIND_PACKAGE(SDL REQUIRED)\nSET(SDL_LIBS SDL::SDL)"
        )

        # 1.1. Bump minimum CMake version (upstream requires 2.4; CMake >= 3.5
        # removed compatibility with <3.5 projects)
        cmake_content = cmake_content.replace(
            "CMAKE_MINIMUM_REQUIRED(VERSION 2.4)",
            "CMAKE_MINIMUM_REQUIRED(VERSION 3.15)"
        )

        # 2. Remove FIND_PACKAGE(X11 REQUIRED) - OHOS has no X11
        cmake_content = cmake_content.replace(
            "IF (NOT APPLE)\nFIND_PACKAGE(X11 REQUIRED)\nSET(ALL_LIBRARIES ${ALL_LIBRARIES} ${X11_LIBRARIES})\nENDIF (NOT APPLE)",
            ""
        )

        # 2.5. Replace FIND_PACKAGE(OpenGL) with direct GLESv2/EGL link (OHOS has libGLESv2/libEGL, no GLX)
        old_opengl = """FIND_PACKAGE(OpenGL REQUIRED)
IF(OPENGL_FOUND)
	INCLUDE_DIRECTORIES(${OPENGL_INCLUDE_DIR})
	SET(ALL_LIBRARIES ${ALL_LIBRARIES} ${OPENGL_gl_LIBRARY})
ELSE(OPENGL_FOUND)
	MESSAGE(FATAL_ERROR \"OpenGL not found\")
ENDIF(OPENGL_FOUND)"""
        new_opengl = """# OHOS: use GLESv2 + EGL (no desktop GL/GLX on OHOS); gles_compat.h shims the fixed pipeline
FIND_LIBRARY(OPENGL_gl_LIBRARY GLESv2
    PATHS "${CMAKE_SYSROOT}/usr/lib/aarch64-linux-ohos"
    NO_DEFAULT_PATH)
FIND_LIBRARY(OPENGL_egl_LIBRARY EGL
    PATHS "${CMAKE_SYSROOT}/usr/lib/aarch64-linux-ohos"
    NO_DEFAULT_PATH)
IF(OPENGL_gl_LIBRARY)
	MESSAGE(STATUS \"Found GLESv2: ${OPENGL_gl_LIBRARY}\")
	SET(ALL_LIBRARIES ${ALL_LIBRARIES} ${OPENGL_gl_LIBRARY} ${OPENGL_egl_LIBRARY})
ELSE(OPENGL_gl_LIBRARY)
	MESSAGE(FATAL_ERROR \"OpenGL ES v2 not found on OHOS\")
ENDIF(OPENGL_gl_LIBRARY)
IF(OPENGL_egl_LIBRARY)
	MESSAGE(STATUS \"Found EGL: ${OPENGL_egl_LIBRARY}\")
ELSE(OPENGL_egl_LIBRARY)
	MESSAGE(FATAL_ERROR \"EGL not found on OHOS\")
ENDIF(OPENGL_egl_LIBRARY)
FIND_PATH(OPENGL_INCLUDE_DIR GLES2/gl2.h
    PATHS "${CMAKE_SYSROOT}/usr/include"
    NO_DEFAULT_PATH)
IF(OPENGL_INCLUDE_DIR)
	INCLUDE_DIRECTORIES(${OPENGL_INCLUDE_DIR})
ENDIF(OPENGL_INCLUDE_DIR)"""
        cmake_content = cmake_content.replace(old_opengl, new_opengl)

        # 2.6. Ensure gles_compat.cpp is compiled (upstream uses GLOB_RECURSE so it is
        # already picked up; make the GLES2 shim dependency explicit)
        cmake_content = cmake_content.replace(
            "FILE(GLOB_RECURSE astromenace_SRCS AstroMenaceSource/*.cpp)",
            "FILE(GLOB_RECURSE astromenace_SRCS AstroMenaceSource/*.cpp)\n"
            "SET(astromenace_SRCS ${astromenace_SRCS} AstroMenaceSource/Core/RendererInterface/gles_compat.cpp)"
        )

        # 2.5. Fix OpenAL: use CMakeDeps target instead of legacy OPENAL_LIBRARY variable
        cmake_content = cmake_content.replace(
            "SET(ALL_LIBRARIES ${ALL_LIBRARIES} ${OPENAL_LIBRARY})",
            "SET(ALL_LIBRARIES ${ALL_LIBRARIES} OpenAL::OpenAL)"
        )

        # 3. Remove ALUT from required deps, add shim include
        # Replace the ALUT FIND_LIBRARY block with shim
        old_alut = """FIND_LIBRARY(ALUT_LIBRARY alut)
IF(ALUT_LIBRARY)
	MESSAGE(STATUS \"Found alut: ${ALUT_LIBRARY}\")
	SET(ALL_LIBRARIES ${ALL_LIBRARIES} ${ALUT_LIBRARY})
ELSE(ALUT_LIBRARY)
	MESSAGE(FATAL_ERROR \"alut not found\")
ENDIF(ALUT_LIBRARY)
FIND_PATH(ALUT_INCLUDE_DIR alut.h
 	HINTS
	$ENV{ALUTDIR}
	$ENV{ALUT_PATH}
 	PATHS
 	PATH_SUFFIXES include/AL include)
IF(ALUT_INCLUDE_DIR)
	MESSAGE(STATUS \"Found alut headers: ${ALUT_INCLUDE_DIR}\")
	INCLUDE_DIRECTORIES(${ALUT_INCLUDE_DIR})
ELSE(ALUT_INCLUDE_DIR)
	MESSAGE(FATAL_ERROR \"alut headers not found\")
ENDIF(ALUT_INCLUDE_DIR)"""
        new_alut = """# ALUT (freealut) not available on OHOS; using local shim
INCLUDE_DIRECTORIES(${CMAKE_SOURCE_DIR}/AstroMenaceSource/Core/Sound)"""
        cmake_content = cmake_content.replace(old_alut, new_alut)

        # 4. Make GLU optional (not available on OHOS without glu.h)
        old_glu = """IF (NOT APPLE)
FIND_LIBRARY(GLU_LIBRARY GLU)
IF(GLU_LIBRARY)
	MESSAGE(STATUS \"Found GLU: ${GLU_LIBRARY}\")
	SET(ALL_LIBRARIES ${ALL_LIBRARIES} ${GLU_LIBRARY})
ELSE(GLU_LIBRARY)
	MESSAGE(FATAL_ERROR \"GLU not found\")
ENDIF(GLU_LIBRARY)
FIND_PATH(GLU_INCLUDE_DIR GL/glu.h
 	HINTS
	$ENV{GLUTDIR}
	$ENV{GLU_PATH}
 	PATHS
 	PATH_SUFFIXES include/GL include)
IF(GLU_INCLUDE_DIR)
	MESSAGE(STATUS \"Found GLU headers: ${GLU_INCLUDE_DIR}\")
	INCLUDE_DIRECTORIES(${GLU_INCLUDE_DIR})
ELSE(GLU_INCLUDE_DIR)
	MESSAGE(FATAL_ERROR \"GLU headers not found\")
ENDIF(GLU_INCLUDE_DIR)
ENDIF (NOT APPLE)"""
        new_glu = """# GLU: use local shim on OHOS (gluLookAt implemented via math)
INCLUDE_DIRECTORIES(${CMAKE_SOURCE_DIR}/AstroMenaceSource/Core)"""
        cmake_content = cmake_content.replace(old_glu, new_glu)

        # 5. Wrap X11-specific code in SDL_VIDEO_DRIVER_X11 guard (already done)
        # 6. Remove Xinerama detection (no X11 on OHOS)
        # Keep the cmake var undef so xinerama stays disabled

        # 7. Wrap X11-dependent window move code
        # Already behind #ifdef SDL_VIDEO_DRIVER_X11 in OGL_Main.cpp

        # 8. ShadowMap.cpp: no separate glu_shim.h include needed — Base.h pulls in
        # RendererInterface/gles_compat.h which provides the GLU shims.

        # 9. Replace #include <AL/alut.h> with the shim in Sound.h
        sound_h_path = os.path.join(src, "AstroMenaceSource", "Core", "Sound", "Sound.h")
        with open(sound_h_path, "r") as f:
            sound_h = f.read()
        sound_h = sound_h.replace(
            '#include "AL/alut.h"',
            '#include "alut_shim.h"'
        )
        with open(sound_h_path, "w") as f:
            f.write(sound_h)

        # 10. Remove #include <GL/glu.h> from Base.h, replace GL/gl.h with gles_compat.h
        base_path = os.path.join(src, "AstroMenaceSource", "Core", "Base.h")
        with open(base_path) as f: base_content = f.read()
        base_content = base_content.replace('#include <GL/glu.h>', '')
        base_content = base_content.replace('#include <OpenGL/glu.h>', '')
        with open(base_path, "w") as f: f.write(base_content)
        base_h_path = os.path.join(src, "AstroMenaceSource", "Core", "Base.h")
        with open(base_h_path, "r") as f:
            base_h = f.read()
        # Remove the macOS glu include
        base_h = base_h.replace(
            '#include <OpenGL/glu.h>\t// Header File For The GLu Library\n',
            ''
        )
        # Replace desktop GL/gl.h with GLES2 compatibility header
        base_h = base_h.replace(
            '#include <GL/gl.h>\t// Header File For The OpenGL Library\n',
            '#include "RendererInterface/gles_compat.h"\n'
        )
        # Fix SDL include: sdl12-compat exposes headers at include/SDL/ so
        # #include "SDL/SDL.h" would need include/SDL/SDL/SDL.h — use SDL.h directly
        base_h = base_h.replace('#include "SDL/SDL.h"', '#include "SDL.h"')
        base_h = base_h.replace('#include "SDL/SDL_thread.h"', '#include "SDL_thread.h"')
        base_h = base_h.replace('#include "SDL/SDL_syswm.h"', '#include "SDL_syswm.h"')
        base_h = base_h.replace('#include "SDL/SDL_endian.h"', '#include "SDL_endian.h"')
        with open(base_h_path, "w") as f:
            f.write(base_h)

        # 11. Handle fontconfig detection: force definition on OHOS
        # Add fontconfig flag to CMakeLists
        cmake_content = cmake_content.replace(
            'IF(FONTCONFIG_LIBRARY AND FONTCONFIG_INCLUDE_DIR_fontconfig)\n\tADD_DEFINITIONS(-Dfontconfig_detected_by_cmake)\nENDIF(FONTCONFIG_LIBRARY AND FONTCONFIG_INCLUDE_DIR_fontconfig)',
            'ADD_DEFINITIONS(-Dfontconfig_detected_by_cmake)'
        )
        # 12. GLext.h: guard Windows-only include for non-Windows (OHOS) builds
        glext_path = os.path.join(src, "AstroMenaceSource", "Core", "RendererInterface", "GLext.h")
        with open(glext_path) as f:
            glext_content = f.read()
        glext_content = glext_content.replace(
            '#include <windows.h>',
            '#if defined(_WIN32)\n#include <windows.h>\n#endif'
        )
        with open(glext_path, "w") as f:
            f.write(glext_content)

        with open(cmake_path, "w") as f:
            f.write(cmake_content)

    def build(self):
        apply_conandata_patches(self)
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "AstroMenace",
             src=os.path.join(self.source_folder),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "gamedata.vfs",
             src=os.path.join(self.source_folder),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
// gles_immediate.h — Minimal desktop-GL immediate-mode shim for fceux on OHOS.
//
// fceux src/drivers/Qt/ConsoleViewerGL.cpp uses the desktop fixed pipeline
// (glMatrixMode/glLoadIdentity/glOrtho + glBegin(GL_QUADS)/glTexCoord2f/
// glVertex2f/glEnd) to draw one textured quad per frame. OHOS only ships
// GLESv2+EGL, which has no matrix stack and no immediate mode, so the link
// fails with `undefined symbol: glLoadIdentity ... glEnd` even though every
// object file compiles.
//
// This shim implements exactly that used subset on top of GLES2: glOrtho
// records the projection bounds, glBegin/glTexCoord2f/glVertex2f buffer one
// quad, and glEnd() draws it through a tiny texture-sampling GLSL program
// (NDC is derived from the recorded ortho bounds, so the mapping honors the
// caller's glOrtho(0, rw, 0, rh) instead of hardcoding dimensions).
// The SDL and QPainter video drivers are untouched; this only makes the
// default OpenGL driver link and render on OHOS.
//
// Same license as fceux (GPL-2.0-or-later).
#ifndef FCEUX_GLES_IMMEDIATE_H
#define FCEUX_GLES_IMMEDIATE_H

#endif // FCEUX_GLES_IMMEDIATE_H

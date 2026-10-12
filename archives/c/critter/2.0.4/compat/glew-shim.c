/*
 * Minimal GLEW compatibility implementation for OpenHarmony PC (OHOS).
 *
 * gl4es resolves GL symbols at runtime through libGL.so; GLEW's own job on
 * this platform is reduced to reporting a version string, so glewInit()
 * succeeds unconditionally and glewGetString() returns a static answer.
 */
#include <GL/glew.h>

GLboolean glewExperimental = 0;

GLenum glewInit(void)
{
    return GLEW_OK;
}

static const GLubyte s_glew_version[] = "1.13.0";

const GLubyte *glewGetString(GLenum name)
{
    switch (name) {
    case GLEW_VERSION:
        return s_glew_version;
    default:
        return (const GLubyte *)"";
    }
}

/* GL_KHR_debug is unavailable in gl4es, so registering a debug callback is a
 * no-op.  Critter only uses it for best-effort diagnostic logging. */
void GLAPIENTRY glDebugMessageCallback(GLDEBUGPROC callback, const void *userParam)
{
    (void)callback;
    (void)userParam;
}

/* gl4es exposes none of the following three GL 3.x entry points.  They reach
 * the linker only through mooflu.common's gl3 wrappers
 * (Buffer::unbind(target, index), Program::setParameter,
 * Program::bindFragDataLocation), none of which Critter's game code calls, so
 * they are kept as documented no-ops rather than omitting the symbols and
 * breaking the link. */
void GLAPIENTRY glBindBufferBase(GLenum target, GLuint index, GLuint buffer)
{
    (void)target;
    (void)index;
    (void)buffer;
}

void GLAPIENTRY glProgramParameteri(GLuint program, GLenum pname, GLint value)
{
    (void)program;
    (void)pname;
    (void)value;
}

void GLAPIENTRY glBindFragDataLocation(GLuint program, GLuint color,
                                       const GLchar *name)
{
    (void)program;
    (void)color;
    (void)name;
}

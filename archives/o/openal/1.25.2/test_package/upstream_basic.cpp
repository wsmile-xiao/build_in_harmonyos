#include <AL/al.h>

int main()
{
    ALuint source = 0;
    ALuint buffer = 0;
    ALfloat offset = 0.0f;
    ALenum state = AL_INITIAL;
    const ALenum initial_error = alGetError();

    (void)source;
    (void)buffer;
    (void)offset;
    (void)state;
    return initial_error == AL_NO_ERROR || initial_error == AL_INVALID_OPERATION ? 0 : 1;
}

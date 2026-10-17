#include <AL/al.h>
#include <AL/alc.h>
#include <stdlib.h>

int main(void)
{
    static const short samples[8] = {0, 512, -512, 1024, -1024, 256, -256, 0};
    ALCdevice *device;
    ALCcontext *context;
    ALuint buffer = 0;
    ALuint source = 0;
    int result = 0;

    if (setenv("ALSOFT_DRIVERS", "null", 1) != 0) {
        return 1;
    }
    device = alcOpenDevice(0);
    if (device == 0) {
        return 1;
    }
    context = alcCreateContext(device, 0);
    if (context == 0 || alcMakeContextCurrent(context) == ALC_FALSE) {
        if (context != 0) {
            alcDestroyContext(context);
        }
        alcCloseDevice(device);
        return 2;
    }

    alGenBuffers(1, &buffer);
    alBufferData(buffer, AL_FORMAT_MONO16, samples, sizeof(samples), 8000);
    alGenSources(1, &source);
    alSourcei(source, AL_BUFFER, (ALint)buffer);
    if (alGetError() != AL_NO_ERROR) {
        result = 3;
    }

    if (source != 0) {
        alDeleteSources(1, &source);
    }
    if (buffer != 0) {
        alDeleteBuffers(1, &buffer);
    }
    alcMakeContextCurrent(0);
    alcDestroyContext(context);
    if (alcCloseDevice(device) == ALC_FALSE && result == 0) {
        result = 4;
    }
    return result;
}

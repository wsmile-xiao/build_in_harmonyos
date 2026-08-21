#include <portaudio.h>

#include <stdio.h>

int main(void) {
    const PaVersionInfo *version = Pa_GetVersionInfo();
    PaError result;
    PaHostApiIndex host_api_count;
    PaDeviceIndex device_count;
    PaDeviceIndex default_input;
    PaDeviceIndex default_output;
    const char *error_text;

    if (version == NULL || version->versionMajor != 19 ||
        version->versionMinor != 7 || version->versionSubMinor != 0 ||
        version->versionText == NULL || version->versionText[0] == '\0') {
        fprintf(stderr, "unexpected PortAudio version information\n");
        return 1;
    }

    result = Pa_Initialize();
    if (result != paNoError) {
        fprintf(stderr, "Pa_Initialize failed: %s\n", Pa_GetErrorText(result));
        return 1;
    }

    host_api_count = Pa_GetHostApiCount();
    device_count = Pa_GetDeviceCount();
    default_input = Pa_GetDefaultInputDevice();
    default_output = Pa_GetDefaultOutputDevice();
    error_text = Pa_GetErrorText(paInvalidDevice);

    if (host_api_count < 0 || device_count < 0 ||
        (default_input != paNoDevice && default_input >= device_count) ||
        (default_output != paNoDevice && default_output >= device_count) ||
        error_text == NULL || error_text[0] == '\0') {
        fprintf(stderr, "PortAudio API consistency check failed\n");
        Pa_Terminate();
        return 1;
    }

    result = Pa_Terminate();
    if (result != paNoError) {
        fprintf(stderr, "Pa_Terminate failed: %s\n", Pa_GetErrorText(result));
        return 1;
    }

    printf(
        "PASS portaudio %s host_apis=%d devices=%d\n",
        version->versionText,
        (int)host_api_count,
        (int)device_count
    );
    return 0;
}

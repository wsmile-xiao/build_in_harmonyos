/* HarmonyOS-specific SDL_image consumer test.
 *
 * This executable validates the headless OHOS runtime path used by the Conan
 * test package: SDL 1.2 must initialize without a video backend, SDL_image
 * must expose the packaged version, and the PNG codec must initialize under
 * the OHOS runtime environment.
 */
#include <SDL/SDL.h>
#include <SDL/SDL_image.h>

#if !defined(__OHOS__)
#error "harmonyos_specific_test must be compiled for HarmonyOS"
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    printf("PASS: %s\n", message);
    return 0;
}

int main(void)
{
    const SDL_version *sdl_version;
    const SDL_version *image_version;
    const char *video_driver;
    int failures = 0;
    int image_flags;

    failures += check(SDL_Init(0) == 0,
                      "SDL 1.2 initializes without a video subsystem on OHOS");
    sdl_version = SDL_Linked_Version();
    image_version = IMG_Linked_Version();
    failures += check(sdl_version != NULL && image_version != NULL,
                      "SDL and SDL_image expose linked version structures");
    failures += check(image_version != NULL && image_version->major == 1 &&
                          image_version->minor == 2,
                      "SDL_image linked version is the SDL 1.2 ABI");

    video_driver = getenv("SDL_VIDEODRIVER");
    failures += check(video_driver != NULL && strcmp(video_driver, "dummy") == 0,
                      "OHOS consumer runs with the headless dummy video driver");

    image_flags = IMG_Init(IMG_INIT_PNG);
    failures += check((image_flags & IMG_INIT_PNG) != 0,
                      "SDL_image PNG codec initializes in the OHOS consumer");
    IMG_Quit();
    SDL_Quit();

    if (failures != 0) {
        fprintf(stderr, "%d HarmonyOS-specific checks failed\n", failures);
        return 1;
    }
    printf("ALL HARMONYOS-SPECIFIC CHECKS PASSED\n");
    return 0;
}

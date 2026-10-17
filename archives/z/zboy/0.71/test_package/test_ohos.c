#include <stdio.h>

#include <SDL2/SDL.h>

#if !defined(__OHOS__)
#error "The HarmonyOS SDL integration test must target OHOS."
#endif

int main(void)
{
    const int width = 160;
    const int height = 144;
    Uint16 pixels[160 * 144];
    SDL_Window *window = NULL;
    SDL_Renderer *renderer = NULL;
    SDL_Texture *texture = NULL;
    int result = 1;

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init(SDL_INIT_VIDEO) failed: %s\n", SDL_GetError());
        return 1;
    }

    window = SDL_CreateWindow("zBoy HarmonyOS SDL test",
                              SDL_WINDOWPOS_UNDEFINED,
                              SDL_WINDOWPOS_UNDEFINED,
                              width,
                              height,
                              SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    if (window == NULL) {
        fprintf(stderr, "SDL_CreateWindow failed: %s\n", SDL_GetError());
        goto cleanup;
    }

    renderer = SDL_CreateRenderer(window, -1, 0);
    if (renderer == NULL) {
        fprintf(stderr, "SDL_CreateRenderer failed: %s\n", SDL_GetError());
        goto cleanup;
    }

    if (SDL_RenderSetLogicalSize(renderer, width, height) != 0) {
        fprintf(stderr, "SDL_RenderSetLogicalSize failed: %s\n", SDL_GetError());
        goto cleanup;
    }

    texture = SDL_CreateTexture(renderer,
                                SDL_PIXELFORMAT_RGB565,
                                SDL_TEXTUREACCESS_STREAMING,
                                width,
                                height);
    if (texture == NULL) {
        fprintf(stderr, "SDL_CreateTexture failed: %s\n", SDL_GetError());
        goto cleanup;
    }

    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            pixels[y * width + x] = (Uint16)(((x >> 3) << 11) |
                                              ((y >> 2) << 5) |
                                              ((x + y) >> 3));
        }
    }

    if (SDL_UpdateTexture(texture, NULL, pixels, width * (int)sizeof(Uint16)) != 0) {
        fprintf(stderr, "SDL_UpdateTexture failed: %s\n", SDL_GetError());
        goto cleanup;
    }
    if (SDL_RenderClear(renderer) != 0 ||
        SDL_RenderCopy(renderer, texture, NULL, NULL) != 0) {
        fprintf(stderr, "SDL render setup failed: %s\n", SDL_GetError());
        goto cleanup;
    }
    SDL_RenderPresent(renderer);
    puts("OHOS SDL video/window/renderer/RGB565 frame test passed.");
    result = 0;

cleanup:
    if (texture != NULL) SDL_DestroyTexture(texture);
    if (renderer != NULL) SDL_DestroyRenderer(renderer);
    if (window != NULL) SDL_DestroyWindow(window);
    SDL_Quit();
    return result;
}

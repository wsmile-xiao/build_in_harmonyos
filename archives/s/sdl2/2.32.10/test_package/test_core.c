#include <stdio.h>
#include <stdlib.h>

#include <SDL2/SDL.h>
#include <SDL2/SDL_test.h>

static int fail(const char *label)
{
    fprintf(stderr, "SDL2_CORE_FAIL assertion=%s error=%s\n", label,
            SDL_GetError());
    return 1;
}

#define CHECK(expr, label)        \
    do {                          \
        if (!(expr)) {            \
            return fail(label);   \
        }                         \
        ++checks;                 \
    } while (0)

int main(void)
{
    SDL_version compiled;
    SDL_version linked;
    Uint64 ticks_before;
    Uint64 ticks_after;
    Uint64 counter_before;
    Uint64 counter_after;
    unsigned char *memory;
    char *run_seed;
    int checks = 0;

    SDL_VERSION(&compiled);
    SDL_GetVersion(&linked);
    CHECK(compiled.major == 2 && compiled.minor == 32 && compiled.patch == 10,
          "compiled_version");
    CHECK(linked.major == 2 && linked.minor == 32 && linked.patch == 10,
          "linked_version");
    CHECK(compiled.major == linked.major && compiled.minor == linked.minor &&
              compiled.patch == linked.patch,
          "header_library_match");
    CHECK(SDL_GetRevision() != NULL && SDL_GetRevision()[0] != '\0',
          "revision_nonempty");
    CHECK(SDL_GetPlatform() != NULL && SDL_GetPlatform()[0] != '\0',
          "platform_nonempty");
    CHECK(SDL_Init(0) == 0, "init_zero");
    CHECK(SDL_WasInit(0) == 0, "no_subsystem_started");
    CHECK(SDL_GetCPUCount() > 0, "cpu_count");
    CHECK(SDL_GetSystemRAM() >= 0, "system_ram_query");
    CHECK(SDL_GetPerformanceFrequency() > 0, "performance_frequency");

    counter_before = SDL_GetPerformanceCounter();
    ticks_before = SDL_GetTicks64();
    SDL_Delay(2);
    counter_after = SDL_GetPerformanceCounter();
    ticks_after = SDL_GetTicks64();
    CHECK(counter_after >= counter_before, "performance_counter_monotonic");
    CHECK(ticks_after >= ticks_before, "ticks_monotonic");

    memory = (unsigned char *)SDL_malloc(32);
    CHECK(memory != NULL, "allocator");
    SDL_memset(memory, 0x5a, 32);
    CHECK(memory[0] == 0x5a, "memset_first_byte");
    CHECK(memory[31] == 0x5a, "memset_last_byte");
    SDL_free(memory);

    run_seed = SDLTest_GenerateRunSeed(8);
    CHECK(run_seed != NULL && SDL_strlen(run_seed) == 8,
          "sdl2test_run_seed");
    SDL_free(run_seed);

    SDL_Quit();
    CHECK(SDL_WasInit(0) == 0, "quit_clean");
    if (checks != 17) {
        return fail("assertion_count");
    }
    printf("SDL2_CORE_PASS assertions=%d\n", checks);
    return 0;
}

#include <stdio.h>
#include <SDL.h>
#include <SDL_mixer.h>

int main(void) {
    int flags = MIX_INIT_MP3;
    int inited = Mix_Init(flags);
    if ((inited & flags) != flags) {
        printf("Mix_Init failed (inited=%d, want=%d)\n", inited, flags);
        return 1;
    }
    /* 无音频设备环境只验证 API 可达与库可链接 */
    Mix_Quit();
    printf("test sdl2-mixer 2.8.2: OK\n");
    return 0;
}

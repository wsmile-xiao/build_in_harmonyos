#include <allegro5/allegro.h>
#include <allegro5/allegro_color.h>
#include <allegro5/allegro_memfile.h>
#include <allegro5/allegro_primitives.h>
#include <allegro5/allegro_font.h>
#include <allegro5/allegro_image.h>
#include <stdio.h>
#include <stdlib.h>

#define CHECK(expr)                                    \
    do {                                               \
        if (!(expr)) {                                 \
            fprintf(stderr, "FAIL: %s:%d: %s\n",       \
                    __FILE__, __LINE__, #expr);         \
            exit(1);                                   \
        }                                              \
    } while (0)

int main(void)
{
    /* 1. Version macros */
    CHECK(ALLEGRO_VERSION == 5);
    CHECK(ALLEGRO_SUB_VERSION == 2);
    CHECK(ALLEGRO_WIP_VERSION == 11);
    printf("PASS: version macros = %d.%d.%d\n",
           ALLEGRO_VERSION, ALLEGRO_SUB_VERSION, ALLEGRO_WIP_VERSION);

    /* 2. Version string */
    printf("PASS: version string = %s\n", ALLEGRO_VERSION_STR);

    /* 3. Date macro */
    CHECK(ALLEGRO_DATE == 20260208);
    printf("PASS: date = %d\n", ALLEGRO_DATE);

    /* 4. Version int and API function */
    CHECK(ALLEGRO_VERSION_INT != 0);
    CHECK(al_get_allegro_version() == ALLEGRO_VERSION_INT);
    printf("PASS: al_get_allegro_version() = 0x%08x\n", al_get_allegro_version());

    /* 5. System ID constants exist (compile-time check) */
    CHECK(ALLEGRO_SYSTEM_ID_XGLX == AL_ID('X', 'G', 'L', 'X'));
    CHECK(ALLEGRO_SYSTEM_ID_ANDROID == AL_ID('A', 'N', 'D', 'R'));
    CHECK(ALLEGRO_SYSTEM_ID_RASPBERRYPI == AL_ID('R', 'A', 'S', 'P'));
    printf("PASS: system ID constants exist\n");

    /* 6. Basic type sizes > 0 */
    CHECK(sizeof(ALLEGRO_BITMAP *) > 0);
    CHECK(sizeof(ALLEGRO_DISPLAY *) > 0);
    CHECK(sizeof(ALLEGRO_COLOR) > 0);
    printf("PASS: basic types exist (ALLEGRO_COLOR size=%zu)\n",
           sizeof(ALLEGRO_COLOR));

    /* 7. Addon init function pointers (compile-time check, no display needed) */
    {
        bool (*init_image)(void) = al_init_image_addon;
        bool (*init_font)(void) = al_init_font_addon;
        bool (*init_prim)(void) = al_init_primitives_addon;
        CHECK(init_image != NULL);
        CHECK(init_font != NULL);
        CHECK(init_prim != NULL);
        (void)init_image; (void)init_font; (void)init_prim;
    }
    printf("PASS: addon init function pointers exist (image/font/primitives)\n");

    /* 8. Color addon types */
    CHECK(sizeof(ALLEGRO_COLOR) == 16);   /* 4 floats: r, g, b, a */
    printf("PASS: ALLEGRO_COLOR size correct\n");

    /* 9. Bitmap flags exist */
    CHECK(ALLEGRO_MEMORY_BITMAP == 1);
    printf("PASS: ALLEGRO_MEMORY_BITMAP constant exists\n");

    /* 10. Primitives types exist */
    CHECK(ALLEGRO_LINE_JOIN_NONE == 0);
    printf("PASS: primitives types exist\n");

    printf("\nAll tests passed!\n");
    return 0;
}

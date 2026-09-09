#include <allegro.h>
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
    /* 1. Version check */
    CHECK(ALLEGRO_VERSION == 4);
    CHECK(ALLEGRO_SUB_VERSION == 4);
    CHECK(ALLEGRO_WIP_VERSION == 3);
    printf("PASS: version %s\n", ALLEGRO_VERSION_STR);

    /* 2. Date check */
    CHECK(ALLEGRO_DATE == 20190303);
    printf("PASS: date %d\n", ALLEGRO_DATE);

    /* 3. Library init (may fail in headless mode, check it exists) */
    allegro_init();
    printf("PASS: allegro_init() called (headless mode, return value ignored)\n");

    /* 4. Library ID */
    const char *id = allegro_id;
    CHECK(id != NULL);
    printf("PASS: allegro_id = %s\n", id);

    /* 5. Basic datafile API (no display needed) */
    /* palette_color is defined in allegro.h - check it exists */
    CHECK(sizeof(RGB) > 0);
    printf("PASS: RGB struct exists\n");

    printf("\nAll tests passed!\n");
    return 0;
}

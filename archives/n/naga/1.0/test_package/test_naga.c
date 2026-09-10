/* test_package/test_naga.c — naga game-logic API test (12 assertions).
 *
 * Links against the installed libnaga.a (engine/naga/utils/keypress units,
 * all curses-free) and exercises movement, screen wrap-around, food,
 * collision and keypress handling without initializing curses, so it runs
 * in a non-interactive CI environment. Each CHECK prints one TAP-style
 * "ok"/"not ok" line; the final HMBS_TEST_PACKAGE_RESULT marker carries
 * the real executed/passed counts produced by this run.
 */
#include <stdio.h>
#include <stdlib.h>

#include "utils.h"
#include "naga.h"
#include "engine.h"
#include "keypress.h"
#include "config.h"

/* Globals owned by the game (mirrors src/main.c). */
struct naga_state the_naga;
uint16_t current_score;
c_bool game_on;
struct point live_food;
uint16_t screen_width;
uint16_t screen_height;

static int total = 0;
static int passed = 0;

#define CHECK(cond, desc) do { \
    total++; \
    if (cond) { passed++; printf("ok %d - %s\n", total, desc); } \
    else { printf("not ok %d - %s\n", total, desc); } \
} while (0)

static int list_len(void) {
    int n = 0;
    struct naga_part *p = the_naga.head;
    while (p != NULL) {
        n++;
        p = p->next;
    }
    return n;
}

static void free_list(void) {
    struct naga_part *p = the_naga.head;
    while (p != NULL) {
        struct naga_part *next = p->next;
        free(p);
        p = next;
    }
    the_naga.head = NULL;
}

static void fresh_world(void) {
    free_list();
    screen_width = 80;
    screen_height = 24;
    game_on = True;
    current_score = 0;
    init_naga();
}

int main(void) {
    /* 1-2: initial state on an 80x24 screen. */
    fresh_world();
    CHECK(the_naga.head->pos.x == 40 && the_naga.head->pos.y == 12,
          "init_naga centers head at (40,12)");
    CHECK(list_len() == NAGA_INITIAL_LENGTH,
          "init_naga builds a 17-part snake");

    /* 3-5: cardinal movement. */
    the_naga.head->pos.x = 40;
    the_naga.head->pos.y = 12;
    update_head(the_naga.head, EAST);
    CHECK(the_naga.head->pos.x == 41 && the_naga.head->pos.y == 12,
          "update_head EAST steps +1 in x");
    update_head(the_naga.head, WEST);
    CHECK(the_naga.head->pos.x == 40 && the_naga.head->pos.y == 12,
          "update_head WEST steps -1 in x");
    the_naga.head->pos.x = 40;
    the_naga.head->pos.y = 12;
    update_head(the_naga.head, NORTH);
    CHECK(the_naga.head->pos.x == 40 && the_naga.head->pos.y == 11,
          "update_head NORTH steps -1 in y");

    /* 6-7: screen wrap-around. */
    the_naga.head->pos.x = 79;
    the_naga.head->pos.y = 12;
    update_head(the_naga.head, EAST);
    CHECK(the_naga.head->pos.x == 1,
          "update_head EAST wraps 79 -> 1");
    the_naga.head->pos.x = 40;
    the_naga.head->pos.y = 23;
    update_head(the_naga.head, SOUTH);
    CHECK(the_naga.head->pos.y == 1,
          "update_head SOUTH wraps 23 -> 1");

    /* 8-9: eating food grows, missing food keeps the length. */
    fresh_world();
    {
        int before = list_len();
        struct point on_head;
        struct point elsewhere;
        c_bool ate;
        on_head.x = the_naga.head->pos.x;
        on_head.y = the_naga.head->pos.y;
        ate = eat_food(&the_naga.head, on_head);
        CHECK(ate == True && list_len() == before + 1,
              "eat_food on the head returns True and grows the snake");
        before = list_len();
        elsewhere.x = 5;
        elsewhere.y = 5;
        if (elsewhere.x == the_naga.head->pos.x &&
            elsewhere.y == the_naga.head->pos.y) {
            elsewhere.x = 6;
        }
        ate = eat_food(&the_naga.head, elsewhere);
        CHECK(ate == False && list_len() == before,
              "eat_food off the head returns False and keeps the length");
    }

    /* 10-11: collision detection. */
    fresh_world();
    CHECK(detect_collision(the_naga) == False,
          "detect_collision is False on a fresh snake");
    the_naga.head->pos.x = the_naga.head->next->pos.x;
    the_naga.head->pos.y = the_naga.head->next->pos.y;
    CHECK(detect_collision(the_naga) == True,
          "detect_collision is True when the head overlaps the body");

    /* 12: keypress handling (direction change + quit). */
    fresh_world();
    {
        c_bool turned;
        the_naga.prev_dir = NORTH;
        process_keypress('a');
        /* c_bool is inverted (True=0, False=1): map C truth to c_bool. */
        turned = (the_naga.current_dir == WEST) ? True : False;
        process_keypress('q');
        CHECK(turned == True && game_on == False,
              "process_keypress turns WEST on 'a' and quits on 'q'");
    }

    free_list();
    printf("PASS: %d/%d (naga logic tests)\n", passed, total);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
           "\"command\":\"./test_naga\",\"discovered\":%d,\"passedCount\":%d}\n",
           (passed == total && total > 0) ? "true" : "false", total, passed);
    return (passed == total && total > 0) ? 0 : 1;
}

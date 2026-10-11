/* test_xbitmaps.c - consumer test for the xbitmaps pure-data package.
 *
 * Really #includes installed X11 bitmaps (they are C source snippets:
 * #define <name>_width/_height + static char <name>_bits[]) and checks
 * dimensions plus the packed byte count ((w+7)/8)*h, exactly the rule
 * XReadBitmapFile implements.
 */
#include <stdio.h>

#include <X11/bitmaps/boxes>
#include <X11/bitmaps/target>
#include <X11/bitmaps/cross_weave>
#include <X11/bitmaps/gray>
#include <X11/bitmaps/plaid>

static int g_checks = 0;

#define CHECK(cond, msg) \
    do { \
        if (!(cond)) { \
            printf("FAIL: %s\n", msg); \
            return 1; \
        } \
        g_checks++; \
    } while (0)

static int expect_bitmap(const char *name, int w, int h, int bytes)
{
    (void)name;
    if (((w + 7) / 8) * h != bytes) {
        printf("FAIL: %s %dx%d has %d bytes\n", name, w, h, bytes);
        return 1;
    }
    return 0;
}

int main(void)
{
    /* boxes: known fixed values from upstream data */
    CHECK(boxes_width == 16, "boxes_width == 16");
    CHECK(boxes_height == 16, "boxes_height == 16");
    CHECK(sizeof(boxes_bits) == 32, "boxes_bits has 32 bytes");

    /* the rest validate through the X11 packing rule */
    if (expect_bitmap("target", target_width, target_height,
                      (int)sizeof(target_bits))) return 1;
    g_checks++;
    if (expect_bitmap("cross_weave", cross_weave_width, cross_weave_height,
                      (int)sizeof(cross_weave_bits))) return 1;
    g_checks++;
    if (expect_bitmap("gray", gray_width, gray_height,
                      (int)sizeof(gray_bits))) return 1;
    g_checks++;
    if (expect_bitmap("plaid", plaid_width, plaid_height,
                      (int)sizeof(plaid_bits))) return 1;
    g_checks++;

#ifdef plaid_x_hot
    CHECK(plaid_x_hot == -1, "plaid_x_hot == -1 (no hotspot)");
#else
    printf("FAIL: plaid_x_hot not defined\n");
    return 1;
#endif

    printf("test_xbitmaps: %d checks ALL PASS\n", g_checks);
    return 0;
}

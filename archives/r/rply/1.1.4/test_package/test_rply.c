/* Consumer test for rply 1.1.4.
 *
 * Writes an ASCII PLY file through the public API, then reads it back and
 * verifies the element/property metadata and the vertex data.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rply.h"

static int checks = 0;
static int fails = 0;

static void check(const char *name, int ok) {
    checks++;
    if (ok) {
        printf("PASS: %s\n", name);
    } else {
        printf("FAIL: %s\n", name);
        fails++;
    }
}

static double sum_x = 0.0, sum_y = 0.0, sum_z = 0.0;

static int cb_x(p_ply_argument a) { sum_x += ply_get_argument_value(a); return 1; }
static int cb_y(p_ply_argument a) { sum_y += ply_get_argument_value(a); return 1; }
static int cb_z(p_ply_argument a) { sum_z += ply_get_argument_value(a); return 1; }

int main(void) {
    const char *path = "consumer_test.ply";
    const double xs[3] = {1.0, 2.0, 3.0};
    const double ys[3] = {4.0, 5.0, 6.0};
    const double zs[3] = {7.0, 8.0, 9.0};
    int i;

    /* ---- write ---- */
    p_ply ply = ply_create(path, PLY_ASCII, NULL, 0, NULL);
    check("ply_create", ply != NULL);
    if (!ply) {
        printf("RPLY_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
        return 1;
    }
    check("ply_add_element", ply_add_element(ply, "vertex", 3));
    check("ply_add_scalar_property x", ply_add_scalar_property(ply, "x", PLY_FLOAT));
    check("ply_add_scalar_property y", ply_add_scalar_property(ply, "y", PLY_FLOAT));
    check("ply_add_scalar_property z", ply_add_scalar_property(ply, "z", PLY_FLOAT));
    check("ply_add_comment", ply_add_comment(ply, "rply consumer test"));
    check("ply_write_header", ply_write_header(ply));
    for (i = 0; i < 3; i++) {
        ply_write(ply, xs[i]);
        ply_write(ply, ys[i]);
        ply_write(ply, zs[i]);
    }
    check("ply_close (write)", ply_close(ply));

    /* ---- read ---- */
    p_ply r = ply_open(path, NULL, 0, NULL);
    check("ply_open", r != NULL);
    if (!r) {
        printf("RPLY_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
        return 1;
    }
    check("ply_read_header", ply_read_header(r));
    check("ply_set_read_cb x returns 3 instances",
          ply_set_read_cb(r, "vertex", "x", cb_x, NULL, 0) == 3);
    ply_set_read_cb(r, "vertex", "y", cb_y, NULL, 0);
    ply_set_read_cb(r, "vertex", "z", cb_z, NULL, 0);
    check("ply_read", ply_read(r));
    check("sum of x values", sum_x == 6.0);
    check("sum of y values", sum_y == 15.0);
    check("sum of z values", sum_z == 24.0);

    {
        p_ply_element el = ply_get_next_element(r, NULL);
        const char *name = NULL;
        long ninstances = 0;
        int ok = el && ply_get_element_info(el, &name, &ninstances) &&
                 name && strcmp(name, "vertex") == 0 && ninstances == 3;
        check("ply_get_element_info(vertex, 3)", ok);
        if (el) {
            p_ply_property prop = ply_get_next_property(el, NULL);
            const char *pname = NULL;
            e_ply_type type = PLY_INT8, lt = PLY_INT8, vt = PLY_INT8;
            ok = prop && ply_get_property_info(prop, &pname, &type, &lt, &vt) &&
                 pname && strcmp(pname, "x") == 0 && type == PLY_FLOAT;
            check("ply_get_property_info(x, float)", ok);
        }
    }
    check("ply_close (read)", ply_close(r));

    remove(path);
    printf("RPLY_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
    return fails ? 1 : 0;
}

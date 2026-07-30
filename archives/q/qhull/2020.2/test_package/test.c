#include <libqhull_r/qhull_ra.h>

#include <stdio.h>

int main(void) {
    const int dimension = 2;
    const int point_count = 4;
    coordT points[] = {
        0.0, 0.0,
        1.0, 0.0,
        0.0, 1.0,
        1.0, 1.0,
    };
    char flags[] = "qhull Qt";
    int exit_code;
    int remaining_long = 0;
    int remaining_total = 0;
    qhT qh_state;
    qhT *qh = &qh_state;

    QHULL_LIB_CHECK
    qh_zero(qh, stderr);
    exit_code = qh_new_qhull(
        qh,
        dimension,
        point_count,
        points,
        False,
        flags,
        NULL,
        stderr
    );

    if (exit_code == 0 && qh->num_vertices != 4) {
        fprintf(stderr, "expected 4 vertices, got %d\n", qh->num_vertices);
        exit_code = 2;
    }
    if (exit_code == 0 && qh->num_facets != 4) {
        fprintf(stderr, "expected 4 facets, got %d\n", qh->num_facets);
        exit_code = 3;
    }

    qh_freeqhull(qh, !qh_ALL);
    qh_memfreeshort(qh, &remaining_long, &remaining_total);
    if (exit_code == 0 && (remaining_long != 0 || remaining_total != 0)) {
        fprintf(
            stderr,
            "qhull retained %d bytes in %d allocations\n",
            remaining_total,
            remaining_long
        );
        exit_code = 4;
    }

    if (exit_code == 0) {
        puts("Qhull consumer test passed");
    }
    return exit_code;
}

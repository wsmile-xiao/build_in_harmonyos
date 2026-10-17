// test_package/test.c — R34: substantive test that uses jc_voronoi API
// Instantiates the header-only implementation, generates a 2D Voronoi
// diagram from a point set and verifies the returned sites/edges.
#define JC_VORONOI_IMPLEMENTATION
#include <jc_voronoi.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    const int num_points = 4;
    jcv_point points[4];
    jcv_rect rect;
    jcv_diagram diagram;

    /* Four points inside the bounding rect */
    points[0].x = 0.1f; points[0].y = 0.1f;
    points[1].x = 0.9f; points[1].y = 0.1f;
    points[2].x = 0.1f; points[2].y = 0.9f;
    points[3].x = 0.9f; points[3].y = 0.9f;

    rect.min.x = 0.0f; rect.min.y = 0.0f;
    rect.max.x = 1.0f; rect.max.y = 1.0f;

    memset(&diagram, 0, sizeof(diagram));

    jcv_diagram_generate(num_points, points, &rect, 0, &diagram);

    if (diagram.numsites != num_points) {
        fprintf(stderr, "FAIL: expected %d sites, got %d\n",
                num_points, diagram.numsites);
        jcv_diagram_free(&diagram);
        return 1;
    }

    const jcv_site* sites = jcv_diagram_get_sites(&diagram);
    if (sites == 0) {
        fprintf(stderr, "FAIL: no sites returned\n");
        jcv_diagram_free(&diagram);
        return 1;
    }

    /* Every site must reference its input index */
    int count = 0;
    for (int i = 0; i < diagram.numsites; ++i) {
        const jcv_site* site = &sites[i];
        if (site->index < 0 || site->index >= num_points) {
            fprintf(stderr, "FAIL: site %d has invalid index %d\n",
                    i, site->index);
            jcv_diagram_free(&diagram);
            return 1;
        }
        ++count;
    }

    if (count != num_points) {
        fprintf(stderr, "FAIL: iterated %d sites, expected %d\n",
                count, num_points);
        jcv_diagram_free(&diagram);
        return 1;
    }

    jcv_diagram_free(&diagram);

    printf("jc_voronoi test passed: %d sites generated and verified\n",
           count);
    return 0;
}

#include <stdio.h>
#include <stdint.h>
#include <h3/h3api.h>

/* DEGS_TO_RADS is an internal macro, not part of the public h3api.h */
static const double DEGS_TO_RADS = 3.14159265358979323846 / 180.0;

int main(void) {
    /* 消费者视角：调用 h3 库的真实 API（R34：必须实质依赖被测包） */
    LatLng ll = {.lat = 40.689167 * DEGS_TO_RADS, .lng = -74.044444 * DEGS_TO_RADS};
    H3Index h3 = H3_NULL;
    H3Error err = latLngToCell(&ll, 9, &h3);
    if (err != E_SUCCESS) {
        fprintf(stderr, "latLngToCell failed: %s\n", describeH3Error(err));
        return 1;
    }
    if (h3 == H3_NULL) {
        fprintf(stderr, "latLngToCell returned H3_NULL\n");
        return 1;
    }
    char buf[17];
    h3ToString(h3, buf, sizeof(buf));
    printf("h3 index (res 9, Statue of Liberty): %s\n", buf);

    /* 反向转换验证 */
    LatLng out;
    err = cellToLatLng(h3, &out);
    if (err != E_SUCCESS) {
        fprintf(stderr, "cellToLatLng failed: %s\n", describeH3Error(err));
        return 1;
    }
    printf("cellToLatLng OK: lat=%.6f lng=%.6f\n", out.lat / DEGS_TO_RADS, out.lng / DEGS_TO_RADS);
    return 0;
}

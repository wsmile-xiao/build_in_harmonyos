/* test_package for tinyspline 0.6.0 — real API consumption (R34).
 * Creates a clamped cubic B-spline, evaluates it, and converts to
 * Bezier curves, asserting each operation succeeds via TS_CALL.
 */
#include "tinyspline.h"
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    tsStatus status;
    tsBSpline spline = ts_bspline_init();
    tsDeBoorNet net = ts_deboornet_init();
    tsBSpline beziers = ts_bspline_init();
    tsReal *result = NULL;
    tsReal *ctrlp = NULL;

    TS_TRY(try, status.code, &status)
        TS_CALL(try, status.code, ts_bspline_new(
            7, 2, 3, TS_CLAMPED, &spline, &status))
        TS_CALL(try, status.code, ts_bspline_eval(
            &spline, 0.5, &net, &status))
        TS_CALL(try, status.code, ts_deboornet_result(
            &net, &result, &status))
        printf("evaluate(0.5) = %f, %f\n", result[0], result[1]);
        TS_CALL(try, status.code, ts_bspline_to_beziers(
            &spline, &beziers, &status))
        TS_CALL(try, status.code, ts_bspline_control_points(
            &beziers, &ctrlp, &status))
        printf("bezier control points = %f, %f\n", ctrlp[0], ctrlp[1]);
    TS_CATCH(status.code)
        puts(status.message);
    TS_FINALLY
        ts_bspline_free(&spline);
        ts_deboornet_free(&net);
        ts_bspline_free(&beziers);
        if (result)
            free(result);
        if (ctrlp)
            free(ctrlp);
    TS_END_TRY

    if (status.code != TS_SUCCESS) {
        fprintf(stderr, "test_tinyspline: FAILED (error %d)\n", status.code);
        return 1;
    }
    printf("test_tinyspline: OK\n");
    return 0;
}

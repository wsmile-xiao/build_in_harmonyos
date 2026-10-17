// Test that the installed astronomy public header and static library link
// and produce a correct, observable astronomical calculation.
#include <stdio.h>
#include <math.h>
#include "astronomy.h"

int main(void)
{
    // 2026-09-19 00:00 UTC: compute Earth's heliocentric vector.
    // (The Sun's own heliocentric vector is (0,0,0) by definition, so we
    // verify with Earth, whose heliocentric distance is ~1 AU.)
    astro_time_t t = Astronomy_MakeTime(2026, 9, 19, 0, 0, 0.0);
    astro_vector_t sv = Astronomy_HelioVector(BODY_EARTH, t);
    if (sv.status != ASTRO_SUCCESS)
    {
        fprintf(stderr, "HelioVector failed: status %d\n", sv.status);
        return 1;
    }
    double mag = hypot(hypot(sv.x, sv.y), sv.z);
    if (mag < 0.98 || mag > 1.02)
    {
        fprintf(stderr, "Earth magnitude out of range: %.6f AU\n", mag);
        return 1;
    }
    printf("Earth heliocentric distance: %.6f AU\n", mag);
    printf("Body name: %s\n", Astronomy_BodyName(BODY_EARTH));
    return 0;
}
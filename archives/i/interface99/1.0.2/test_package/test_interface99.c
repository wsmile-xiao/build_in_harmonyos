/* Consumer test for interface99/1.0.1+ on OHOS PC.
 *
 * Mirrors upstream's examples/shape.c: defines a Shape interface, two
 * implementations, dispatches dynamically, and asserts the vtable calls
 * and data polymorphism behave exactly as documented.  Exit code is the
 * verdict.
 */
#include <interface99.h>

#include <assert.h>
#include <stdio.h>

#define Shape_IFACE                 \
    vfunc(int, perim, const VSelf)  \
    vfunc(void, scale, VSelf, int factor)

interface(Shape);

typedef struct {
    int a, b;
} Rectangle;

static int Rectangle_perim(const VSelf) {
    VSELF(const Rectangle);
    return (self->a + self->b) * 2;
}

static void Rectangle_scale(VSelf, int factor) {
    VSELF(Rectangle);
    self->a *= factor;
    self->b *= factor;
}

impl(Shape, Rectangle);

typedef struct {
    int a, b, c;
} Triangle;

static int Triangle_perim(const VSelf) {
    VSELF(const Triangle);
    return self->a + self->b + self->c;
}

static void Triangle_scale(VSelf, int factor) {
    VSELF(Triangle);
    self->a *= factor;
    self->b *= factor;
    self->c *= factor;
}

impl(Shape, Triangle);

int main(void) {
    Rectangle rect = {5, 7};
    Triangle tri = {10, 20, 30};

    Shape r = DYN(Rectangle, Shape, &rect);
    Shape t = DYN(Triangle, Shape, &tri);

    assert(VCALL(r, perim) == 24);
    assert(VCALL(t, perim) == 60);

    VCALL(r, scale, 5);
    assert(VCALL(r, perim) == 120);

    VCALL(t, scale, 5);
    assert(VCALL(t, perim) == 300);

    /* The vtable must stay distinct per dynamic type. */
    assert(r.vptr != t.vptr);

    printf("interface99 consumer test: 5 assertions passed\n");
    return 0;
}

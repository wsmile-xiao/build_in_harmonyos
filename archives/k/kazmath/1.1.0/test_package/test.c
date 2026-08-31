#include <kazmath/kazmath.h>
#include <stdio.h>

int main(void) {
    kmMat4 m, a, b, c;
    kmVec3 v;
    kmMat4Identity(&m);
    if (m.mat[0] != 1.0f || m.mat[15] != 1.0f) return 1;
    kmVec3Fill(&v, 1.0f, 2.0f, 3.0f);
    kmVec3Transform(&v, &v, &m);
    if (v.x != 1.0f || v.y != 2.0f || v.z != 3.0f) return 1;
    kmMat4Identity(&a);
    kmMat4Identity(&b);
    kmMat4Multiply(&c, &a, &b);
    if (c.mat[0] != 1.0f || c.mat[15] != 1.0f) return 1;
    puts("kazmath consumer API test: OK");
    return 0;
}

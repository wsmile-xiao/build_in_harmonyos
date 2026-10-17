/* graphene 1.10.8 真实功能断言：graphene_point3d_* 核心 API。 */
#include <graphene.h>
#include <stdio.h>

int main(void)
{
    graphene_point3d_t p;
    graphene_point3d_t q;

    graphene_point3d_init(&p, 1.f, 2.f, 3.f);
    graphene_point3d_init(&q, 1.f, 2.f, 3.f);

    if (graphene_point3d_distance(&p, &q, NULL) != 0.f) {
        fprintf(stderr, "point3d distance not zero\n");
        return 1;
    }

    printf("graphene point3d OK\n");
    return 0;
}

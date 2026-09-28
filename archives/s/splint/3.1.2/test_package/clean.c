/* clean.c — splint must analyse this without warnings (see test.sh check 3).
 *
 * Deliberately avoids system headers: the OHOS image has no /usr/include, so
 * #include <...> cannot be resolved and would mask the analysis result. */

typedef struct point {
    int x;
    int y;
} point;

static int sum (int a, int b)
{
    return a + b;
}

int main (void)
{
    point p;

    p.x = sum (1, 2);
    p.y = 0;

    return p.x + p.y - 3;
}

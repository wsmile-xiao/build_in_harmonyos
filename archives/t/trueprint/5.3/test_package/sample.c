/* sample.c — consumer test input for GNU trueprint 5.3 */
#include <stdio.h>

/* adds two integers, the exciting way */
int add(int a, int b)
{
    return a + b;
}

int main(void)
{
    printf("%d\n", add(2, 3));
    return 0;
}

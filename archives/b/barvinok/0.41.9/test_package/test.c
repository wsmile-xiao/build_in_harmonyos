#include <stdio.h>

#include <barvinok/options.h>

int main(void)
{
    struct barvinok_options *options = barvinok_options_new_with_defaults();

    if (!options || options->MaxRays == 0)
        return 1;

    barvinok_options_free(options);
    puts("barvinok public API OK");
    return 0;
}

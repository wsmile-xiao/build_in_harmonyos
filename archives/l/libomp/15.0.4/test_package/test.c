#include <omp.h>
#include <stdio.h>

int main(void) {
    int max_threads = omp_get_max_threads();
    if (max_threads > 0) {
        printf("omp_get_max_threads: %d\n", max_threads);
        #pragma omp parallel
        {
            #pragma omp single
            printf("Running with %d threads\n", omp_get_num_threads());
        }
        printf("test libomp 15.0.4: OK\n");
        return 0;
    }
    fprintf(stderr, "omp_get_max_threads returned %d\n", max_threads);
    return 1;
}

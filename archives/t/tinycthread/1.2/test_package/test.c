#include <tinycthread.h>
#include <stdio.h>
#include <stdlib.h>

int thread_func(void *arg) {
    printf("Thread running with arg: %d\n", *(int*)arg);
    return 0;
}

int main() {
    thrd_t thread;
    int arg = 42;
    
    if (thrd_create(&thread, thread_func, &arg) != thrd_success) {
        fprintf(stderr, "Failed to create thread\n");
        return EXIT_FAILURE;
    }
    
    int result;
    if (thrd_join(thread, &result) != thrd_success) {
        fprintf(stderr, "Failed to join thread\n");
        return EXIT_FAILURE;
    }
    
    printf("Thread joined successfully, result: %d\n", result);
    return EXIT_SUCCESS;
}

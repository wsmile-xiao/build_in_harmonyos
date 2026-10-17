/* test_package/test.c — enkiTS consumer test (R34: substantive API use).
 *
 * Exercises the core enkiTS C task-scheduler API: create a TaskScheduler,
 * initialize it (which spawns the worker threads), schedule a parallel
 * TaskSet that sums a range of integers across threads, wait for it to
 * complete, verify the result against a serial sum, then shut down and
 * delete the scheduler. This links against libenkiTS and calls
 * enkiNewTaskScheduler / enkiInitTaskScheduler / enkiCreateTaskSet /
 * enkiAddTaskSet / enkiWaitForTaskSet / enkiDeleteTaskSet /
 * enkiWaitforAllAndShutdown / enkiDeleteTaskScheduler — not an empty stub.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "enkiTS/TaskScheduler_c.h"

/* Task arguments: a parallel partial-sum array indexed by thread number. */
typedef struct ParallelSumArgs {
    uint64_t *pPartialSums;
    uint32_t  numPartialSums;
} ParallelSumArgs;

/* The task function executed in parallel across the [start_, end_) range. */
static void ParallelSumTaskSetFunc(uint32_t start_, uint32_t end_,
                                   uint32_t threadnum_, void *pArgs_) {
    ParallelSumArgs args = *(ParallelSumArgs *)pArgs_;
    uint64_t sum = args.pPartialSums[threadnum_];
    uint32_t i;
    for (i = start_; i < end_; ++i) {
        sum += (uint64_t)(i + 1);
    }
    args.pPartialSums[threadnum_] = sum;
}

int main(void) {
    const uint32_t setSize = 10 * 1024 * 1024; /* 10M elements */
    uint32_t i;
    uint64_t serialSum;
    int rc = 0;

    /* 1. Create and initialize the task scheduler (spawns worker threads). */
    enkiTaskScheduler *pETS = enkiNewTaskScheduler();
    if (pETS == NULL) {
        printf("FAIL: enkiNewTaskScheduler returned NULL\n");
        return 1;
    }
    enkiInitTaskScheduler(pETS);
    uint32_t numThreads = enkiGetNumTaskThreads(pETS);
    printf("enkiTS initialized: %u task threads\n", (unsigned)numThreads);
    if (numThreads == 0) {
        printf("FAIL: enkiGetNumTaskThreads returned 0\n");
        rc = 1;
        goto cleanup;
    }

    /* 2. Create a TaskSet and schedule it over the full range. */
    enkiTaskSet *pTask = enkiCreateTaskSet(pETS, ParallelSumTaskSetFunc);
    if (pTask == NULL) {
        printf("FAIL: enkiCreateTaskSet returned NULL\n");
        rc = 1;
        goto cleanup;
    }

    ParallelSumArgs args;
    args.numPartialSums = numThreads;
    args.pPartialSums = (uint64_t *)calloc(args.numPartialSums, sizeof(uint64_t));
    if (args.pPartialSums == NULL) {
        printf("FAIL: calloc failed\n");
        rc = 1;
        goto delete_task;
    }

    struct enkiParamsTaskSet params = enkiGetParamsTaskSet(pTask);
    params.pArgs = &args;
    params.setSize = setSize;
    params.minRange = 1024;
    enkiSetParamsTaskSet(pTask, params);

    /* 3. Add the task and wait for completion. */
    enkiAddTaskSet(pETS, pTask);
    enkiWaitForTaskSet(pETS, pTask);

    /* 4. Reduce the partial sums into the parallel total. */
    uint64_t parallelSum = 0;
    for (i = 0; i < args.numPartialSums; ++i) {
        parallelSum += args.pPartialSums[i];
    }

    /* 5. Compute the serial reference sum and compare. */
    serialSum = 0;
    for (i = 0; i < setSize; ++i) {
        serialSum += (uint64_t)(i + 1);
    }

    printf("parallel sum: %llu\n", (long long unsigned)parallelSum);
    printf("serial sum:   %llu\n", (long long unsigned)serialSum);

    if (parallelSum != serialSum) {
        printf("FAIL: parallel sum does not match serial sum\n");
        rc = 1;
    } else {
        printf("test enkits 1.12: OK\n");
    }

    free(args.pPartialSums);

delete_task:
    enkiDeleteTaskSet(pETS, pTask);

cleanup:
    enkiWaitforAllAndShutdown(pETS);
    enkiDeleteTaskScheduler(pETS);
    return rc;
}

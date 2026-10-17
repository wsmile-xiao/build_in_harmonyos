/* libgomp 16.1.1 L1 消费者测试。
 *
 * 验证打包后的 GCC OpenMP 运行时（libgomp）能被消费者使用：
 *   1. #include <omp.h> 的运行时 API（线程数 / 线程号 / 动态线程 / 锁）。
 *   2. libgomp 的并行核心（GOMP_parallel ABI）。
 *
 * 说明：OHOS clang 15 的 -fopenmp=libgomp 驱动参数不会传给 cc1（被吞掉），
 *   #pragma omp parallel 不会生成并行代码（工具链限制，非 libgomp 缺陷），
 *   故改用 libgomp 导出的底层 GOMP_parallel ABI 直接验证并行执行。
 *
 * 编译：clang -I<omp.h dir> -L<libgomp dir> -lgomp test.c
 * 运行：OMP_NUM_THREADS=4 ./test_libgomp
 */
#include <omp.h>
#include <stdio.h>

/* libgomp 底层并行 ABI（libgomp.map 导出）。 */
extern void GOMP_parallel (void (*fn) (void *), void *data,
                           unsigned num_threads, unsigned int flags);

static void
parallel_worker (void *data)
{
    int *seen = (int *)data;
    int tid = omp_get_thread_num ();
    if (tid >= 0 && tid < 4)
        seen[tid] = 1;
}

int
main (void)
{
    int failures = 0;

    /* 1. 最大线程数必须为正 */
    int max_threads = omp_get_max_threads ();
    if (max_threads <= 0) {
        printf ("FAIL: omp_get_max_threads = %d\n", max_threads);
        failures++;
    }

    /* 2. 固定线程数并读回 */
    omp_set_dynamic (0);
    omp_set_num_threads (4);
    if (omp_get_dynamic () != 0) {
        printf ("FAIL: omp_get_dynamic != 0 after omp_set_dynamic(0)\n");
        failures++;
    }

    /* 3. 并行区外线程号应为 0，线程数应为 1 */
    int serial_num = omp_get_num_threads ();
    int serial_tid = omp_get_thread_num ();
    if (serial_num != 1 || serial_tid != 0) {
        printf ("FAIL: serial region num=%d tid=%d\n", serial_num, serial_tid);
        failures++;
    }

    /* 4. 处理器数应为正 */
    if (omp_get_num_procs () <= 0) {
        printf ("FAIL: omp_get_num_procs <= 0\n");
        failures++;
    }

    /* 5. omp_lock_t 基本可用 */
    omp_lock_t lock;
    omp_init_lock (&lock);
    omp_set_lock (&lock);
    omp_unset_lock (&lock);
    omp_destroy_lock (&lock);

    /* 6. 并行核心：GOMP_parallel 创建 4 线程 team，每个线程各执行一次
     *    parallel_worker，证明 libgomp 的线程池/barrier 真并行工作。 */
    int seen[4] = {0, 0, 0, 0};
    GOMP_parallel (parallel_worker, seen, 4, 0);

    int seen_threads = 0;
    for (int i = 0; i < 4; i++)
        seen_threads += seen[i];

    printf ("max_threads=%d seen_threads=%d\n", max_threads, seen_threads);

    if (failures == 0 && seen_threads >= 2) {
        printf ("libgomp 16.1.1 runtime test: ALL PASSED\n");
        return 0;
    }
    if (seen_threads < 2) {
        printf ("FAIL: parallel region used only %d thread(s)\n", seen_threads);
        failures++;
    }
    printf ("libgomp 16.1.1 runtime test: %d FAILURE(S)\n", failures);
    return 1;
}

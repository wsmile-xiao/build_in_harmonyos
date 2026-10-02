/*
 * sems_host_stubs.c — 测试宿主提供的 SEMS core 日志符号
 *
 * SEMS 插件（MODULE）由 sems 主程序以 -rdynamic 加载，插件引用宿主导出的
 * 日志符号。dlopen 消费模型下宿主需提供这些符号。符号集合经
 * `llvm-nm -D --undefined-only opus.so` 实测确认：
 *   run_log_hooks / log_level / log_level2str / log_stderr
 *
 * 声明必须与上游 core/log.h:170-175 的 extern 逐字一致：
 *   extern int log_level;
 *   extern int log_stderr;
 *   extern const char* log_level2str[];
 *   void run_log_hooks(int, pid_t, pthread_t, const char*, const char*, int, char*);
 * 其中 log_level2str 是**数据符号**（core/log.h 的 _LOG 宏按
 * log_level2str[level_] 取值），因此这里必须定义为数组而非函数——否则
 * ABI 不符，插件内的日志宏会把函数体当地址解引用。
 */
#include <pthread.h>
#include <stdio.h>
#include <sys/types.h> /* pid_t */

int log_level = 2; /* L_INFO，对齐 core/log.h 的 enum Log_Level */
int log_stderr = 1;
const char* log_level2str[] = { "ERROR", "WARNING", "INFO", "DEBUG", NULL };

void run_log_hooks(int level, pid_t pid, pthread_t tid,
                   const char* func, const char* file, int line, char* msg) {
    (void)pid; (void)tid; (void)func; (void)file; (void)line;
    if (msg)
        fprintf(stderr, "[sems:%d] %s\n", level, msg);
}

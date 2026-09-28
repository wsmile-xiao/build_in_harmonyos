/* 消费者测试：真实执行包交付的 memdump，逐条断言退出码与错误形态。
 *
 * 依据（本包一手实测，详见 archives/m/memdump/1.01/notes.md）：
 *   memdump.c:437  if ((fd = open(path, O_RDONLY, 0)) < 0) error("open %s: %m", path);
 *   error.c:131    error() 打印后 exit(1)  ⇒ 设备打不开时 rc==1，
 *                  stderr 形如 "<argv0>: open /dev/mem: <strerror>"。
 *   OHOS 构建主机实测 /dev/mem 与 /dev/kmem 的设备节点不存在（ENOENT，不是
 *   EACCES/EPERM —— 节点本身缺失），因此本平台走 "absent" 分支。
 *   设备形态由 stat+open 现场探测、错误文案取自当次 strerror，不写死本平台读数：
 *   换到 /dev/mem 可读的 Linux 上自动改走"真转储 4096 字节"分支。
 * 断言计数在结尾打印（passed/run），PR 正文与本目录 MANIFEST.yml 引用同一份数字。
 * 所有写入落在按进程号分址的私有临时目录，退出前清理。
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static int assertions_run;
static int assertions_passed;
static char work_dir[1024];

struct outcome {
    int rc;
    long stdout_bytes;
    char stderr_text[4096];
};

static void check(const char *what, int cond)
{
    assertions_run++;
    if (cond) {
        assertions_passed++;
        printf("ok   %s\n", what);
    } else {
        fprintf(stderr, "FAIL %s\n", what);
    }
}

static long file_bytes(const char *path)
{
    struct stat st;

    return (stat(path, &st) == 0) ? (long) st.st_size : -1;
}

static void slurp(const char *path, char *buf, size_t cap)
{
    FILE *f;
    size_t n;

    buf[0] = 0;
    f = fopen(path, "rb");
    if (f == NULL) {
        return;
    }
    n = fread(buf, 1, cap - 1, f);
    buf[n] = 0;
    fclose(f);
}

/* run - 执行制品一次，捕获退出码、stdout 字节数与 stderr 全文 */
static void run(const char *prog, const char *args, struct outcome *o)
{
    char cmd[4096];
    char path[1024];
    int rc;

    snprintf(cmd, sizeof(cmd), "\"%s\" %s > \"%s/out\" 2> \"%s/err\" < /dev/null",
             prog, args, work_dir, work_dir);
    rc = system(cmd);
    o->rc = (rc == -1) ? -1 : WEXITSTATUS(rc);
    snprintf(path, sizeof(path), "%s/out", work_dir);
    o->stdout_bytes = file_bytes(path);
    snprintf(path, sizeof(path), "%s/err", work_dir);
    slurp(path, o->stderr_text, sizeof(o->stderr_text));
}

/* device_form - 现场探测设备节点形态；why 回填当次 strerror 文案 */
static const char *device_form(const char *dev, char *why, size_t cap)
{
    struct stat st;
    int fd;

    why[0] = 0;
    if (stat(dev, &st) != 0) {
        snprintf(why, cap, "%s", strerror(errno));
        return "absent";
    }
    fd = open(dev, O_RDONLY, 0);
    if (fd < 0) {
        snprintf(why, cap, "%s", strerror(errno));
        return "denied";
    }
    close(fd);
    snprintf(why, cap, "%s", "readable");
    return "openable";
}

int main(int argc, char **argv)
{
    const char *prog = (argc > 1) ? argv[1] : "memdump";
    struct outcome o;
    char mem_why[256];
    char kmem_why[256];
    char args[1536];
    const char *mem_form;
    const char *kmem_form;
    const char *base;
    char path[1024];

    /* 私有临时目录（按进程号分址）；TMPDIR 缺失时退到 HOME，再退到 /tmp */
    base = getenv("TMPDIR");
    if (base == NULL || *base == 0) {
        base = getenv("HOME");
    }
    if (base == NULL || *base == 0) {
        base = "/tmp";
    }
    snprintf(work_dir, sizeof(work_dir), "%s/memdump-test-%ld", base, (long) getpid());
    if (mkdir(work_dir, 0700) != 0 && errno != EEXIST) {
        fprintf(stderr, "FAIL cannot create private test dir %s: %s\n",
                work_dir, strerror(errno));
        return 1;
    }

    mem_form = device_form("/dev/mem", mem_why, sizeof(mem_why));
    kmem_form = device_form("/dev/kmem", kmem_why, sizeof(kmem_why));
    printf("probed /dev/mem=%s (%s) /dev/kmem=%s (%s)\n",
           mem_form, mem_why, kmem_form, kmem_why);

    /* A. 默认物理内存路径：-s 换算 + 设备打开 + %m 错误格式化 + error() 退出码 */
    run(prog, "-s 4k", &o);
    if (strcmp(mem_form, "openable") == 0) {
        check("A1 rc==0 with readable /dev/mem", o.rc == 0);
        check("A2 dumped exactly -s bytes", o.stdout_bytes == 4096);
        check("A3 no diagnostic on the success path", o.stderr_text[0] == 0);
    } else {
        check("A1 rc==1 when /dev/mem unusable", o.rc == 1);
        check("A2 stderr names the device", strstr(o.stderr_text, "open /dev/mem:") != NULL);
        check("A3 stderr carries this errno text", strstr(o.stderr_text, mem_why) != NULL);
        check("A4 stdout produced no dump bytes", o.stdout_bytes == 0);
    }

    /* B. -k 走 _PATH_KMEM（补丁提供的宏之一） */
    run(prog, "-k -s 4k", &o);
    if (strcmp(kmem_form, "openable") == 0) {
        check("B1 rc==0 with readable /dev/kmem", o.rc == 0);
    } else {
        check("B1 rc==1 when /dev/kmem unusable", o.rc == 1);
        check("B2 stderr names /dev/kmem", strstr(o.stderr_text, "open /dev/kmem:") != NULL);
        check("B3 stderr carries this errno text", strstr(o.stderr_text, kmem_why) != NULL);
    }

    /* C. 未知选项：usage() 经 error() 终止（上游无 --version/--help，见 notes.md） */
    run(prog, "-Z", &o);
    check("C1 unknown option rc==1", o.rc == 1);
    check("C2 usage banner emitted", strstr(o.stderr_text, "usage:") != NULL);
    check("C3 usage documents -s", strstr(o.stderr_text, "-s memory_dump-size") != NULL);
    check("C4 no dump bytes on usage error", o.stdout_bytes == 0);

    /* D. convert_size() 契约：非法尺寸后缀（memdump.c:387 + convert_size.c:46-58） */
    run(prog, "-s xyz", &o);
    check("D1 bad size rc==1", o.rc == 1);
    check("D2 stderr bad memory dump size", strstr(o.stderr_text, "bad memory dump size") != NULL);

    /* E. 位置参数必须为空（memdump.c:435） */
    run(prog, "-s 4k /dev/null", &o);
    check("E1 extra operand rc==1", o.rc == 1);
    check("E2 stderr too many arguments", strstr(o.stderr_text, "too many arguments") != NULL);

    /* F. -v 审计链路：remark() 输出到 stderr，k 后缀换算成 0x1000 */
    run(prog, "-v -s 4k", &o);
    check("F1 verbose dump size", strstr(o.stderr_text, "dump size 0x1000") != NULL);
    check("F2 verbose page size", strstr(o.stderr_text, "page size 0x") != NULL);
    check("F3 verbose buffer size", strstr(o.stderr_text, "buffer size 0x") != NULL);

    /* G. -m 映射文件：fopen(optarg,"w") 在打开设备之前发生，故失败路径也应建文件 */
    snprintf(path, sizeof(path), "%s/map.txt", work_dir);
    snprintf(args, sizeof(args), "-s 4k -m \"%s\"", path);
    run(prog, args, &o);
    if (strcmp(mem_form, "openable") == 0) {
        check("G1 -m map path rc==0 on readable device", o.rc == 0);
        check("G2 map file written", file_bytes(path) > 0);
    } else {
        check("G1 -m map path rc==1 on unusable device", o.rc == 1);
        check("G2 map file created but empty", file_bytes(path) == 0);
    }

    /* H. -b 读缓冲尺寸换算被接受（不报 bad read buffer size） */
    run(prog, "-b 64k -s 4k", &o);
    check("H1 -b size accepted", strstr(o.stderr_text, "bad read buffer size") == NULL);

    printf("memdump consumer test: assertions %d/%d passed\n",
           assertions_passed, assertions_run);

    /* 清理私有目录（失败也要清） */
    unlink(path);
    snprintf(path, sizeof(path), "%s/out", work_dir);
    unlink(path);
    snprintf(path, sizeof(path), "%s/err", work_dir);
    unlink(path);
    rmdir(work_dir);

    return (assertions_passed == assertions_run) ? 0 : 1;
}

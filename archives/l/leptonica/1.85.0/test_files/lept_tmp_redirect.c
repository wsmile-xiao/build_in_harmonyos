#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdarg.h>
#include <dirent.h>
#include <errno.h>

/* 将 /tmp/lept 前缀重定向到 $LEPT_TMP_REDIRECT 指定的可写目录。
 * 用于 /tmp 只读的 HarmonyOS 环境运行上游 reg 测试。 */

static const char *redirect_base(void) {
    static char buf[512];
    static int inited = 0;
    if (!inited) {
        const char *env = getenv("LEPT_TMP_REDIRECT");
        if (env && env[0]) {
            snprintf(buf, sizeof(buf), "%s", env);
        } else {
            buf[0] = '\0';
        }
        inited = 1;
    }
    return buf;
}

/* 若 path 以 /tmp/lept 开头则返回重定向后的静态缓冲，否则返回 NULL */
static const char *maybe_redirect(const char *path) {
    static __thread char rbuf[1024];
    const char *base = redirect_base();
    if (!base[0] || !path) return NULL;
    /* 重定向前缀规则（等长映射到 base 下）：
     *   /tmp/lept...  → base/lept...   （reg 框架子树 + /tmp/lept.XXX 临时文件，
     *                                  path+4 保留 "lept" 起始的相对部分） */
    if (strncmp(path, "/tmp/lept", 9) == 0) {
        snprintf(rbuf, sizeof(rbuf), "%s/%s", base, path + 5);
        return rbuf;
    }
    return NULL;
}

int mkdir(const char *path, mode_t mode) {
    static int (*real_mkdir)(const char *, mode_t) = NULL;
    if (!real_mkdir) real_mkdir = dlsym(RTLD_NEXT, "mkdir");
    const char *r = maybe_redirect(path);
    return real_mkdir(r ? r : path, mode);
}

int mkdirat(int dirfd, const char *path, mode_t mode) {
    static int (*real_mkdirat)(int, const char *, mode_t) = NULL;
    if (!real_mkdirat) real_mkdirat = dlsym(RTLD_NEXT, "mkdirat");
    const char *r = maybe_redirect(path);
    return real_mkdirat(dirfd, r ? r : path, mode);
}

/* fopen/fopen64 包装：leptonica 用 fopenWriteStream 等，最终走 fopen */
FILE *fopen(const char *path, const char *mode) {
    static FILE *(*real_fopen)(const char *, const char *) = NULL;
    if (!real_fopen) real_fopen = dlsym(RTLD_NEXT, "fopen");
    const char *r = maybe_redirect(path);
    if (getenv("LEPT_REDIRECT_DEBUG") && r)
        dprintf(2, "[dbg] fopen %s -> %s\n", path, r);
    return real_fopen(r ? r : path, mode);
}


/* open 包装：leptonica l_binaryWrite/read 走 open */
int open(const char *path, int flags, ...) {
    static int (*real_open)(const char *, int, ...) = NULL;
    if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
    const char *r = maybe_redirect(path);
    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = va_arg(ap, mode_t);
        va_end(ap);
    }
    return real_open(r ? r : path, flags, mode);
}


/* access/stat 系列：lept_direxists 用 stat；getSortedPathnamesInDirectory 用 opendir */
int stat(const char *path, struct stat *st) {
    static int (*real_stat)(const char *, struct stat *) = NULL;
    if (!real_stat) real_stat = dlsym(RTLD_NEXT, "stat");
    const char *r = maybe_redirect(path);
    return real_stat(r ? r : path, st);
}


int access(const char *path, int mode) {
    static int (*real_access)(const char *, int) = NULL;
    if (!real_access) real_access = dlsym(RTLD_NEXT, "access");
    const char *r = maybe_redirect(path);
    return real_access(r ? r : path, mode);
}

DIR *opendir(const char *path) {
    static DIR *(*real_opendir)(const char *) = NULL;
    if (!real_opendir) real_opendir = dlsym(RTLD_NEXT, "opendir");
    const char *r = maybe_redirect(path);
    return real_opendir(r ? r : path);
}

int unlink(const char *path) {
    static int (*real_unlink)(const char *) = NULL;
    if (!real_unlink) real_unlink = dlsym(RTLD_NEXT, "unlink");
    const char *r = maybe_redirect(path);
    return real_unlink(r ? r : path);
}

int remove(const char *path) {
    static int (*real_remove)(const char *) = NULL;
    if (!real_remove) real_remove = dlsym(RTLD_NEXT, "remove");
    const char *r = maybe_redirect(path);
    return real_remove(r ? r : path);
}

int rmdir(const char *path) {
    static int (*real_rmdir)(const char *) = NULL;
    if (!real_rmdir) real_rmdir = dlsym(RTLD_NEXT, "rmdir");
    const char *r = maybe_redirect(path);
    return real_rmdir(r ? r : path);
}

int rename(const char *old, const char *new) {
    static int (*real_rename)(const char *, const char *) = NULL;
    if (!real_rename) real_rename = dlsym(RTLD_NEXT, "rename");
    const char *ro = maybe_redirect(old);
    const char *rn = maybe_redirect(new);
    return real_rename(ro ? ro : old, rn ? rn : new);
}

/* tmpfile 拦截：musl tmpfile 用 /tmp（只读），重定向到 $LEPT_TMP_REDIRECT 下。
 * leptonica 的 tmpfile 仅在 HAVE_FMEMOPEN 未定义时的 *Mem 系列 #else 分支使用。 */
FILE *tmpfile(void) {
    static FILE *(*real_tmpfile)(void) = NULL;
    static char path[600];
    static int seq = 0;
    if (!real_tmpfile)
        real_tmpfile = dlsym(RTLD_NEXT, "tmpfile");
    /* 先试真实 tmpfile（若 TMPDIR 环境变量生效则成功） */
    FILE *fp = real_tmpfile ? real_tmpfile() : NULL;
    if (fp) return fp;
    /* 失败则回落到重定向目录 */
    const char *base = redirect_base();
    if (base[0]) {
        mkdir("/tmp/lept", 0777);
        const char *r = maybe_redirect("/tmp/lept");
        mkdir(r, 0777);
        snprintf(path, sizeof(path), "%s/tmpfile_%d_%ld", base, ++seq, (long)getpid());
        return fopen(path, "w+b");
    }
    return NULL;
}

/* realpath 拦截：leptonica getFilenamesInDirectory 用 realpath 解析
 * "/tmp/lept" 子目录（在只读 /tmp 上不存在）→ NULL → "realdir not made"。
 * musl realpath 内部直接系统调用不走 fopen/open，必须单独拦截。 */
char *realpath(const char *path, char *resolved) {
    static char *(*real_realpath)(const char *, char *) = NULL;
    if (!real_realpath) real_realpath = dlsym(RTLD_NEXT, "realpath");
    const char *r = maybe_redirect(path);
    if (r) {
        /* 重定向路径解析：直接返回规范化后的重定向路径。
         * 用真实 realpath 解析重定向路径（真实存在），若无 resolved
         * 缓冲则分配 PATH_MAX。 */
        static __thread char rbuf[4096];
        char *out = resolved ? resolved : rbuf;
        char *res = real_realpath(r, out);
        if (!res && !resolved) return NULL;
        return res;
    }
    return real_realpath(path, resolved);
}


/* mkstemp 家族拦截（等长替换方案）：
 * leptonica l_makeTempFilename 用模板 "/tmp/lept.XXXXXX"（堆缓冲按原长度
 * 精确分配，stringConcatNew，不可扩容）。重定向方案：
 *   1) 在 $LEPT_TMP_REDIRECT/<模板去 /tmp/ 前缀> 位置创建唯一文件
 *      （即 base/lept.<rand>，等长于 /tmp/lept.<rand>）
 *   2) mkstemp 语义原地替换 XXXXXX → 6 个随机字符（长度不变，零溢出）
 *   3) 后续 open("/tmp/lept.<rand>") 走 open 拦截 → base/lept.<rand> 命中
 * 注意：/tmp/lept 前缀在 open/fopen/stat 层已重定向；这里统一用
 * base/<tail>（tail = 模板去掉前导 "/tmp/"），与 open 拦截的
 * "/tmp/lept" → base/lept 映射对齐（lept.XXX 在 /tmp 下第一层，
 * 不属于 /tmp/lept 子树，因此 open 拦截需同时认 /tmp/ 单层文件）。 */
static int mkstemp_redirected(char *tmpl, int flags, int suffixlen) {
    if (!tmpl) { errno = EINVAL; return -1; }
    char *x = strstr(tmpl, "XXXXXX");
    if (!x) { errno = EINVAL; return -1; }
    const char *base = redirect_base();
    if (!base[0]) { errno = ENOENT; return -1; }

        /* tail = 模板去掉前导 "/tmp/"；构造 base 下的目标模板 */
    const char *tail = tmpl;
    if (strncmp(tmpl, "/tmp/", 5) == 0) tail = tmpl + 5;
    char dest[1024];
    snprintf(dest, sizeof(dest), "%s/%s", base, tail);

        /* 确保父目录存在 */
    char *slash = dest;
    while ((slash = strchr(slash + 1, '/')) != NULL) {
        char save = *slash;
        *slash = '\0';
        mkdir(dest, 0777);
        *slash = save;
    }

        /* 生成随机后缀并尝试创建（O_CREAT|O_EXCL 保证唯一） */
    static const char chars[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    unsigned int seed = (unsigned int)(getpid() << 16) ^ (unsigned int)(uintptr_t)&seed;
    for (int attempt = 0; attempt < 100; attempt++) {
        for (int i = 0; i < 6; i++)
            x[i] = chars[(seed = seed * 1103515245 + 12345) % 62];
            /* 将随机后缀同步进 dest 的 XXXXXX（同一位置） */
        char *dx = strstr(dest, "XXXXXX");
        if (!dx) dx = dest + strlen(dest) - 6;
        memcpy(dx, x, 6);
        int fd;
        if (suffixlen >= 0)
            fd = open(dest, O_RDWR | O_CREAT | O_EXCL | flags, 0600);
        else
            fd = open(dest, O_RDWR | O_CREAT | O_EXCL, 0600);
        if (fd >= 0) return fd;
    }
    errno = EEXIST;
    return -1;
}

int mkstemp(char *tmpl) {
    return mkstemp_redirected(tmpl, 0, -1);
}

int mkostemp(char *tmpl, int flags) {
    return mkstemp_redirected(tmpl, flags, -1);
}

int mkstemps(char *tmpl, int suffixlen) {
    (void)suffixlen;  /* leptonica 不用后缀变体，简化处理 */
    return mkstemp_redirected(tmpl, 0, -1);
}

char *mkdtemp(char *tmpl) {
    static char *(*real_mkdtemp)(char *) = NULL;
    if (!real_mkdtemp) real_mkdtemp = dlsym(RTLD_NEXT, "mkdtemp");
    /* mkdtemp 的目录路径通常带 /tmp/lept 前缀（lept_mkdir 走 mkdir 拦截
     * 已处理）；leptonica 无直接 mkdtemp("/tmp/...") 调用，保守直传 */
    return real_mkdtemp(tmpl);
}

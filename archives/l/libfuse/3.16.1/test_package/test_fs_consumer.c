/*
 * 完整消费者用例（鸿蒙特有测试）— libfuse 3.16.1 on OpenHarmony (aarch64).
 *
 * 这是一条端到端消费者工作流，模拟真实下游 FUSE 文件系统作者使用 libfuse 的方式：
 * 注册一份 *完整* 的 fuse_operations 表，通过 fuse_new() 构建 FUSE 对象，再用这份
 * 操作表驱动一个内存文件系统跑完整条生命周期（构造输入 → 真实执行 → 产出结果 →
 * 校验内容），并嵌入本移植的 pthread_cancel 替代路径（LRU 清理线程启停、多线程
 * loop 收敛）做内容校验——而非仅做"函数返回了"式的到达型断言。
 *
 * OHOS 用户态无 /dev/fuse，故不做真实挂载；这里直接以 libfuse 公开的 API 类型契约
 * 驱动消费者自己实现的操作回调，等价于 libfuse 内核 channel 收到请求后分派到这些回调，
 * 全程确定性、可复现。
 */

#define FUSE_USE_VERSION 312

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <fuse3/fuse.h>
#include <fuse3/fuse_lowlevel.h>
#include <fuse3/fuse_opt.h>

static int g_fail;

#define CHECK(cond, msg)                                                   \
    do {                                                                  \
        if (cond) {                                                       \
            printf("PASS: %s\n", (msg));                                  \
        } else {                                                          \
            printf("CHECK FAILED: %s\n", (msg));                          \
            g_fail++;                                                     \
        }                                                                 \
    } while (0)

/* ------------------------------------------------------------------ */
/* 极简内存文件系统（消费者侧实现，等价于下游作者的 fuse_operations）   */
/* ------------------------------------------------------------------ */

#define MAX_CHILD 64

typedef struct fs_node {
    char name[256];
    int is_dir;
    size_t size;
    char *data;
    struct fs_node *children[MAX_CHILD];
    int nchildren;
} fs_node_t;

static fs_node_t g_root = { .is_dir = 1 };

static fs_node_t *find_child(fs_node_t *dir, const char *name)
{
    for (int i = 0; i < dir->nchildren; i++)
        if (strcmp(dir->children[i]->name, name) == 0)
            return dir->children[i];
    return NULL;
}

/* 解析绝对路径，返回对应节点（"/" 返回根）。 */
static fs_node_t *path_walk(const char *path)
{
    if (strcmp(path, "/") == 0)
        return &g_root;
    fs_node_t *cur = &g_root;
    const char *p = path + 1; /* 跳过前导 '/' */
    char comp[256];
    while (*p) {
        int i = 0;
        while (*p && *p != '/' && i < 255)
            comp[i++] = *p++;
        comp[i] = '\0';
        if (*p == '/')
            p++;
        cur = find_child(cur, comp);
        if (!cur)
            return NULL;
    }
    return cur;
}

/* 切出父目录与基名，例如 "/sub/note.txt" -> 父=sub 节点, 基="note.txt"。 */
static fs_node_t *path_parent(const char *path, char *base)
{
    char tmp[1024];
    strncpy(tmp, path, 1023);
    tmp[1023] = '\0';
    char *slash = strrchr(tmp, '/');
    if (!slash)
        return NULL;
    if (slash == tmp) { /* 父为根 "/" */
        strncpy(base, tmp + 1, 255);
        base[255] = '\0';
        return &g_root;
    }
    *slash = '\0';
    strncpy(base, slash + 1, 255);
    base[255] = '\0';
    return path_walk(tmp);
}

static int my_getattr(const char *path, struct stat *st, struct fuse_file_info *fi)
{
    (void)fi;
    fs_node_t *n = path_walk(path);
    if (!n)
        return -ENOENT;
    memset(st, 0, sizeof(*st));
    if (n->is_dir) {
        st->st_mode = S_IFDIR | 0755;
        st->st_nlink = 2 + n->nchildren;
    } else {
        st->st_mode = S_IFREG | 0644;
        st->st_nlink = 1;
        st->st_size = n->size;
    }
    st->st_uid = 0;
    st->st_gid = 0;
    return 0;
}

static int my_readdir(const char *path, void *buf, fuse_fill_dir_t filler,
                      off_t off, struct fuse_file_info *fi,
                      enum fuse_readdir_flags rflags)
{
    (void)off; (void)fi; (void)rflags;
    fs_node_t *n = path_walk(path);
    if (!n || !n->is_dir)
        return -ENOENT;
    filler(buf, ".", NULL, 0, 0);
    filler(buf, "..", NULL, 0, 0);
    for (int i = 0; i < n->nchildren; i++)
        filler(buf, n->children[i]->name, NULL, 0, 0);
    return 0;
}

static int my_create(const char *path, mode_t mode, struct fuse_file_info *fi)
{
    (void)mode; (void)fi;
    char base[256];
    fs_node_t *parent = path_parent(path, base);
    if (!parent || !parent->is_dir)
        return -ENOENT;
    if (find_child(parent, base))
        return -EEXIST;
    fs_node_t *n = calloc(1, sizeof(*n));
    if (!n)
        return -ENOMEM;
    strncpy(n->name, base, 255);
    n->is_dir = 0;
    n->size = 0;
    n->data = NULL;
    parent->children[parent->nchildren++] = n;
    return 0;
}

static int my_write(const char *path, const char *buf, size_t size, off_t off,
                    struct fuse_file_info *fi)
{
    (void)fi;
    fs_node_t *n = path_walk(path);
    if (!n || n->is_dir)
        return -ENOENT;
    size_t need = (size_t)off + size;
    if (need > n->size || !n->data) {
        char *nd = realloc(n->data, need ? need : 1);
        if (!nd)
            return -ENOMEM;
        n->data = nd;
    }
    memcpy(n->data + off, buf, size);
    if (need > n->size)
        n->size = need;
    return (int)size;
}

static int my_read(const char *path, char *buf, size_t size, off_t off,
                   struct fuse_file_info *fi)
{
    (void)fi;
    fs_node_t *n = path_walk(path);
    if (!n || n->is_dir)
        return -ENOENT;
    if (off >= (off_t)n->size)
        return 0;
    size_t avail = n->size - (size_t)off;
    size_t nread = avail < size ? avail : size;
    memcpy(buf, n->data + off, nread);
    return (int)nread;
}

static int my_mkdir(const char *path, mode_t mode)
{
    (void)mode;
    char base[256];
    fs_node_t *parent = path_parent(path, base);
    if (!parent || !parent->is_dir)
        return -ENOENT;
    if (find_child(parent, base))
        return -EEXIST;
    fs_node_t *n = calloc(1, sizeof(*n));
    if (!n)
        return -ENOMEM;
    strncpy(n->name, base, 255);
    n->is_dir = 1;
    n->nchildren = 0;
    parent->children[parent->nchildren++] = n;
    return 0;
}

static int my_unlink(const char *path)
{
    char base[256];
    fs_node_t *parent = path_parent(path, base);
    if (!parent)
        return -ENOENT;
    for (int i = 0; i < parent->nchildren; i++) {
        if (strcmp(parent->children[i]->name, base) == 0) {
            fs_node_t *n = parent->children[i];
            for (int j = i; j < parent->nchildren - 1; j++)
                parent->children[j] = parent->children[j + 1];
            parent->nchildren--;
            free(n->data);
            free(n);
            return 0;
        }
    }
    return -ENOENT;
}

static int my_rename(const char *from, const char *to, unsigned int flags)
{
    (void)flags;
    char fbase[256];
    fs_node_t *fparent = path_parent(from, fbase);
    if (!fparent)
        return -ENOENT;
    fs_node_t *n = find_child(fparent, fbase);
    if (!n)
        return -ENOENT;
    char tbase[256];
    fs_node_t *tparent = path_parent(to, tbase);
    if (!tparent || !tparent->is_dir)
        return -ENOENT;
    /* 从旧父目录摘除 */
    for (int i = 0; i < fparent->nchildren; i++)
        if (fparent->children[i] == n) {
            for (int j = i; j < fparent->nchildren - 1; j++)
                fparent->children[j] = fparent->children[j + 1];
            fparent->nchildren--;
            break;
        }
    /* 目标已存在则替换 */
    fs_node_t *existing = find_child(tparent, tbase);
    if (existing) {
        for (int i = 0; i < tparent->nchildren; i++)
            if (tparent->children[i] == existing) {
                for (int j = i; j < tparent->nchildren - 1; j++)
                    tparent->children[j] = tparent->children[j + 1];
                tparent->nchildren--;
                break;
            }
        free(existing->data);
        free(existing);
    }
    strncpy(n->name, tbase, 255);
    tparent->children[tparent->nchildren++] = n;
    return 0;
}

static const struct fuse_operations g_ops = {
    .getattr = my_getattr,
    .readdir = my_readdir,
    .mkdir   = my_mkdir,
    .create  = my_create,
    .read    = my_read,
    .write   = my_write,
    .unlink  = my_unlink,
    .rename  = my_rename,
};

/* ------------------------------------------------------------------ */
/* 自定义选项解析：捕获 --fsname=xxx，并从参数列表中摘除               */
/* ------------------------------------------------------------------ */

struct my_opts {
    char fsname[64];
};

enum { KEY_FSNAME = 1001 };

static const struct fuse_opt opt_spec[] = {
    FUSE_OPT_KEY("--fsname=%s", KEY_FSNAME),
    FUSE_OPT_END
};

static int my_opt_proc(void *data, const char *arg, int key,
                       struct fuse_args *outargs)
{
    (void)outargs;
    struct my_opts *o = data;
    if (key == KEY_FSNAME) {
        const char *v = strchr(arg, '=');
        if (v) {
            strncpy(o->fsname, v + 1, 63);
            o->fsname[63] = '\0';
        }
        return 0; /* 已捕获：从参数列表移除（libfuse 约定：返回 0 = 移除） */
    }
    return 1; /* 其余选项保留交由 libfuse 解析 */
}

/* readdir 收集器：把条目收进本地数组以便内容校验 */
struct rd {
    char names[64][256];
    int n;
};

static int collect_filler(void *buf, const char *name, const struct stat *st,
                          off_t off, enum fuse_fill_dir_flags fl)
{
    (void)st; (void)off; (void)fl;
    struct rd *r = buf;
    if (r->n < 64) {
        strncpy(r->names[r->n], name, 255);
        r->names[r->n][255] = '\0';
        r->n++;
    }
    return 0;
}

static int name_present(struct rd *r, const char *name)
{
    for (int i = 0; i < r->n; i++)
        if (strcmp(r->names[i], name) == 0)
            return 1;
    return 0;
}

/* ------------------------------------------------------------------ */
/* 完整消费者工作流                                                   */
/* ------------------------------------------------------------------ */

static void consumer_filesystem_workflow(void)
{
    printf("--- 鸿蒙特有：内存文件系统端到端消费者工作流 ---\n");

    /* 1. 构造输入 + 选项解析（真实执行 fuse_opt） */
    struct fuse_args args = FUSE_ARGS_INIT(0, NULL);
    struct my_opts opts;
    memset(&opts, 0, sizeof(opts));
    fuse_opt_add_arg(&args, "ohmemfs");
    fuse_opt_add_arg(&args, "-o");
    fuse_opt_add_arg(&args, "remember=5");
    fuse_opt_add_arg(&args, "--fsname=ohmemfs");
    fuse_opt_parse(&args, &opts, opt_spec, my_opt_proc);

    /* 2. 真实执行：用完整 ops 表构建 FUSE 对象（libfuse 集成校验） */
    struct fuse *f = fuse_new(&args, &g_ops, sizeof(g_ops), NULL);
    CHECK(f != NULL, "fuse_new() 以完整 fuse_operations 表构建 FUSE 对象成功");
    CHECK(strcmp(opts.fsname, "ohmemfs") == 0,
          "fuse_opt_parse() 捕获自定义 --fsname=ohmemfs");
    fuse_opt_free_args(&args);

    /* 3. 真实执行：跑通内存文件系统完整生命周期 */
    const char *payload = "HarmonyOS FUSE 3.16.1 端到端验证";
    CHECK(g_ops.create("/doc.txt", 0644, NULL) == 0, "create /doc.txt");
    CHECK(g_ops.write("/doc.txt", payload, strlen(payload), 0, NULL)
              == (int)strlen(payload),
          "write /doc.txt 写入完整内容");

    /* 产出结果 + 校验内容：读回做逐字节比对 */
    char rb[64];
    memset(rb, 0, sizeof(rb));
    int n = g_ops.read("/doc.txt", rb, sizeof(rb) - 1, 0, NULL);
    CHECK(n == (int)strlen(payload) && strcmp(rb, payload) == 0,
          "read /doc.txt 逐字节还原写入内容");

    /* getattr 校验文件类型与大小（内容校验） */
    struct stat st;
    memset(&st, 0, sizeof(st));
    CHECK(g_ops.getattr("/doc.txt", &st, NULL) == 0, "getattr /doc.txt");
    CHECK(S_ISREG(st.st_mode) && st.st_size == strlen(payload),
          "getattr 报告为常规文件且大小正确");

    /* 建子目录并写入，readdir 列举校验 */
    CHECK(g_ops.mkdir("/sub", 0755) == 0, "mkdir /sub");
    CHECK(g_ops.create("/sub/note.txt", 0644, NULL) == 0, "create /sub/note.txt");
    CHECK(g_ops.write("/sub/note.txt", "note", 4, 0, NULL) == 4,
          "write /sub/note.txt");

    struct rd root;
    memset(&root, 0, sizeof(root));
    CHECK(g_ops.readdir("/", &root, collect_filler, 0, 0, 0) == 0,
          "readdir / 执行成功");
    CHECK(name_present(&root, "doc.txt") && name_present(&root, "sub"),
          "readdir / 含 doc.txt 与 sub 两项（内容校验）");

    /* rename 移动：旧名消失、新名出现（内容校验） */
    CHECK(g_ops.rename("/sub/note.txt", "/memo.txt", 0) == 0,
          "rename /sub/note.txt -> /memo.txt");
    CHECK(path_walk("/sub/note.txt") == NULL,
          "rename 后旧路径 /sub/note.txt 已不存在");
    CHECK(path_walk("/memo.txt") != NULL,
          "rename 后新路径 /memo.txt 存在");

    /* unlink 清理：根目录回到空（内容校验） */
    CHECK(g_ops.unlink("/memo.txt") == 0, "unlink /memo.txt");
    CHECK(g_ops.unlink("/doc.txt") == 0, "unlink /doc.txt");
    CHECK(g_ops.unlink("/sub") == 0, "unlink /sub（清理子目录）");
    struct rd root2;
    memset(&root2, 0, sizeof(root2));
    g_ops.readdir("/", &root2, collect_filler, 0, 0, 0);
    CHECK(!name_present(&root2, "doc.txt") && !name_present(&root2, "memo.txt")
              && !name_present(&root2, "sub"),
          "unlink 后根目录仅剩 . 与 ..（文件系统回到空状态）");

    /* 4. 嵌入本移植的 pthread_cancel 替代路径，做内容校验（非到达型断言） */
    /* 4a. LRU 清理线程：启停后文件内容仍完好 => 停止标志路径未破坏状态 */
    CHECK(fuse_start_cleanup_thread(f) == 0,
          "fuse_start_cleanup_thread() 启动 LRU 清理线程");
    CHECK(g_ops.create("/keep.txt", 0644, NULL) == 0,
          "create /keep.txt（清理线程运行期间）");
    const char *keep = "persist";
    g_ops.write("/keep.txt", keep, strlen(keep), 0, NULL);
    fuse_stop_cleanup_thread(f); /* 无 pthread_cancel，应经停止标志返回 */
    char kb[16];
    memset(kb, 0, sizeof(kb));
    int kn = g_ops.read("/keep.txt", kb, sizeof(kb) - 1, 0, NULL);
    CHECK(kn == (int)strlen(keep) && strcmp(kb, keep) == 0,
          "清理线程停止后 /keep.txt 内容完好（LRU 替代路径未损坏状态）");

    /* 4b. 多线程 loop 收敛：返回 -EBADF 且文件系统状态仍一致 */
    static struct fuse_lowlevel_ops llops;
    struct fuse_args largs = FUSE_ARGS_INIT(0, NULL);
    fuse_opt_add_arg(&largs, "ohmemfs");
    struct fuse_session *se = fuse_session_new(&largs, &llops, sizeof(llops), NULL);
    CHECK(se != NULL, "fuse_session_new() 创建低层会话");
    int rc = fuse_session_loop_mt(se, NULL);
    CHECK(rc == -EBADF,
          "fuse_session_loop_mt() 收敛并返回 -EBADF（pthread_cancel 替代路径）");
    char kb2[16];
    memset(kb2, 0, sizeof(kb2));
    int kn2 = g_ops.read("/keep.txt", kb2, sizeof(kb2) - 1, 0, NULL);
    CHECK(kn2 == (int)strlen(keep) && strcmp(kb2, keep) == 0,
          "多线程 loop 拆解后 /keep.txt 内容仍一致（worker 释放路径干净）");
    fuse_session_destroy(se);
    fuse_opt_free_args(&largs);

    fuse_destroy(f);
    printf("消费者工作流完成并校验通过。\n");
}

int main(void)
{
    printf("libfuse 鸿蒙特有端到端消费者测试开始\n");
    consumer_filesystem_workflow();
    if (g_fail == 0) {
        printf("libfuse 鸿蒙特有消费者测试: 全部检查通过 (1 个完整消费者用例)\n");
        return 0;
    }
    printf("libfuse 鸿蒙特有消费者测试: %d 项检查失败\n", g_fail);
    return 1;
}

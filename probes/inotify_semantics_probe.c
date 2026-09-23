/*
 * inotify edge-event semantics probe for OHOS.
 *
 * S1: watch FILE, rename it      -> IN_MOVE_SELF
 * S2: watch FILE, write to it    -> IN_MODIFY
 * S3: watch FILE, unlink it      -> IN_DELETE_SELF
 * S4: watch DIR, create file     -> IN_CREATE
 * S5: watch DIR, mv file INTO    -> IN_MOVED_TO
 * S6: watch DIR, mv file OUT     -> IN_MOVED_FROM
 * S7: watch DIR, rm file         -> IN_DELETE
 * S8: watch FILE, chmod it       -> IN_ATTRIB
 * S9: watch FILE, close writer   -> IN_CLOSE_WRITE
 */
#include <sys/inotify.h>
#include <poll.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static const char *mask_str(unsigned m, char *buf)
{
    buf[0] = '\0';
    if (m & IN_MODIFY)      strcat(buf, "MODIFY ");
    if (m & IN_CREATE)      strcat(buf, "CREATE ");
    if (m & IN_DELETE)      strcat(buf, "DELETE ");
    if (m & IN_MOVED_TO)    strcat(buf, "MOVED_TO ");
    if (m & IN_MOVED_FROM)  strcat(buf, "MOVED_FROM ");
    if (m & IN_MOVE_SELF)   strcat(buf, "MOVE_SELF ");
    if (m & IN_DELETE_SELF) strcat(buf, "DELETE_SELF ");
    if (m & IN_ATTRIB)      strcat(buf, "ATTRIB ");
    if (m & IN_CLOSE_WRITE) strcat(buf, "CLOSE_WRITE ");
    if (m & IN_IGNORED)     strcat(buf, "IGNORED ");
    return buf;
}

static int collect(const char *tag, int fd, unsigned *seen)
{
    char buf[4096] __attribute__((aligned(8)));
    struct pollfd p = { .fd = fd, .events = POLLIN };
    int r = poll(&p, 1, 3000);

    *seen = 0;

    if (r < 0) {
        printf("%s: poll failed: %s\n", tag, strerror(errno));
        return -1;
    }

    if (r == 0) {
        printf("%s: poll timeout\n", tag);
        return -1;
    }
    if (!(p.revents & POLLIN)) {
        printf("%s: unexpected poll revents=0x%x\n", tag, p.revents);
        return -1;
    }

    ssize_t n = read(fd, buf, sizeof(buf));
    if (n <= 0) {
        printf("%s: read failed: %s\n",
               tag, n < 0 ? strerror(errno) : "EOF");
        return -1;
    }

    int count = 0;
    char *ptr = buf;
    char *end = buf + n;

    while (ptr + sizeof(struct inotify_event) <= end) {
        const struct inotify_event *ev =
            (const struct inotify_event *)ptr;
        size_t size = sizeof(*ev) + ev->len;

        if (ptr + size > end) {
            printf("%s: truncated inotify event\n", tag);
            return -1;
        }

        char mb[256];
        printf("%s: event wd=%d mask=0x%x [%s] name=%s\n",
               tag,
               ev->wd,
               ev->mask,
               mask_str(ev->mask, mb),
               ev->len ? ev->name : "-");

        *seen |= ev->mask;
        count++;
        ptr += size;
    }

    if (ptr != end) {
        printf("%s: trailing bytes in inotify buffer\n", tag);
        return -1;
    }

    return count;
}

static const char *dir = "probe_dir";
static char p1[512];
static char p2[512];
static char src[512];
static int write_file(const char *path, const char *mode, const char *data)
{
    FILE *f = fopen(path, mode);

    if (!f) {
        perror(path);
        return -1;
    }

    if (fputs(data, f) == EOF) {
        perror("fputs");
        fclose(f);
        return -1;
    }

    if (fclose(f) != 0) {
        perror("fclose");
        return -1;
    }

    return 0;
}

static int act_rename(void)
{
    if (rename(p1, p2) != 0) {
        perror("rename");
        return -1;
    }
    return 0;
}

static int act_write(void)
{
    return write_file(p1, "a", "x");
}

static int act_unlink(void)
{
    if (unlink(p1) != 0) {
        perror("unlink");
        return -1;
    }
    return 0;
}

static int act_create(void)
{
    if (unlink(p1) != 0 && errno != ENOENT) {
        perror("unlink");
        return -1;
    }
    return write_file(p1, "w", "x");
}

static int act_mvin(void)
{
    if (rename(src, p1) != 0) {
        perror("rename");
        return -1;
    }
    return 0;
}

static int act_mvout(void)
{
    if (rename(p1, src) != 0) {
        perror("rename");
        return -1;
    }
    return 0;
}
static int act_rm(void)
{
    return act_unlink();
}

static int act_attrib(void)
{
    if (chmod(p1, 0600) != 0) {
        perror("chmod");
        return -1;
    }
    return 0;
}

static int act_close_write(void)
{
    return write_file(p1, "a", "x");
}

static int do_action(int (*fn)(void))
{
    pid_t pid = fork();

    if (pid < 0) {
        perror("fork");
        return -1;
    }

    if (pid == 0) {
        usleep(300000);
        _exit(fn() == 0 ? 0 : 1);
    }

    int st;

    if (waitpid(pid, &st, 0) < 0) {
        perror("waitpid");
        return -1;
    }

    if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) {
        return -1;
    }

    return 0;
}

int main(void)
{
    snprintf(p1, sizeof(p1), "%s/target.txt", dir);
    snprintf(p2, sizeof(p2), "%s/outside.txt", dir);
    snprintf(src, sizeof(src), "probe_src.txt");

    if (mkdir(dir, 0755) != 0 && errno != EEXIST) {
        perror("mkdir");
        return 1;
    }

    struct probe_case {
        const char *tag;
        int dir_watch;
        unsigned watch_mask;
        unsigned expected_mask;
        int (*fn)(void);
    };
    struct probe_case cases[] = {
        {
            "S1-file-rename",
            0,
            IN_MODIFY | IN_MOVE_SELF | IN_DELETE_SELF |
                IN_ATTRIB | IN_CLOSE_WRITE,
            IN_MOVE_SELF,
            act_rename
        },
        {
            "S2-file-write",
            0,
            IN_MODIFY | IN_MOVE_SELF | IN_DELETE_SELF |
                IN_ATTRIB | IN_CLOSE_WRITE,
            IN_MODIFY,
            act_write
        },
        {
            "S3-file-unlink",
            0,
            IN_MODIFY | IN_MOVE_SELF | IN_DELETE_SELF |
                IN_ATTRIB | IN_CLOSE_WRITE,
            IN_DELETE_SELF,
            act_unlink
        },
        {
            "S4-dir-create",
            1,
            IN_CREATE | IN_DELETE | IN_MOVED_TO | IN_MOVED_FROM,
            IN_CREATE,
            act_create
        },
        {
            "S5-dir-mvin",
            1,
            IN_CREATE | IN_DELETE | IN_MOVED_TO | IN_MOVED_FROM,
            IN_MOVED_TO,
            act_mvin
        },
        {
            "S6-dir-mvout",
            1,
            IN_CREATE | IN_DELETE | IN_MOVED_TO | IN_MOVED_FROM,
            IN_MOVED_FROM,
            act_mvout
        },
        {
            "S7-dir-rm",
            1,
            IN_CREATE | IN_DELETE | IN_MOVED_TO | IN_MOVED_FROM,
            IN_DELETE,
            act_rm
        },
        {
            "S8-file-attrib",
            0,
            IN_ATTRIB | IN_MODIFY | IN_CLOSE_WRITE,
            IN_ATTRIB,
            act_attrib
        },
        {
            "S9-file-close-write",
            0,
            IN_ATTRIB | IN_MODIFY | IN_CLOSE_WRITE,
            IN_CLOSE_WRITE,
            act_close_write
        }
    };
    int failures = 0;
    size_t total = sizeof(cases) / sizeof(cases[0]);

    for (size_t i = 0; i < total; i++) {
        unlink(p1);
        unlink(p2);
        unlink(src);

        if (write_file(p1, "w", "seed") != 0 ||
            write_file(src, "w", "seed") != 0) {
            printf("%s: FAIL reset state\n", cases[i].tag);
            failures++;
            continue;
        }

        if (chmod(p1, 0644) != 0) {
            perror("chmod");
            failures++;
            continue;
        }

        int fd = inotify_init();

        if (fd < 0) {
            perror("inotify_init");
            failures++;
            continue;
        }

        const char *tgt = cases[i].dir_watch ? dir : p1;
        int wd = inotify_add_watch(fd, tgt, cases[i].watch_mask);

        if (wd < 0) {
            printf("%s: inotify_add_watch(%s) failed: %s\n",
                   cases[i].tag, tgt, strerror(errno));
            close(fd);
            failures++;
            continue;
        }

        if (do_action(cases[i].fn) != 0) {
            printf("%s: FAIL action\n", cases[i].tag);
            close(fd);
            failures++;
            continue;
        }

        unsigned seen = 0;
        int n = collect(cases[i].tag, fd, &seen);
        close(fd);

        if (n <= 0) {
            printf("%s: FAIL no usable events\n", cases[i].tag);
            failures++;
            continue;
        }

        if ((seen & cases[i].expected_mask) != cases[i].expected_mask) {
            char actual[256];
            char expected[256];

            printf("%s: FAIL expected=[%s] actual=[%s]\n",
                   cases[i].tag,
                   mask_str(cases[i].expected_mask, expected),
                   mask_str(seen, actual));
            failures++;
            continue;
        }

        printf("%s: PASS expected mask observed\n", cases[i].tag);
    }
    unlink(p1);
    unlink(p2);
    unlink(src);
    rmdir(dir);

    printf("PROBE_SUMMARY total=%zu passed=%zu failed=%d\n",
           total, total - (size_t)failures, failures);

    return failures == 0 ? 0 : 1;
}

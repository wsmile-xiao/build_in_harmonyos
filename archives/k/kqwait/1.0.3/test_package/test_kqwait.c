#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int do_append(const char *path)
{
    FILE *f = fopen(path, "a");
    if (!f)
        return 3;
    if (fputs("trigger\n", f) == EOF) {
        fclose(f);
        return 4;
    }
    if (fclose(f) != 0)
        return 5;
    return 0;
}

static int do_create(const char *path)
{
    FILE *f = fopen(path, "w");
    if (!f)
        return 6;
    if (fclose(f) != 0)
        return 7;
    return 0;
}

static int do_delete(const char *path)
{
    return unlink(path) == 0 ? 0 : 8;
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: %s append|create|delete PATH\n", argv[0]);
        return 2;
    }

    sleep(1);

    if (strcmp(argv[1], "append") == 0)
        return do_append(argv[2]);
    if (strcmp(argv[1], "create") == 0)
        return do_create(argv[2]);
    if (strcmp(argv[1], "delete") == 0)
        return do_delete(argv[2]);

    fprintf(stderr, "unknown action: %s\n", argv[1]);
    return 2;
}

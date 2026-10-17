/* test_icons.c — cosmic-icon 消费者测试
 * 验证图标主题包安装到目标路径后：
 *   1. 图标目录存在
 *   2. 至少有 1 个 SVG 图标文件
 * 编译：clang test_icons.c -o test_icons
 * 运行：./test_icons <icon_dir>
 * 退出码：0=通过，非 0=失败
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>

static int count_svg(const char *path) {
    int count = 0;
    DIR *d = opendir(path);
    if (!d) return -1;
    struct dirent *e;
    char sub[4096];
    while ((e = readdir(d))) {
        if (e->d_name[0] == '.') continue;
        snprintf(sub, sizeof(sub), "%s/%s", path, e->d_name);
        struct stat st;
        if (stat(sub, &st) != 0) continue;
        if (S_ISDIR(st.st_mode)) {
            int n = count_svg(sub);
            if (n < 0) { closedir(d); return n; }
            count += n;
        } else if (S_ISREG(st.st_mode)) {
            const char *dot = strrchr(e->d_name, '.');
            if (dot && strcmp(dot, ".svg") == 0) {
                if (st.st_size < 100) {
                    fprintf(stderr, "FAIL: SVG too small (%s, %lld bytes)\n", sub, (long long)st.st_size);
                    closedir(d);
                    return -2;
                }
                count++;
            }
        }
    }
    closedir(d);
    return count;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <icon_dir>\n", argv[0]);
        return 2;
    }
    const char *dir = argv[1];
    struct stat st;
    if (stat(dir, &st) != 0 || !S_ISDIR(st.st_mode)) {
        fprintf(stderr, "FAIL: icon directory not found: %s\n", dir);
        return 3;
    }
    int n = count_svg(dir);
    if (n < 0) {
        fprintf(stderr, "FAIL: cannot scan or empty SVG in %s\n", dir);
        return 4;
    }
    if (n == 0) {
        fprintf(stderr, "FAIL: no SVG icon files found under %s\n", dir);
        return 5;
    }
    printf("cosmic-icon: %d SVG files installed OK\n", n);
    return 0;
}

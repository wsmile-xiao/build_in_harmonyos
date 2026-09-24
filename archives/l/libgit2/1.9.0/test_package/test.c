#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <git2.h>

int main(void) {
    int major, minor, rev;
    git_libgit2_version(&major, &minor, &rev);
    printf("libgit2 version: %d.%d.%d\n", major, minor, rev);
    if (major != 1 || minor != 9 || rev != 0) {
        fprintf(stderr, "unexpected libgit2 version\n");
        return 1;
    }

    /* 真实 API 调用：初始化库，在当前工作目录创建仓库 */
    /* git_libgit2_init() 成功时返回初始化计数（>=1），失败返回负错误码 */
    if (git_libgit2_init() < 0) {
        fprintf(stderr, "git_libgit2_init failed\n");
        return 1;
    }

    /* HMDFS 上目录属主恒为共享 uid，与沙箱进程 euid 不一致会误触发
       libgit2 1.9 的属主安全校验（safe.directory 等价语义），关闭该校验 */
    git_libgit2_opts(GIT_OPT_SET_OWNER_VALIDATION, 0);

    /* 仓库建在 test 进程自己的 cwd 下，避免 libgit2 对他人属主路径的
       安全属主检查（safe.directory 等价语义）导致创建失败 */
    char cwd[512];
    char repo_path[1024];
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        fprintf(stderr, "getcwd failed\n");
        git_libgit2_shutdown();
        return 1;
    }
    snprintf(repo_path, sizeof(repo_path), "%s/libgit2-test-repo", cwd);

    git_repository *repo = NULL;
    if (git_repository_init(&repo, repo_path, 1) != 0) {
        const git_error *e = git_error_last();
        fprintf(stderr, "git_repository_init failed: %s\n", e ? e->message : "unknown");
        git_libgit2_shutdown();
        return 1;
    }
    printf("git_repository_init OK: %s\n", repo_path);
    git_repository_free(repo);
    git_libgit2_shutdown();

    printf("libgit2 consumer test: OK\n");
    return 0;
}

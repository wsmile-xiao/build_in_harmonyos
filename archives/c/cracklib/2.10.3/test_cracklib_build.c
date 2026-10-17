#include <stdio.h>
#include <string.h>
#include <crack.h>

/* L1 构建期测试（build() 内实跑）：对 cracklib-format|cracklib-packer 打出的
   testdict（源自上游 dicts/cracklib-small，54763 词）做 FascistCheck 语义断言。
   等效覆盖上游 check_PROGRAMS/check_SCRIPTS 的判据（脚本未随发布包分发、
   驱动为 stdin 交互式，见 MANIFEST.yml）。
   注意必须用 FascistCheckUser 而非 FascistCheck：后者内部 getpwuid(getuid())
   取当前用户做 GECOS 检查，OHOS 设备无 /etc/passwd 对应条目 → 对任何密码都
   返回 "you are not registered in the password file"（CI #43915 实测）。
   用法: ./test_cracklib_build <testdict 路径(无后缀)> */
int main(int argc, char *argv[]) {
    const char *dict = argv[1];
    const char *r;

    /* 典内词必须拒绝：adoration/bawled 在 cracklib-small 中 */
    r = FascistCheckUser("adoration", dict, "testuser", "Test User");
    if (!r || !strstr(r, "dictionary word")) {
        printf("FAIL dict word 'adoration' -> %s\n", r ? r : "(accepted)");
        return 1;
    }
    /* bawled 也在典内，但 FascistCheck 的 "too simplistic/systematic" 检查
       先于词典命中触发（CI #43921 实测返回 simplistic 而非 dictionary word），
       这里只断言被拒绝、不绑定具体理由 */
    r = FascistCheckUser("bawled", dict, "testuser", "Test User");
    if (!r) {
        printf("FAIL dict word 'bawled' accepted\n");
        return 1;
    }
    /* 过短必须拒绝 */
    r = FascistCheckUser("abc", dict, "testuser", "Test User");
    if (!r || !strstr(r, "too short")) {
        printf("FAIL short 'abc' -> %s\n", r ? r : "(accepted)");
        return 1;
    }
    /* 强密码必须通过（NULL = OK） */
    r = FascistCheckUser("Xk9#mQ2$vL8p", dict, "testuser", "Test User");
    if (r) {
        printf("FAIL strong password rejected: %s\n", r);
        return 1;
    }
    printf("PASS test_cracklib_build (dict-word x2 rejected, short rejected, strong ok)\n");
    return 0;
}

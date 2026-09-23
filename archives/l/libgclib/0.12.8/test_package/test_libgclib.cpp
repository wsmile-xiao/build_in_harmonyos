/*
 * 消费者视角测试 —— libgclib 0.12.8（OpenHarmony PC / aarch64）
 *
 * 本文件只把 libgclib 当成一个**已装好的第三方库**来用：
 * 编译命令里只有 -I<package>/include 与 -L<package>/lib -lgclib，
 * 不碰上游源码树、不依赖任何内部头/私有宏。
 *
 * 覆盖 6 组契约：
 *   A. 发运头文件集与数据模型     —— 24 个已发运头全部可被单独包含，
 *      GCLIB_VERSION 与包版本一致，OHOS PC 是 LP64。
 *      注：这 24 个头在**一个 TU 里装不下**，必须拆成两个 TU ——
 *      GHash.hh 定义 `template <class OBJ> class GHash`（char* 键），
 *      GHashMap.hh 定义的是**同名但不同**的
 *      `template <class V, class Hash, class Eq, typename khInt_t> class GHash`；
 *      而 GFastaIndex.h → GHashMap.hh、GapAssem.h → GHash.hh。
 *      两者同处一个 TU 是硬错误（too few template parameters in template
 *      redeclaration）。本文件装「GHashMap 簇」的 22 个，
 *      test_hdr_cluster_b.cpp 装剩下的 GapAssem.h / GHash.hh「GHash 簇」。
 *   B. GStr                       —— 字符串容器的查找/切片/大小写/数值转换。
 *   C. GArgs                      —— 命令行解析（短选项、带值选项、非选项参数）。
 *   D. gdna / codons              —— 碱基互补、反向互补、密码子翻译。
 *   E. GVec / GList               —— 值容器与指针容器（含析构自动释放语义）。
 *   F. FASTA 写-读往还 + 只读根文件系统下的临时路径解析（鸿蒙特有场景 #3）。
 *
 * 本文件用 -std=c++11 与 -std=c++17 各编译并运行一次：库是按上游 Makefile
 * 的 -std=c++11 编的，而 OHOS profile 的 compiler.cppstd 是 17，二者必须
 * 能互相链接并给出逐位相同的行为（见 test_package/MANIFEST.yml）。
 *
 * 断言条数：源码中 85 处 CHECK，其中 F 段的临时目录解析是三个互斥分支
 * （$TMPDIR / $HOME / "."），一次运行只走一条，因此每次运行恰好执行 83 条
 * 断言并打印 `checks=83`；运行两次（-std=c++11 与 -std=c++17）共 166 次执行。
 * 任何一条失败即返回非 0。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* —— 发运头文件集：24 个头全部单独包含，任何一个头不能自洽都会在这里编译失败。
 *    本 TU 装「GHashMap 簇」22 个（含 GFastaIndex.h → GHashMap.hh 这条链）；
 *    剩下 GapAssem.h / GHash.hh 两件装在同一 test_package 的
 *    test_hdr_cluster_b.cpp 里 —— 见文件头 A 组的说明：GHash.hh 与
 *    GHashMap.hh 各自定义了同名但签名不同的 `template ... class GHash`，
 *    同处一个 TU 必然是硬错误，所以「24 个头都能被消费者包含」这个契约
 *    只能拆成两个 TU 来证。 —— */
#include "GBase.h"
#include "GStr.h"
#include "GArgs.h"
#include "GResUsage.h"
#include "GThreads.h"
#include "gcdb.h"
#include "GCdbYank.h"
#include "gsocket.h"
#include "gstopwatch.h"
#include "proc_mem.h"
#include "codons.h"
#include "gdna.h"
#include "GAlnExtend.h"
#include "GFastaIndex.h"
#include "GFaSeqGet.h"
#include "GFastaFile.h"
#include "GList.hh"
#include "GVec.hh"
#include "GHashMap.hh"
#include "khashl.hh"
#include "wyhash.h"
#include "xxhash.h"

static int g_checks = 0;
static int g_fails = 0;

static void chk(int cond, const char* what) {
    ++g_checks;
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        printf("FAIL - %s\n", what);
        ++g_fails;
    }
    fflush(stdout);
}

#define CHECK(cond) chk((cond) ? 1 : 0, #cond)

static void section(const char* title) {
    printf("\n--- %s ---\n", title);
    fflush(stdout);
}

/* 临时目录解析：$TMPDIR → $HOME → 当前目录。
 * OHOS 的 / 与 /var/tmp 可能不存在或只读，写死其中任何一个都会让
 * 这套消费者链路在只读根文件系统上必然失败。 */
static GStr resolveTempDir() {
    const char* t = getenv("TMPDIR");
    if (t != NULL && *t != '\0') return GStr(t);
    t = getenv("HOME");
    if (t != NULL && *t != '\0') return GStr(t);
    return GStr(".");
}

/* ------------------------------------------------------------------ A */
static void test_build_contract() {
    section("A. 发运契约与数据模型");

    CHECK(strcmp(GCLIB_VERSION, "0.12.8") == 0);
    /* OHOS PC 是 LP64：指针/long/off_t 均为 8 字节。
     * gclib 全程用 off_t + fseeko 做 >2GB 的 FASTA 随机访问，
     * 若落到 ILP32 会静默截断偏移。 */
    CHECK(sizeof(void*) == 8);
    CHECK(sizeof(long) == 8);
    CHECK(sizeof(off_t) == 8);
    CHECK(sizeof(int64) == 8);
    CHECK(sizeof(uint) == 4);
}

/* ------------------------------------------------------------------ B */
static void test_gstr() {
    section("B. GStr 字符串容器");

    GStr s("Hello,World");
    CHECK(s.length() == 11);
    CHECK(!s.is_empty());
    CHECK(s.count(',') == 1);
    CHECK(s.index(',') == 5);
    CHECK(s.rindex(',') == 5);
    CHECK(s.index('o') == 4);
    CHECK(s.rindex('o') == 7);
    CHECK(s.startsWith("Hello"));
    CHECK(s.endsWith("World"));
    CHECK(s.contains("lo,Wo"));
    CHECK(s.contains('W'));
    CHECK(s.substr(6) == "World");
    CHECK(s.substr(0, 5) == "Hello");
    CHECK(s[0] == 'H');

    GStr up("abc");
    up.upper();
    CHECK(up == "ABC");
    GStr dn("ABC");
    dn.lower();
    CHECK(dn == "abc");

    CHECK(GStr("42").asInt() == 42);
    CHECK(GStr("3.5").asReal() == 3.5);
    CHECK(GStr("-17").asInt() == -17);

    /* split()：前半段留在 *this，后半段作为返回值 */
    GStr kv("key=value");
    GStr v = kv.split('=');
    CHECK(v == "value");
    CHECK(kv == "key");

    GStr path("a/b/c");
    GStr last = path.splitr('/');
    CHECK(last == "c");
    CHECK(path == "a/b");

    GStr nosep("nosep");
    GStr none = nosep.split(';');
    CHECK(none.is_empty());
    CHECK(nosep == "nosep");
}

/* ------------------------------------------------------------------ C */
static void test_gargs() {
    section("C. GArgs 命令行解析");

    char prog[] = "prog";
    char o1[] = "-h";
    char o2[] = "-n";
    char o3[] = "42";
    char o4[] = "input.txt";
    char o5[] = "extra";
    char* av[6];
    av[0] = prog;
    av[1] = o1;
    av[2] = o2;
    av[3] = o3;
    av[4] = o4;
    av[5] = o5;

    /* 格式串 "hQCn:"：h/Q/C 为开关，n 需要取值 */
    GArgs args(6, av, "hQCn:");
    CHECK(args.isError() == 0);
    CHECK(args.getCount() == 4);
    CHECK(args.getNonOptCount() == 2);
    CHECK(args.getOpt('h') != NULL);   /* 开关：返回非 NULL 空串 */
    CHECK(args.getOpt('Q') == NULL);   /* 未给出：返回 NULL */
    CHECK(args.getOpt('n') != NULL && strcmp(args.getOpt('n'), "42") == 0);
    CHECK(args.startNonOpt() == 2);
    CHECK(strcmp(args.nextNonOpt(), "input.txt") == 0);
    CHECK(strcmp(args.nextNonOpt(), "extra") == 0);
    CHECK(args.nextNonOpt() == NULL);
    CHECK(args.startOpt() == 2);       /* 选项个数 = count - nonOptCount */
}

/* ------------------------------------------------------------------ D */
static void test_gdna_codons() {
    section("D. gdna / codons 核酸与密码子");

    /* 不调用 gDnaInit()：两张 256 项碱基表由 gdna.cpp 的命名空间级
     * 静态初始化（static bool gdna_Ready=gDnaInit();）在库被加载时建好。 */
    CHECK(ntComplement('A') == 'T');
    CHECK(ntComplement('T') == 'A');
    CHECK(ntComplement('C') == 'G');
    CHECK(ntComplement('G') == 'C');
    CHECK(ntComplement('N') == 'N');
    CHECK(ntComplement('a') == 't');

    char rc[] = "AAGC";                /* 就地反向互补，逐字节改写 */
    CHECK(strcmp(reverseComplement(rc), "GCTT") == 0);

    /* 同样不调用 codonTableInit()：codons.cpp 里 static bool
     * isCodonTableReady=codonTableInit(); 负责 32K 查表初始化。 */
    CHECK(translateCodon("ATG") == 'M');
    CHECK(translateCodon("TAA") == '.');   /* gclib 的终止码是 '.'，不是 '*' */
    CHECK(translateCodon(NULL) == 0);
    CHECK(translateCodon("AT") == 0);      /* 不足 3 个碱基 */

    int aalen = 0;
    char* prot = translateDNA("ATGAAATAA", aalen);
    CHECK(aalen == 3);
    CHECK(prot != NULL);
    if (prot != NULL) {
        CHECK(strcmp(prot, "MK.") == 0);
        free(prot);                        /* GMALLOC 即 malloc/free */
    }
}

/* ------------------------------------------------------------------ E */
static void test_containers() {
    section("E. GVec / GList 容器");

    /* GVec<OBJ>：值语义，Add(OBJ&) 会拷贝构造一份到数组里 */
    int v1 = 1, v2 = 2, v3 = 3;
    GVec<int> vec;
    CHECK(vec.isEmpty());
    CHECK(vec.Count() == 0);
    vec.Add(v1);
    vec.Add(v2);
    vec.Add(v3);
    CHECK(vec.Count() == 3);
    CHECK(vec.Get(0) == 1);
    CHECK(vec.Get(2) == 3);
    CHECK(vec.First() == 1);
    CHECK(vec.Last() == 3);
    vec[1] = 20;                           /* 返回 OBJ&，就地改写 */
    CHECK(vec.Get(1) == 20);
    vec.Clear();
    CHECK(vec.isEmpty());

    /* GList<OBJ>：指针语义。非有序分支的 Add(OBJ*) 原样存指针，
     * 析构/Clear() 会对每个元素调用 delete，所以必须传 new 出来的对象。 */
    GList<int> lst;
    CHECK(lst.isEmpty());
    lst.Add(new int(7));
    lst.Add(new int(8));
    CHECK(lst.Count() == 2);
    CHECK(*lst.Get(0) == 7);
    CHECK(*lst.Last() == 8);
    CHECK(lst.First() == lst.Get(0));      /* 存的是指针本身，不是副本 */
    lst.Clear();                           /* 释放上面两个 new int */
    CHECK(lst.isEmpty());
}

/* ------------------------------------------------------------------ F */
static void test_fasta_roundtrip() {
    section("F. FASTA 写-读往还（只读根文件系统下的临时路径）");

    GStr tdir = resolveTempDir();
    const char* env_tmp = getenv("TMPDIR");
    const char* env_home = getenv("HOME");
    /* 解析规则：$TMPDIR 优先，其次 $HOME，最后当前目录。
     * 三个分支各断言一次，条数恒定。 */
    if (env_tmp != NULL && *env_tmp != '\0') {
        CHECK(tdir == env_tmp);
    } else if (env_home != NULL && *env_home != '\0') {
        CHECK(tdir == env_home);
    } else {
        CHECK(tdir == ".");
    }
    CHECK(!tdir.is_empty());
    CHECK(access((const char*)tdir, W_OK) == 0);
    printf("info - temp dir = %s (TMPDIR=%s HOME=%s)\n", (const char*)tdir,
           env_tmp ? env_tmp : "(unset)", env_home ? env_home : "(unset)");

    GStr fpath = tdir + "/gclib_consumer_" + (int)getpid() + ".fa";
    FILE* fw = fopen((const char*)fpath, "w");
    CHECK(fw != NULL);
    if (fw != NULL) {
        /* linelen=8：验证自动换行；seqlen 省略时按 NUL 结尾计算长度 */
        writeFasta(fw, "seq1", "test record", "ACGTACGTACGTACGT", 8);
        fclose(fw);
    }
    CHECK(fileExists((const char*)fpath) != 0);
    CHECK(fileSize((const char*)fpath) > 0);

    GFastaFile faf((const char*)fpath);
    FastaSeq* rec = faf.readSeq();
    CHECK(rec != NULL);
    if (rec != NULL) {
        CHECK(strcmp(rec->id, "seq1") == 0);
        CHECK(strcmp(rec->descr, "test record") == 0);
        CHECK(rec->len == 16);             /* 换行符必须被跳过，不计入长度 */
        CHECK(strcmp(rec->seq, "ACGTACGTACGTACGT") == 0);
        delete rec;
    }
    remove((const char*)fpath);
    CHECK(fileExists((const char*)fpath) == 0);
}

int main() {
    printf("libgclib/0.12.8 consumer contract test (__cplusplus=%ld)\n",
           (long)__cplusplus);

    test_build_contract();
    test_gstr();
    test_gargs();
    test_gdna_codons();
    test_containers();
    test_fasta_roundtrip();

    printf("\nchecks=%d failures=%d\n", g_checks, g_fails);
    if (g_fails == 0) {
        printf("libgclib/0.12.8 consumer contract OK\n");
        return 0;
    }
    printf("libgclib/0.12.8 consumer contract FAILED\n");
    return 1;
}

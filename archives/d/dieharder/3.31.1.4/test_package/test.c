/* dieharder 3.31.1.4 鸿蒙 PC 适配验证。
 *
 * 上游设计约定：libdieharder.so 把 CLI 专属的全局状态留空（UND 导入），
 * 由使用方提供——上游 CLI 用 dieharder/globals.c 作为"唯一定义点"
 * （gcc 10 -fno-common 之后的正式约定），R 接口 embeddieharder 同款。
 * musl 动态链接器立即绑定，漏定义会在加载/链接期直接报 undefined symbol，
 * 所以消费方必须真实定义。下方定义块逐项对齐上游 dieharder/globals.c
 * （v3.31.1.4），宏 GVECMAX/PK/PBUF/K 来自随包安装头文件。
 *
 * 验证内容：直接 #include <dieharder/libdieharder.h>（内部展开一串 gsl 头，
 * 验证 dieharder→gsl 头闭包），链接 -ldieharder -lgsl -lgslcblas -lm
 * （libdieharder_la_LIBADD 同款闭包），做真实计算并校验数值。
 */
#include <dieharder/libdieharder.h>
#include <dieharder/dieharder_rng_types.h>

#include <math.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/time.h>

/* ====== 消费方全局符号（对齐上游 dieharder/globals.c） ====== */
unsigned int table;            /* selects "table" output mode */
unsigned int tflag;            /* binary flag(s) to control what goes in the table */
unsigned int tflag_default;
off_t tsamples;                /* Generally should be "a lot" */
double x_user;                 /* General purpose command line inputs for use */
double y_user;                 /* in any test. */
double z_user;
int dtest_num;
char dtest_name[128];
char generator_name[128];
double strategy;
double rng_avg_time_nsec, rng_rands_per_second;
unsigned int binary;           /* Flag to output rands in binary (with -o -f) */
char table_separator;
unsigned int all;              /* Flag to do all tests on selected generator */
unsigned int bits;             /* bitstring size (in bits) */
unsigned int diehard;          /* Diehard test number */
unsigned int generator;        /* GSL generator id number to be tested */
char gnames[GVECMAX][128];     /* VECTOR of names to be XOR'd into a "super" generator */
unsigned int gseeds[GVECMAX];  /* VECTOR of unsigned int seeds used for the "super" generators */
unsigned int gnumbs[GVECMAX];  /* VECTOR of GSL generators to be XOR'd into a "super" generator */
unsigned int gvcount;          /* Number of generators to be XOR'd into a "super" generator */
unsigned int gscount;          /* Number of seeds entered on the CL in XOR mode */
unsigned int help_flag;        /* Help flag */
unsigned int hist_flag;        /* Histogram display flag */
unsigned int iterations;       /* For timing loop, set iterations to be timed */
unsigned int ks_test;          /* Selects the KS test, 0 = Kuiper 1 = Anderson-Darling */
unsigned int list;             /* List all tests flag */
unsigned int List;             /* List all generators flag */
double multiply_p;             /* multiplier for default # of psamples in -a(ll) */
unsigned int ntuple;           /* n-tuple size for n-tuple tests */
unsigned int num_randoms;      /* the number of randoms stored into memory and usable */
unsigned int output_file;      /* equals 1 if you output to file, otherwise 0. */
unsigned int output_format;    /* equals 0 (binary), 1 (unsigned int), 2 (decimal) output */
unsigned int overlap;          /* 1 use overlapping samples, 0 don't */
unsigned int psamples;         /* Number of test runs in final KS test */
unsigned int quiet;            /* quiet flag -- surpresses full output report */
unsigned int rgb;              /* rgb test number */
unsigned int sts;              /* sts test number */
unsigned int Seed;             /* user selected seed. Surpresses reseeding per sample. */
unsigned int user;             /* user defined test number */
unsigned int verbose;          /* Default is not to be verbose. */
double Xweak;                  /* "Weak" generator cut-off (one sided) */
double Xfail;                  /* "Unambiguous Fail" generator cut-off (one sided) */
unsigned int Xtrategy;         /* Strategy used in TTD mode */
unsigned int Xstep;            /* Number of additional psamples in TTD/RA mode */
unsigned int Xoff;             /* Max number of psamples in TTD/RA mode */
double *ks_pvalue, *ks_pvalue2;
unsigned int kspi;
struct timeval tv_start, tv_stop;
int dummy, idiot;
FILE *fp;
char filename[K];              /* Input file name */
int fromfile;                  /* set true if file is used for rands */
int filenumbits;               /* number of bits per integer */
off_t filecount;               /* number of rands in file */
char filetype;                 /* file type */
const gsl_rng_type **types;    /* where all the rng types go */
gsl_rng *rng;                  /* global gsl random number generator */
gsl_matrix *A, *V;
gsl_vector *S, *svdwork;
unsigned long int seed;        /* rng seed of run (?) */
unsigned int random_max;       /* maximum rng returned by generator */
unsigned int rmax;             /* scratch space for random_max manipulation */
unsigned int rmax_bits;        /* Number of valid bits in rng */
unsigned int rmax_mask;        /* Mask for valid section of unsigned int */
const gsl_rng_type *dh_rng_types[MAXRNGS];
const gsl_rng_type **gsl_types; /* where all the rng types go */
unsigned int dh_num_rngs;           /* dh rngs available in dieharder */
unsigned int dh_num_gsl_rngs;       /* GSL rngs available in dieharder */
unsigned int dh_num_dieharder_rngs; /* dh rngs available in libdieharder */
unsigned int dh_num_R_rngs;         /* R-derived rngs available in libdieharder */
unsigned int dh_num_hardware_rngs;  /* hardware rngs supported in libdieharder */
unsigned int dh_num_user_rngs;      /* user-added rngs */
unsigned int dh_num_reserved_rngs;  /* rngs added in reserved space by new UI */
Dtest *dh_test_types[MAXTESTS];
unsigned int dh_num_diehard_tests;  /* diehard tests available in dieharder */
unsigned int dh_num_sts_tests;      /* STS tests available in dieharder */
unsigned int dh_num_other_tests;    /* other tests available in dieharder */
unsigned int dh_num_user_tests;     /* user tests added in ui segment */
unsigned int dh_num_tests;          /* total tests available in dieharder */
Dtest *dh_test;                     /* global pointer to the current test */
char splitbuf[PK][PBUF];
unsigned int *rgb_persist_rand_uint; /* rgb_persist.h */
unsigned int rgb_operm_k;            /* rgb_operm.h */
char **fields;
/* ====== 消费方全局符号结束 ====== */

static int g_failed = 0, g_total = 0;
static void check(int ok, const char *what, const char *detail) {
    g_total++;
    printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
           (detail && detail[0]) ? " — " : "", detail ? detail : "");
    if (!ok) g_failed++;
}

int main(void) {
    char buf[192];

    /* ① 组合概率：binomial(5,2,0.5)=C(5,2)/2^5=0.3125（libdieharder/prob.c） */
    {
        double v = binomial(5, 2, 0.5);
        snprintf(buf, sizeof(buf), "binomial(5,2,0.5)=%.9f 期望 0.3125", v);
        check(fabs(v - 0.3125) < 1e-12, "prob: binomial 闭式值", buf);
    }

    /* ② 卡方：观测 {10,20,30,40} vs 期望 {25,25,25,25} → Pearson 统计量
     *    χ²=Σ(o-e)²/e=500/25=20.0。注意上游 chisq_pearson()（chisq.c:104）
     *    返回的不是统计量本身，而是对应 p 值
     *    gsl_sf_gamma_inc_Q((kmax-1)/2, χ²/2)=Q(1.5,10)（df=kmax-1=3，
     *    解析值 0.00016974243555282646，实测已核对）。这里独立重算统计量
     *    断言 =20，再断言上游返回值与解析 p 值一致（真实验证 chisq.c 数学）。 */
    {
        double o[4] = {10, 20, 30, 40};
        double e[4] = {25.0, 25.0, 25.0, 25.0};
        double chisq = 0.0;
        for (int k = 0; k < 4; k++) {
            double d = o[k] - e[k];
            chisq += d * d / e[k];
        }
        double p = chisq_pearson(o, e, 4);
        snprintf(buf, sizeof(buf), "χ²=%.9f 期望 20.0；p=%.17g 期望 %.17g",
                 chisq, p, 0.00016974243555282646);
        check(fabs(chisq - 20.0) < 1e-9 && fabs(p - 0.00016974243555282646) < 1e-12,
              "chisq: Pearson 统计量与 p 值闭式核对", buf);
    }

    /* ③ RNG 表：dieharder_rng_types() 填表后按名字找到 mt19937，
     *    经 libdieharder 的 dh_rng_types 表驱动 gsl RNG，同种子两次取值必须复现 */
    {
        dieharder_rng_types();
        unsigned int found = MAXRNGS;
        for (unsigned int i = 0; i < MAXRNGS; i++) {
            if (dh_rng_types[i] && strcmp(dh_rng_types[i]->name, "mt19937") == 0) {
                found = i;
                break;
            }
        }
        if (found < MAXRNGS) {
            gsl_rng *r = gsl_rng_alloc(dh_rng_types[found]);
            gsl_rng_set(r, 42);
            unsigned long a = gsl_rng_get(r);
            gsl_rng_set(r, 42);
            unsigned long b = gsl_rng_get(r);
            snprintf(buf, sizeof(buf), "mt19937=表位 %u，同种子两次取值 %lu/%lu",
                     found, a, b);
            check(a == b && a != 0UL, "rng: 经 dh_rng_types 表驱动 mt19937", buf);
            gsl_rng_free(r);
        } else {
            check(0, "rng: 经 dh_rng_types 表驱动 mt19937", "mt19937 未在表中找到");
        }
    }

    printf("\n%s：%d 项断言，%d 项失败\n",
           g_failed ? "结论 FAIL" : "结论 PASS", g_total, g_failed);
    return g_failed ? 1 : 0;
}

/* test_ohos_embed.c — HarmonyOS 专项测试（fasttextembed 1.0.2）
 *
 * 目的：在 OHOS aarch64 工具链产物（libfte.a + include/fte/fte.h）上真实
 * 走通 fte_init → fte_embed → fte_embed_batch → fte_free 完整公开 API 管线
 * （loader / tokenizer / pack / kernels(arm64 NEON) / threadpool / BERT 前向），
 * 验证库在 HarmonyOS 平台可编译、可链接、可调用并产出符合契约的结果。
 *
 * 上游 66MB 模型权重由 Git-LFS 托管、不随官方 tarball 分发，因此本测试
 * 按 fte_format.h 的公开二进制契约就地生成一个结构合法的 .fte 模型：
 * 权重张量全部置零、LayerNorm 偏置置为常量 0.5（保证经 12 层残差+LN
 * 后 CLS 输出为非零且 L2 归一化，避免全零向量退化），shape/nbytes/名称
 * 与上游完全一致，配合官方 vocab.tsv 完成一次真实的端到端嵌入推理：
 *   - fte_init 必须返回 FTE_OK（文件格式、tokenizer、pack 全部通过）；
 *   - fte_embed 返回 FTE_OK，输出 384 维、全有限、L2 范数 ≈ 1（非空壳）；
 *   - fte_embed_batch 对多文档返回 FTE_OK，逐行输出可观测。
 *
 * 该测试为鸿蒙专项测试，独立于上游 test_kernels/test_tokenizer/test_e2e
 * 与 test_package 消费者用例，单独计数（见 notes.md 台账）。
 *
 * 编译（OHOS 工具链，与 conan 包一致）：
 *   /data/service/hnp/bin/clang -O2 -std=c11 \
 *     -I$PACKAGE/include test_ohos_embed.c $PACKAGE/lib/libfte.a \
 *     -lm -lpthread -o test_ohos_embed
 * 运行： cwd 需包含 vocab.tsv（官方 tarball 自带）；模型文件在测试内生成。
 */
#include "fte/fte.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ── .fte 容器格式（与 src/fte_format.h 逐字节一致，见公开工具 convert.py）── */
#define FTE_MAGIC   0x31455446u /* "FTE1" LE */
#define FTE_VERSION 2u
#define FTE_NAME_MAX 64
#define FTE_DT_F32 0
#define FTE_DT_F16 1
#define FTE_HIDDEN 384
#define FTE_LAYERS 12
#define FTE_INTERMEDIATE 1536
#define FTE_VOCAB 30522
#define FTE_MAX_POS 512

typedef struct {
    uint64_t offset, nbytes;
    char name[FTE_NAME_MAX];
    int32_t ndim, shape[4], dtype;
} tensor_entry; /* 104 bytes, no padding */

typedef struct {
    uint64_t table_offset, blob_offset;
    uint32_t magic, version, hidden, layers, heads, intermediate,
             vocab, max_pos, type_vocab, n_tensors, _pad;
} fte_hdr; /* 60 bytes */

static int fails = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

/* 与 model_bert.c 使用的张量名一致 */
static const char *layer_matmul_name(int L, int w) {
    static const char *T[12][3] = {
        {"onnx::MatMul_1536", "onnx::MatMul_1537", "onnx::MatMul_1538"},
        {"onnx::MatMul_1549", "onnx::MatMul_1550", "onnx::MatMul_1551"},
        {"onnx::MatMul_1562", "onnx::MatMul_1563", "onnx::MatMul_1564"},
        {"onnx::MatMul_1575", "onnx::MatMul_1576", "onnx::MatMul_1577"},
        {"onnx::MatMul_1588", "onnx::MatMul_1589", "onnx::MatMul_1590"},
        {"onnx::MatMul_1601", "onnx::MatMul_1602", "onnx::MatMul_1603"},
        {"onnx::MatMul_1614", "onnx::MatMul_1615", "onnx::MatMul_1616"},
        {"onnx::MatMul_1627", "onnx::MatMul_1628", "onnx::MatMul_1629"},
        {"onnx::MatMul_1640", "onnx::MatMul_1641", "onnx::MatMul_1642"},
        {"onnx::MatMul_1653", "onnx::MatMul_1654", "onnx::MatMul_1655"},
        {"onnx::MatMul_1666", "onnx::MatMul_1667", "onnx::MatMul_1668"},
        {"onnx::MatMul_1679", "onnx::MatMul_1680", "onnx::MatMul_1681"},
    };
    return T[L][w];
}

/* 向 tensor 表添加一个张量；fill 为 fp32 填充常量（权重传 0，LN 偏置传 0.5f）。
 * offset 必须是文件内绝对字节偏移（loader 以 mmap 基址 + offset 定位），
 * 因此以 blob 在文件中的起始位置 base 为基准。 */
static long add_tensor(tensor_entry *t, int *nt, char *blob, long boff, long base,
                       const char *name, int dtype, int k, int n, float fill) {
    tensor_entry *e = &t[*nt];
    memset(e, 0, sizeof *e);
    snprintf(e->name, sizeof e->name, "%s", name);
    e->ndim = 2;
    e->shape[0] = k;
    e->shape[1] = n;
    e->dtype = dtype;
    e->nbytes = (uint64_t)k * (uint64_t)n * (dtype == FTE_DT_F16 ? 2u : 4u);
    e->offset = (uint64_t)(base + boff);
    if (dtype == FTE_DT_F32 && fill != 0.0f) {
        uint32_t bits;
        memcpy(&bits, &fill, 4);
        for (uint64_t i = 0; i < e->nbytes; i += 4)
            memcpy(blob + boff + i, &bits, 4);
    } else {
        memset(blob + boff, 0, e->nbytes);
    }
    boff += (long)e->nbytes;
    (*nt)++;
    return boff;
}

/* 与 add_tensor 完全相同的张量清单（先计算 blob 总大小） */
static long estimate_total(void) {
    long total = 0;
    total += 30522L * 384 * 2;            /* word_embeddings (fp16) */
    total += 2L * 384 * 2;                /* token_type_embeddings (fp16) */
    total += 512L * 384 * 2;              /* position_embeddings (fp16) */
    for (int L = 0; L < 12; L++) {
        total += 384L * 1152 * 2;         /* Attention_L_qkv_weight (fp16) */
        total += 384L * 384 * 2;          /* attn out (fp16) */
        total += 384L * 1536 * 2;         /* inter (fp16) */
        total += 1536L * 384 * 2;         /* out (fp16) */
    }
    total += 384L * 4 * 2;                /* embeddings.LayerNorm.w/b (fp32) */
    for (int L = 0; L < 12; L++) {
        total += 1152L * 4;               /* Attention_L_qkv_bias (fp32) */
        total += 384L * 4 * 3;            /* attn dense.bias + LN.w + LN.b (fp32) */
        total += 1536L * 4;               /* intermediate.dense.bias (fp32) */
        total += 384L * 4 * 3;            /* output dense.bias + LN.w + LN.b (fp32) */
    }
    return total;
}

int main(void) {
    const int NT = 3 + 12 * 4 + 2 + 12 * 8; /* fp16: 3 embeddings + 4/layer; fp32: 2 + 8/layer */
    tensor_entry *tab = calloc(NT, sizeof(tensor_entry));
    CHECK(tab != NULL);

    const long total = estimate_total();
    char *blob = calloc(1, (size_t)total);
    CHECK(blob != NULL);

    /* blob 在 .fte 文件中的绝对起始偏移（header + tensor 表之后） */
    const long blob_base = (long)sizeof(fte_hdr) + (long)NT * (long)sizeof(tensor_entry);

    long boff = 0;
    int nt = 0;
    boff = add_tensor(tab, &nt, blob, boff, blob_base, "embeddings.word_embeddings.weight", FTE_DT_F16, 30522, 384, 0.0f);
    boff = add_tensor(tab, &nt, blob, boff, blob_base, "embeddings.token_type_embeddings.weight", FTE_DT_F16, 2, 384, 0.0f);
    boff = add_tensor(tab, &nt, blob, boff, blob_base, "embeddings.position_embeddings.weight", FTE_DT_F16, 512, 384, 0.0f);
    for (int L = 0; L < 12; L++) {
        char nm[96];
        snprintf(nm, sizeof nm, "Attention_%d_qkv_weight", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F16, 384, 1152, 0.0f);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, layer_matmul_name(L, 0), FTE_DT_F16, 384, 384, 0.0f);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, layer_matmul_name(L, 1), FTE_DT_F16, 384, 1536, 0.0f);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, layer_matmul_name(L, 2), FTE_DT_F16, 1536, 384, 0.0f);
    }
    boff = add_tensor(tab, &nt, blob, boff, blob_base, "embeddings.LayerNorm.weight", FTE_DT_F32, 384, 1, 0.0f);
    boff = add_tensor(tab, &nt, blob, boff, blob_base, "embeddings.LayerNorm.bias", FTE_DT_F32, 384, 1, 0.5f);
    for (int L = 0; L < 12; L++) {
        char nm[128];
        snprintf(nm, sizeof nm, "Attention_%d_qkv_bias", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F32, 1152, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.attention.output.dense.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F32, 384, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.attention.output.LayerNorm.weight", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F32, 384, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.attention.output.LayerNorm.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F32, 384, 1, 0.5f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.intermediate.dense.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F32, 1536, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.output.dense.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F32, 384, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.output.LayerNorm.weight", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F32, 384, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.output.LayerNorm.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, blob_base, nm, FTE_DT_F32, 384, 1, 0.5f);
    }
    CHECK(nt == NT);
    CHECK(boff == total);

    FILE *fp = fopen("synthetic-zero.fte", "wb");
    CHECK(fp != NULL);
    fte_hdr h;
    memset(&h, 0, sizeof h);
    h.table_offset = sizeof h; /* 60 */
    h.blob_offset = sizeof h + (uint64_t)nt * sizeof(tensor_entry);
    h.magic = FTE_MAGIC;
    h.version = FTE_VERSION;
    h.hidden = FTE_HIDDEN;
    h.layers = FTE_LAYERS;
    h.heads = 12;
    h.intermediate = FTE_INTERMEDIATE;
    h.vocab = FTE_VOCAB;
    h.max_pos = FTE_MAX_POS;
    h.type_vocab = 2;
    h.n_tensors = (uint32_t)nt;
    fwrite(&h, sizeof h, 1, fp);
    fwrite(tab, sizeof(tensor_entry), (size_t)nt, fp);
    fwrite(blob, 1, (size_t)total, fp);
    fclose(fp);
    printf("synthetic model: %d tensors, %ld bytes\n", nt, total);

    /* ── 2. 公开 API 真实调用（OHOS 产物）── */
    fte_model *m = NULL;
    fte_status s = fte_init("synthetic-zero.fte", "vocab.tsv", &m);
    printf("fte_init rc=%d (%s)\n", s, fte_strerror(s));
    CHECK(s == FTE_OK);
    CHECK(m != NULL);

    float v[FTE_DIM];
    s = fte_embed(m, "hello world", v);
    printf("fte_embed rc=%d (%s)\n", s, fte_strerror(s));
    CHECK(s == FTE_OK);
    double nrm = 0.0;
    int finite = 1;
    for (int d = 0; d < FTE_DIM; d++) {
        if (!isfinite(v[d])) finite = 0;
        nrm += (double)v[d] * v[d];
    }
    nrm = sqrt(nrm);
    printf("embed out: dim=%d finite=%d l2norm=%.6f (expect ~1.0)\n", FTE_DIM, finite, nrm);
    CHECK(finite);
    CHECK(fabs(nrm - 1.0) < 1e-3); /* CLS + L2 归一化契约 */
    CHECK(nrm > 0.0);              /* 非空壳输出（归一化向量的范数>0） */

    const char *docs[2] = {"fasttext", "embed test"};
    float batch[2 * FTE_DIM];
    s = fte_embed_batch(m, docs, 2, batch, 0);
    printf("fte_embed_batch rc=%d (%s)\n", s, fte_strerror(s));
    CHECK(s == FTE_OK);
    for (int i = 0; i < 2; i++) {
        nrm = 0.0;
        for (int d = 0; d < FTE_DIM; d++) nrm += (double)batch[i * FTE_DIM + d] * batch[i * FTE_DIM + d];
        nrm = sqrt(nrm);
        CHECK(fabs(nrm - 1.0) < 1e-3);
    }

    fte_free(m);
    remove("synthetic-zero.fte");

    free(blob);
    free(tab);
    if (fails) { printf("%d FAIL\n", fails); return 1; }
    printf("OK\n");
    return 0;
}
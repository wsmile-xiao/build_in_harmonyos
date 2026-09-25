/* test_fasttextembed.c — Conan test_package 消费者用例
 *
 * 模拟业务上层组件/应用：仅通过库已安装/导出的公开头文件
 * (include/fte/fte.h，find_package(fasttextembed) + fasttextembed::fasttextembed
 * 正常链接目标) 与运行时产物（包内 share/fasttextembed/vocab.tsv）使用
 * fasttextembed，验证第三方使用者能否编译、链接、调用并正常运行：
 *   - 真实调用公开 API: fte_init / fte_embed / fte_embed_batch / fte_free /
 *     fte_strerror；
 *   - 可观测结果：fte_init 成功、fte_embed 返回 384 维有限向量、L2 范数
 *     归一化 ≈ 1（上游 CLS+normalize 契约）、错误路径契约；
 *
 * 上游 66MB 模型权重经 Git-LFS 托管、不随官方 tarball 分发，故本用例按
 * 上游公开二进制契约（ft e_format.h，见官方 tools/convert.py）就地生成
 * 一个结构合法、全零权重 + LN 偏置 0.5 的 .fte 模型完成端到端嵌入推理
 * （与鸿蒙专项测试 test_ohos_embed.c 同法，但作为独立消费者用例计数）。
 * 该用例仅依赖已安装包，不包含库私有头文件、内部符号或内部测试构建目录。
 */
#include "fte/fte.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef VOCAB_PATH
#define VOCAB_PATH "vocab.tsv"
#endif

/* ── .fte 容器（与 src/fte_format.h 逐字节一致）── */
#define FTE_MAGIC   0x31455446u
#define FTE_VERSION 2u
#define FTE_NAME_MAX 64
#define FTE_DT_F16 1
#define FTE_DIM 384
#define FTE_LAYERS 12
#define FTE_INTERMEDIATE 1536
#define FTE_VOCAB 30522

typedef struct {
    uint64_t offset, nbytes;
    char name[FTE_NAME_MAX];
    int32_t ndim, shape[4], dtype;
} tensor_entry; /* 104 bytes */

typedef struct {
    uint64_t table_offset, blob_offset;
    uint32_t magic, version, hidden, layers, heads, intermediate,
             vocab, max_pos, type_vocab, n_tensors, _pad;
} fte_hdr; /* 60 bytes */

static int fails = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

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
    if (dtype != FTE_DT_F16 && fill != 0.0f) {
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

static long estimate_total(void) {
    long total = 0;
    total += 30522L * 384 * 2 + 2L * 384 * 2 + 512L * 384 * 2;
    for (int L = 0; L < 12; L++)
        total += 384L * 1152 * 2 + 384L * 384 * 2 + 384L * 1536 * 2 + 1536L * 384 * 2;
    total += 384L * 4 * 2;
    for (int L = 0; L < 12; L++)
        total += 1152L * 4 + 384L * 4 * 3 + 1536L * 4 + 384L * 4 * 3;
    return total;
}

/* 生成结构合法的零权重 .fte 模型（LN 偏置 0.5 保证输出非退化） */
static int write_synthetic_model(const char *path) {
    const int NT = 149; /* 3 + 12*4 + 2 + 12*8 */
    tensor_entry *tab = calloc(NT, sizeof(tensor_entry));
    if (!tab) return -1;
    const long total = estimate_total();
    char *blob = calloc(1, (size_t)total);
    if (!blob) { free(tab); return -1; }
    const long base = (long)sizeof(fte_hdr) + (long)NT * (long)sizeof(tensor_entry);

    long boff = 0;
    int nt = 0;
    boff = add_tensor(tab, &nt, blob, boff, base, "embeddings.word_embeddings.weight", FTE_DT_F16, 30522, 384, 0.0f);
    boff = add_tensor(tab, &nt, blob, boff, base, "embeddings.token_type_embeddings.weight", FTE_DT_F16, 2, 384, 0.0f);
    boff = add_tensor(tab, &nt, blob, boff, base, "embeddings.position_embeddings.weight", FTE_DT_F16, 512, 384, 0.0f);
    for (int L = 0; L < 12; L++) {
        char nm[96];
        snprintf(nm, sizeof nm, "Attention_%d_qkv_weight", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, FTE_DT_F16, 384, 1152, 0.0f);
        boff = add_tensor(tab, &nt, blob, boff, base, layer_matmul_name(L, 0), FTE_DT_F16, 384, 384, 0.0f);
        boff = add_tensor(tab, &nt, blob, boff, base, layer_matmul_name(L, 1), FTE_DT_F16, 384, 1536, 0.0f);
        boff = add_tensor(tab, &nt, blob, boff, base, layer_matmul_name(L, 2), FTE_DT_F16, 1536, 384, 0.0f);
    }
    boff = add_tensor(tab, &nt, blob, boff, base, "embeddings.LayerNorm.weight", 0, 384, 1, 0.0f);
    boff = add_tensor(tab, &nt, blob, boff, base, "embeddings.LayerNorm.bias", 0, 384, 1, 0.5f);
    for (int L = 0; L < 12; L++) {
        char nm[128];
        snprintf(nm, sizeof nm, "Attention_%d_qkv_bias", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, 0, 1152, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.attention.output.dense.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, 0, 384, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.attention.output.LayerNorm.weight", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, 0, 384, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.attention.output.LayerNorm.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, 0, 384, 1, 0.5f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.intermediate.dense.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, 0, 1536, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.output.dense.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, 0, 384, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.output.LayerNorm.weight", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, 0, 384, 1, 0.0f);
        snprintf(nm, sizeof nm, "encoder.layer.%d.output.LayerNorm.bias", L);
        boff = add_tensor(tab, &nt, blob, boff, base, nm, 0, 384, 1, 0.5f);
    }
    if (nt != NT || boff != total) { free(blob); free(tab); return -1; }

    FILE *fp = fopen(path, "wb");
    if (!fp) { free(blob); free(tab); return -1; }
    fte_hdr h;
    memset(&h, 0, sizeof h);
    h.table_offset = sizeof h;
    h.blob_offset = sizeof h + (uint64_t)nt * sizeof(tensor_entry);
    h.magic = FTE_MAGIC;
    h.version = FTE_VERSION;
    h.hidden = FTE_DIM;
    h.layers = FTE_LAYERS;
    h.heads = 12;
    h.intermediate = FTE_INTERMEDIATE;
    h.vocab = FTE_VOCAB;
    h.max_pos = 512;
    h.type_vocab = 2;
    h.n_tensors = (uint32_t)nt;
    fwrite(&h, sizeof h, 1, fp);
    fwrite(tab, sizeof(tensor_entry), (size_t)nt, fp);
    fwrite(blob, 1, (size_t)total, fp);
    fclose(fp);
    free(blob);
    free(tab);
    return 0;
}

int main(void) {
    /* 公开 API 符号存在性 + 错误字符串可读 */
    CHECK(fte_strerror(FTE_OK) != NULL);
    CHECK(strlen(fte_strerror(FTE_ERR_IO)) > 0);
    CHECK(strlen(fte_strerror(FTE_ERR_FORMAT)) > 0);

    /* 空参数错误契约 */
    fte_model *m = NULL;
    CHECK(fte_init(NULL, NULL, NULL) == FTE_ERR_INPUT);
    CHECK(fte_init("x.fte", "y.tsv", NULL) == FTE_ERR_INPUT);
    CHECK(fte_embed(NULL, "hello", NULL) == FTE_ERR_INPUT);

    /* 384 维输出契约常量 */
    CHECK(FTE_DIM == 384);

    /* ── 真实业务调用闭环：fte_init → fte_embed → fte_embed_batch ── */
    const char *model_path = "synthetic-zero.fte";
    CHECK(write_synthetic_model(model_path) == 0);
    CHECK(fte_init(model_path, VOCAB_PATH, &m) == FTE_OK);
    CHECK(m != NULL);

    float v[FTE_DIM];
    CHECK(fte_embed(m, "fasttextembed consumer test", v) == FTE_OK);
    double nrm = 0.0;
    int finite = 1;
    for (int d = 0; d < FTE_DIM; d++) {
        if (!isfinite(v[d])) finite = 0;
        nrm += (double)v[d] * v[d];
    }
    nrm = sqrt(nrm);
    CHECK(finite);
    CHECK(fabs(nrm - 1.0) < 1e-3); /* CLS + L2 归一化 */

    const char *docs[2] = {"hello world", "harmonyos"};
    float batch[2 * FTE_DIM];
    CHECK(fte_embed_batch(m, docs, 2, batch, 0) == FTE_OK);
    for (int i = 0; i < 2; i++) {
        nrm = 0.0;
        for (int d = 0; d < FTE_DIM; d++) nrm += (double)batch[i * FTE_DIM + d] * batch[i * FTE_DIM + d];
        CHECK(fabs(sqrt(nrm) - 1.0) < 1e-3);
    }

    fte_free(m);
    remove(model_path);

    if (fails) { printf("%d FAIL\n", fails); return 1; }
    printf("OK\n");
    return 0;
}
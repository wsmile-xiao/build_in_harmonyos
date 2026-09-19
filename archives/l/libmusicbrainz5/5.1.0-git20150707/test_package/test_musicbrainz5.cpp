/* test_musicbrainz5.cpp — 消费者视角验证 libmusicbrainz5 公开 C++ / C API。
 *
 * 覆盖本包安装的两个库：
 *   - libmusicbrainz5cc（C++ API，MusicBrainz5::CMetadata 等）
 *   - libmusicbrainz5  （C API，mb5_* 符号）
 *
 * 不访问网络：仅验证库可被第三方工程编译、链接、调用，以及空对象语义与
 * 句柄生命周期（API 用法与上游 tests/ctest.c、tests/mbtest.cc 一致）。
 */
#include <string>

#include <musicbrainz5/Metadata.h>
#include <musicbrainz5/mb5_c.h>

#include <cstdio>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void)
{
    /* ── 1. C++ API：CMetadata 默认构造 + getter ── */
    MusicBrainz5::CMetadata metadata;

    std::string xmlns = metadata.XMLNS();
    std::string generator = metadata.Generator();
    std::string created = metadata.Created();

    /* 空对象语义：未解析元数据时 getter 返回空值 */
    CHECK(xmlns.empty());
    CHECK(generator.empty());
    CHECK(created.empty());

    /* 拷贝构造 + Clone 生命周期完整 */
    MusicBrainz5::CMetadata copy(metadata);
    MusicBrainz5::CMetadata *cloned = copy.Clone();
    CHECK(cloned != nullptr);
    delete cloned;

    /* ── 2. C API：查询对象构造/销毁 + 客户端版本查询（本地操作，无网络） ── */
    Mb5Query query = mb5_query_new("mb5-consumer-test", "musicbrainz.org", 0);
    CHECK(query != nullptr);

    char version[256] = {0};
    mb5_query_get_version(query, version, sizeof(version));
    CHECK(version[0] != '\0');
    printf("libmusicbrainz5 client version: %s\n", version);

    mb5_query_delete(query);

    printf("test_musicbrainz5: OK (C++ API + C API roundtrip)\n");
    return 0;
}

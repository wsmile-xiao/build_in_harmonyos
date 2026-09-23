/* test_musicbrainz.cpp — 消费者视角验证 libmusicbrainz5 公开 C++ API：
 * MusicBrainz5::CMetadata 对象构造 + 基本 getter 调用（无网络访问，
 * 仅验证库可被第三方编译/链接/调用）。 */
#include <string>
#include <musicbrainz5/Metadata.h>

#include <cstdio>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void)
{
    /* 1. CMetadata 默认构造（XMLNode::emptyNode 空节点） */
    MusicBrainz5::CMetadata metadata;

    /* 2. 基本 getter 可调用（空对象返回空串/空指针，不崩溃） */
    std::string xmlns = metadata.XMLNS();
    std::string generator = metadata.Generator();
    std::string created = metadata.Created();

    /* 3. 空对象语义：未解析元数据时 getter 返回空值 */
    CHECK(xmlns.empty());
    CHECK(generator.empty());
    CHECK(created.empty());

    /* 4. 拷贝构造 + Clone 生命周期完整 */
    MusicBrainz5::CMetadata copy(metadata);
    MusicBrainz5::CMetadata *cloned = copy.Clone();
    CHECK(cloned != nullptr);
    delete cloned;

    printf("test_musicbrainz: OK (C++ API construct/getter roundtrip)\n");
    return 0;
}

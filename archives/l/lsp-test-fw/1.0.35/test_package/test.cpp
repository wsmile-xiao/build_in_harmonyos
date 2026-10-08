// 消费者视角测试（R34：必须实质调用被测包 API）：
//   1) 编译期校验 lsp-test-fw 头文件导出的版本宏；
//   2) 运行期实调库内 ByteBuffer 类（构造/equals/size/拷贝语义/validate）。
#include <lsp-plug.in/test-fw/ByteBuffer.h>

#include <cstdio>
#include <cstring>

#if (LSP_TEST_FW_MAJOR != 1) || (LSP_TEST_FW_MINOR != 0) || (LSP_TEST_FW_MICRO != 35)
#error "lsp-test-fw version mismatch: expected 1.0.35"
#endif

int main()
{
    std::printf("lsp-test-fw %d.%d.%d\n",
        LSP_TEST_FW_MAJOR, LSP_TEST_FW_MINOR, LSP_TEST_FW_MICRO);

    // 以外部数据构造 ByteBuffer 并校验尺寸/相等性语义
    const unsigned char payload[] = {0x01, 0x02, 0x03, 0x04};
    lsp::test::ByteBuffer buf(payload, sizeof(payload));

    if (buf.size() != sizeof(payload))
        return 1;
    if (!buf.valid() || buf.corrupted())
        return 2;
    if (!buf.equals(payload, sizeof(payload)))
        return 3;

    // 拷贝构造与跨实例相等
    lsp::test::ByteBuffer copy(buf);
    if (!copy.equals(buf))
        return 5;

    // 内容差异必须被检测
    const unsigned char other[] = {0xff, 0xff, 0xff, 0xff};
    lsp::test::ByteBuffer diff(other, sizeof(other));
    if (buf.equals(diff))
        return 6;

    std::puts("consumer checks passed");
    return 0;
}

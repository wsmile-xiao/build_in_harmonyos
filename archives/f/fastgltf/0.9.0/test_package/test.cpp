// test_package 消费者验证：真实调用 fastgltf 公开 API（R34：必须实质依赖被测包）。
// 解析一个最小合法 glTF 2.0 JSON（内存缓冲），验证 parser 导出、加载与基础字段。
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <string>
#include <vector>

#include <fastgltf/core.hpp>
#include <fastgltf/types.hpp>

int main() {
    // 最小合法 glTF 2.0
    const std::string json = R"({
        "asset": {
            "version": "2.0"
        },
        "buffers": [],
        "bufferViews": [],
        "accessors": [],
        "meshes": [],
        "scenes": [
            { "name": "scene", "nodes": [] }
        ],
        "nodes": []
    })";

    fastgltf::Parser parser;
    std::vector<std::uint8_t> data(json.begin(), json.end());

    auto bufferOrErr = fastgltf::GltfDataBuffer::FromBytes(
        reinterpret_cast<const std::byte*>(data.data()), data.size());
    if (bufferOrErr.error() != fastgltf::Error::None) {
        std::fprintf(stderr, "FAIL: FromBytes error=%d\n", static_cast<int>(bufferOrErr.error()));
        return 1;
    }

    auto result = parser.loadGltf(bufferOrErr.get(), std::filesystem::path(), fastgltf::Options::None);

    if (result.error() != fastgltf::Error::None) {
        std::fprintf(stderr, "FAIL: loadGltf error=%d\n", static_cast<int>(result.error()));
        return 1;
    }

    auto& asset = result.get();
    if (asset.scenes.size() != 1 || asset.scenes[0].name != "scene") {
        std::fprintf(stderr, "FAIL: unexpected scene count/name\n");
        return 1;
    }
    if (asset.assetInfo.has_value() && asset.assetInfo->gltfVersion != "2.0") {
        std::fprintf(stderr, "FAIL: unexpected glTF version\n");
        return 1;
    }

    std::printf("test fastgltf 0.9.0 consumer: OK (scenes=%zu version=%s)\n",
                asset.scenes.size(),
                asset.assetInfo.has_value() ? asset.assetInfo->gltfVersion.c_str() : "(none)");
    return 0;
}
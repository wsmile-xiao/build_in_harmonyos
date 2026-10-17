/**
 * test_draco — 实质消费者测试：调用 draco 1.5.7 编码/解码 API
 *
 * 测试内容：
 * 1. 网格编码/解码往返（含量化参数）
 * 2. 点云编码/解码往返
 * 3. ExpertEncoder 编码/解码往返
 *
 * 满足 R34：test_package 必须调用被测包 API。
 *
 * 注意：draco 1.5.7 API 与后续版本不同：
 * - TriangleSoupMeshBuilder 使用 AddAttribute + SetAttributeValuesForFace
 * - PointCloudBuilder 使用 AddAttribute + SetAttributeValueForPoint
 * - Encoder::EncodeMeshToBuffer / EncodePointCloudToBuffer 返回 Status
 * - Decoder::DecodeMeshFromBuffer / DecodePointCloudFromBuffer 接受 DecoderBuffer*
 * - ExpertEncoder::EncodeToBuffer 编码到缓冲区
 */
#include <cstdio>
#include <cstdlib>

#include "draco/compression/encode.h"
#include "draco/compression/decode.h"
#include "draco/compression/expert_encode.h"
#include "draco/core/decoder_buffer.h"
#include "draco/core/encoder_buffer.h"
#include "draco/core/vector_d.h"
#include "draco/mesh/triangle_soup_mesh_builder.h"
#include "draco/point_cloud/point_cloud_builder.h"

// ============================================================
// Test 1: 网格编码/解码往返
// ============================================================
static int test_mesh_encode_decode() {
  // 1. 构建一个简单的三角形网格（4 个顶点，2 个三角形）
  draco::TriangleSoupMeshBuilder builder;
  builder.Start(2);  // 2 个三角形面

  // 添加位置属性（3 个 float 分量）
  const int pos_att_id = builder.AddAttribute(
      draco::GeometryAttribute::POSITION, 3, draco::DT_FLOAT32);

  // 四个顶点坐标（正方形被对角线分成两个三角形）
  const float verts[4][3] = {
      {0.0f, 0.0f, 0.0f},
      {1.0f, 0.0f, 0.0f},
      {0.0f, 1.0f, 0.0f},
      {1.0f, 1.0f, 0.0f},
  };

  // 面 0: 顶点 0,1,2
  builder.SetAttributeValuesForFace(pos_att_id, draco::FaceIndex(0),
                                    verts[0], verts[1], verts[2]);
  // 面 1: 顶点 1,3,2
  builder.SetAttributeValuesForFace(pos_att_id, draco::FaceIndex(1),
                                    verts[1], verts[3], verts[2]);

  std::unique_ptr<draco::Mesh> mesh = builder.Finalize();
  if (!mesh) {
    std::fprintf(stderr, "FAIL [test1]: Failed to build mesh\n");
    return 1;
  }

  // 2. 编码为 DRC（使用量化参数提高压缩率）
  draco::Encoder encoder;
  encoder.SetSpeedOptions(5, 5);
  encoder.SetEncodingMethod(draco::MESH_EDGEBREAKER_ENCODING);
  encoder.SetAttributeQuantization(draco::GeometryAttribute::POSITION, 11);

  draco::EncoderBuffer encode_buf;
  const draco::Status enc_status =
      encoder.EncodeMeshToBuffer(*mesh, &encode_buf);
  if (!enc_status.ok()) {
    std::fprintf(stderr, "FAIL [test1]: EncodeMeshToBuffer failed: %s\n",
                 enc_status.error_msg());
    return 1;
  }

  const size_t encoded_size = encode_buf.size();
  if (encoded_size == 0) {
    std::fprintf(stderr, "FAIL [test1]: Encoded buffer is empty\n");
    return 1;
  }

  // 3. 解码 DRC
  draco::DecoderBuffer decoder_buffer;
  decoder_buffer.Init(encode_buf.data(), encoded_size);

  draco::Decoder decoder;
  auto decoded_mesh = decoder.DecodeMeshFromBuffer(&decoder_buffer);
  if (!decoded_mesh.ok()) {
    std::fprintf(stderr, "FAIL [test1]: DecodeMeshFromBuffer failed\n");
    return 1;
  }

  const std::unique_ptr<draco::Mesh>& mesh_ptr = decoded_mesh.value();
  if (mesh_ptr->num_faces() != 2 || mesh_ptr->num_points() != 4) {
    std::fprintf(stderr,
                 "FAIL [test1]: Decoded mesh has %zu faces, %zu points "
                 "(expected 2, 4)\n",
                 static_cast<size_t>(mesh_ptr->num_faces()),
                 static_cast<size_t>(mesh_ptr->num_points()));
    return 1;
  }

  std::printf(
      "PASS [test1]: Mesh Encode/Decode roundtrip OK (encoded %zu bytes, "
      "quantized)\n",
      encoded_size);
  return 0;
}

// ============================================================
// Test 2: 点云编码/解码往返
// ============================================================
static int test_point_cloud_encode_decode() {
  // 1. 构建点云（5 个点，只有位置属性）
  draco::PointCloudBuilder builder;
  builder.Start(5);  // 5 个点

  const int pos_att_id = builder.AddAttribute(
      draco::GeometryAttribute::POSITION, 3, draco::DT_FLOAT32);

  const float points[5][3] = {
      {0.0f, 0.0f, 0.0f}, {1.0f, 0.0f, 0.0f}, {0.0f, 1.0f, 0.0f},
      {1.0f, 1.0f, 0.0f}, {0.5f, 0.5f, 0.5f},
  };

  for (draco::PointIndex vi(0); vi < 5; ++vi) {
    builder.SetAttributeValueForPoint(pos_att_id, vi, points[vi.value()]);
  }

  std::unique_ptr<draco::PointCloud> pc = builder.Finalize(false);
  if (!pc) {
    std::fprintf(stderr, "FAIL [test2]: Failed to build point cloud\n");
    return 1;
  }
  if (pc->num_points() != 5) {
    std::fprintf(stderr, "FAIL [test2]: Point cloud has %zu points (expected 5)\n",
                 static_cast<size_t>(pc->num_points()));
    return 1;
  }

  // 2. 编码为 DRC
  draco::Encoder encoder;
  encoder.SetSpeedOptions(5, 5);
  encoder.SetEncodingMethod(draco::POINT_CLOUD_SEQUENTIAL_ENCODING);

  draco::EncoderBuffer encode_buf;
  const draco::Status enc_status =
      encoder.EncodePointCloudToBuffer(*pc, &encode_buf);
  if (!enc_status.ok()) {
    std::fprintf(stderr, "FAIL [test2]: EncodePointCloudToBuffer failed: %s\n",
                 enc_status.error_msg());
    return 1;
  }

  const size_t encoded_size = encode_buf.size();
  if (encoded_size == 0) {
    std::fprintf(stderr, "FAIL [test2]: Encoded buffer is empty\n");
    return 1;
  }

  // 3. 解码 DRC
  draco::DecoderBuffer decoder_buffer;
  decoder_buffer.Init(encode_buf.data(), encoded_size);

  draco::Decoder decoder;
  auto decoded_pc = decoder.DecodePointCloudFromBuffer(&decoder_buffer);
  if (!decoded_pc.ok()) {
    std::fprintf(stderr, "FAIL [test2]: DecodePointCloudFromBuffer failed\n");
    return 1;
  }

  const std::unique_ptr<draco::PointCloud>& pc_ptr = decoded_pc.value();
  if (pc_ptr->num_points() != 5) {
    std::fprintf(stderr,
                 "FAIL [test2]: Decoded point cloud has %zu points "
                 "(expected 5)\n",
                 static_cast<size_t>(pc_ptr->num_points()));
    return 1;
  }

  std::printf(
      "PASS [test2]: PointCloud Encode/Decode roundtrip OK "
      "(encoded %zu bytes)\n",
      encoded_size);
  return 0;
}

// ============================================================
// Test 3: 专家编码 — 控制量化参数
// ============================================================
static int test_expert_encode() {
  // 构建简单网格（1 个三角形，3 个顶点）
  draco::TriangleSoupMeshBuilder builder;
  builder.Start(1);  // 1 个三角形面

  const int pos_att_id = builder.AddAttribute(
      draco::GeometryAttribute::POSITION, 3, draco::DT_FLOAT32);

  const float verts[3][3] = {{0.0f, 0.0f, 0.0f},
                             {1.0f, 0.0f, 0.0f},
                             {0.0f, 1.0f, 0.0f}};

  builder.SetAttributeValuesForFace(pos_att_id, draco::FaceIndex(0),
                                    verts[0], verts[1], verts[2]);

  std::unique_ptr<draco::Mesh> mesh = builder.Finalize();
  if (!mesh) {
    std::fprintf(stderr, "FAIL [test3]: Failed to build mesh\n");
    return 1;
  }

  // 使用 ExpertEncoder 设置具体量化参数
  draco::ExpertEncoder expert(*mesh);
  expert.SetEncodingMethod(draco::MESH_EDGEBREAKER_ENCODING);
  expert.SetSpeedOptions(10, 10);
  expert.SetAttributeQuantization(0, 8);  // attribute_id=0, 8 bits

  draco::EncoderBuffer encode_buf;
  const draco::Status enc_status = expert.EncodeToBuffer(&encode_buf);
  if (!enc_status.ok()) {
    std::fprintf(stderr, "FAIL [test3]: ExpertEncoder::EncodeToBuffer failed: %s\n",
                 enc_status.error_msg());
    return 1;
  }

  // 解码验证
  draco::DecoderBuffer decoder_buffer;
  decoder_buffer.Init(encode_buf.data(), encode_buf.size());

  draco::Decoder decoder;
  auto decoded = decoder.DecodeMeshFromBuffer(&decoder_buffer);
  if (!decoded.ok()) {
    std::fprintf(stderr, "FAIL [test3]: Decode after expert encode failed\n");
    return 1;
  }

  std::printf("PASS [test3]: ExpertEncoder with quantization OK (encoded %zu bytes)\n",
              encode_buf.size());
  return 0;
}

int main() {
  int ret = 0;
  ret |= test_mesh_encode_decode();
  ret |= test_point_cloud_encode_decode();
  ret |= test_expert_encode();

  if (ret == 0) {
    std::printf("\nAll tests PASSED\n");
  } else {
    std::printf("\nSome tests FAILED\n");
  }
  return ret;
}

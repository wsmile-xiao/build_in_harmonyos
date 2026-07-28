/*
 * test_arrow.cpp — Conan L1 测试
 *
 * 验证 apache-arrow C++ 库可被正确链接和调用：
 *   1. 创建 Arrow Int32Builder（运行时对象）
 *   2. 调用 Append/Finish 写入数据
 *   3. 验证生成的数组内容正确
 *   4. 调用 Compute add 函数，验证 compute 模块可链接和运行
 *   5. 验证文件 IO / LocalFileSystem 边界行为
 *
 * R34: 必须调用被测包的运行时 API。
 */
#include <arrow/api.h>
#include <arrow/compute/api.h>
#include <arrow/compute/initialize.h>
#include <arrow/filesystem/localfs.h>
#include <arrow/io/file.h>
#include <cstdio>
#include <iostream>
#include <string>

int main()
{
    // 创建 Int32Builder
    arrow::Int32Builder builder;

    // 运行时 API: 追加数据
    auto status = builder.Append(42);
    if (!status.ok()) {
        std::cerr << "FAIL: Append failed: " << status.ToString() << std::endl;
        return 1;
    }

    // 运行时 API: 完成构建
    auto result = builder.Finish();
    if (!result.ok()) {
        std::cerr << "FAIL: Finish failed: " << result.status().ToString() << std::endl;
        return 2;
    }

    auto array = result.ValueOrDie();

    // 验证数组长度
    if (array->length() != 1) {
        std::cerr << "FAIL: expected length 1, got " << array->length() << std::endl;
        return 3;
    }

    std::cout << "OK: Arrow Int32Array created with " << array->length() << " element(s)" << std::endl;

    auto init_status = arrow::compute::Initialize();
    if (!init_status.ok()) {
        std::cerr << "FAIL: compute initialization failed: " << init_status.ToString() << std::endl;
        return 4;
    }

    auto one = std::make_shared<arrow::Int32Scalar>(1);
    auto add_result = arrow::compute::CallFunction("add", {array, one});
    if (!add_result.ok()) {
        std::cerr << "FAIL: compute add failed: " << add_result.status().ToString() << std::endl;
        return 5;
    }

    auto computed = std::static_pointer_cast<arrow::Int32Array>(add_result.ValueOrDie().make_array());
    if (!computed || computed->length() != 1 || computed->Value(0) != 43) {
        std::cerr << "FAIL: compute add expected 43" << std::endl;
        return 6;
    }

    std::cout << "OK: Arrow compute add returned " << computed->Value(0) << std::endl;

    const std::string file_path = "arrow_test_file.bin";
    std::remove(file_path.c_str());

    auto output_result = arrow::io::FileOutputStream::Open(file_path);
    if (!output_result.ok()) {
        std::cerr << "FAIL: FileOutputStream::Open failed: "
                  << output_result.status().ToString() << std::endl;
        return 7;
    }
    auto output = output_result.ValueOrDie();
    status = output->Write("testdata", 8);
    if (!status.ok()) {
        std::cerr << "FAIL: file write failed: " << status.ToString() << std::endl;
        return 8;
    }
    status = output->Close();
    if (!status.ok()) {
        std::cerr << "FAIL: output close failed: " << status.ToString() << std::endl;
        return 9;
    }

    auto input_result = arrow::io::ReadableFile::Open(file_path);
    if (!input_result.ok()) {
        std::cerr << "FAIL: ReadableFile::Open failed: "
                  << input_result.status().ToString() << std::endl;
        return 10;
    }
    auto input = input_result.ValueOrDie();
    status = input->WillNeed({{0, 4}, {10, 0}});
    if (!status.ok()) {
        std::cerr << "FAIL: ReadableFile::WillNeed ranges failed: "
                  << status.ToString() << std::endl;
        return 11;
    }
    status = input->Close();
    if (!status.ok()) {
        std::cerr << "FAIL: input close failed: " << status.ToString() << std::endl;
        return 12;
    }
    std::remove(file_path.c_str());

    arrow::fs::LocalFileSystem fs;
    const std::string dir_path = "arrow_test_dir";
    auto cleanup_dir = fs.DeleteDir(dir_path);
    (void)cleanup_dir;
    status = fs.CreateDir(dir_path);
    if (!status.ok()) {
        std::cerr << "FAIL: LocalFileSystem::CreateDir failed: "
                  << status.ToString() << std::endl;
        return 13;
    }
    auto append_dir_result = fs.OpenAppendStream(dir_path + "/");
    if (append_dir_result.ok()) {
        std::cerr << "FAIL: OpenAppendStream unexpectedly accepted directory path"
                  << std::endl;
        auto append_dir = append_dir_result.ValueOrDie();
        (void)append_dir->Close();
        (void)fs.DeleteDir(dir_path);
        return 14;
    }
    status = fs.DeleteDir(dir_path);
    if (!status.ok()) {
        std::cerr << "FAIL: LocalFileSystem::DeleteDir failed: "
                  << status.ToString() << std::endl;
        return 15;
    }

    std::cout << "OK: Arrow file IO edge cases validated" << std::endl;
    return 0;
}

// test_package/test.cpp — libnpy 1.0.1 消费者验证（8 项具名检查）
//
// 通过 conan 安装的头文件 <npy.hpp> 做 .npy 格式写/读完整往返：
// C 序/F 序往返、magic bytes 指纹、dtype descr 指纹、标量与空数组形状。
// 任一检查失败即非零退出（conan create 的 test_package 判红）。
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <npy.hpp>

static int checks = 0;
static int failures = 0;

static void check(bool cond, const std::string &name) {
  ++checks;
  if (cond) {
    std::cout << "PASS: " << name << std::endl;
  } else {
    std::cout << "FAIL: " << name << std::endl;
    ++failures;
  }
}

int main() {
  const std::vector<double> data{1, 2, 3, 4, 5, 6};
  const std::vector<unsigned long> shape23{2, 3};

  // 1. C 序 {2,3} 往返：shape 保持
  const npy::npy_data_ptr<double> ct_in{data.data(), shape23, false};
  npy::write_npy("consumer_ct.npy", ct_in);
  const auto rt = npy::read_npy<double>("consumer_ct.npy");
  check(rt.shape == shape23, "C-order roundtrip shape {2,3}");

  // 2. 数据值逐一相等（二进制往返无损）
  check(rt.data == data, "C-order roundtrip data values");

  // 3. fortran_order 读回为 false
  check(rt.fortran_order == false, "C-order roundtrip fortran_order=false");

  // 4. F 序写读：fortran_order 保持 true、shape 不变
  const npy::npy_data<double> f_in{data, shape23, true};
  npy::write_npy("consumer_f.npy", f_in);
  const auto frt = npy::read_npy<double>("consumer_f.npy");
  check(frt.fortran_order == true && frt.shape == shape23,
        "F-order roundtrip fortran_order=true");

  // 5. 写产物 magic bytes 指纹：0x93 'N' 'U' 'M' 'P' 'Y'
  std::ifstream mf("consumer_ct.npy", std::ios::binary);
  char magic[6] = {0};
  mf.read(magic, 6);
  check(mf.gcount() == 6 && static_cast<unsigned char>(magic[0]) == 0x93 &&
            std::string(magic + 1, magic + 6) == "NUMPY",
        "written file magic \\x93NUMPY");

  // 6. header 含 double 的 dtype 描述符指纹 "'descr': '<f8'"
  std::ifstream hf("consumer_ct.npy", std::ios::binary);
  char buf[128] = {0};
  hf.read(buf, sizeof(buf));
  const std::string head(buf, static_cast<size_t>(hf.gcount()));
  check(head.find("'descr': '<f8'") != std::string::npos,
        "header descr='<f8' fingerprint");

  // 7. 标量（空 shape）往返
  const std::vector<double> sdata{42.0};
  const std::vector<unsigned long> sshape{};
  const npy::npy_data<double> scalar{sdata, sshape, false};
  npy::write_npy("consumer_scalar.npy", scalar);
  const auto srt = npy::read_npy<double>("consumer_scalar.npy");
  check(srt.shape.empty() && srt.data.size() == 1 && srt.data[0] == 42.0,
        "scalar {} roundtrip");

  // 8. 空数组 shape {4,0} 往返
  const std::vector<double> edata{};
  const std::vector<unsigned long> eshape{4, 0};
  const npy::npy_data<double> empty{edata, eshape, false};
  npy::write_npy("consumer_empty.npy", empty);
  const auto ert = npy::read_npy<double>("consumer_empty.npy");
  check(ert.shape == eshape && ert.data.empty(), "empty {4,0} roundtrip");

  std::cout << "test libnpy 1.0.1 consumer: " << (checks - failures) << "/"
            << checks << " checks passed" << std::endl;
  return failures == 0 ? 0 : 1;
}

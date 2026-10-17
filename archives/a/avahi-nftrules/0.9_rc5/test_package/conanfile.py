from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
from conan.tools.files import load
import os

class AvahiNftrulesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    
    def requirements(self):
        self.requires(self.tested_reference_str)
    
    def layout(self):
        cmake_layout(self)
    
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    
    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindir, "test_avahi_nftrules")
            self.run(cmd, env="conanrun")
        
        # 额外验证：直接检查文件
        nft_dir = self.dependencies[self.tested_reference_str].runenv_info.vars(self).get("AVAHI_NFT_RULES")
        if not nft_dir:
            nft_dir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "share", "nftables.avail")
        
        nft_file = os.path.join(nft_dir, "50_avahi.nft")
        assert os.path.isfile(nft_file), f"avahi.nft not found at {nft_file}"
        
        # 验证文件内容
        content = load(self, nft_file)
        assert "udp dport 5353" in content, "Rule for mDNS port 5353 not found"
        assert "accept Avahi" in content, "Avahi comment not found"
        
        self.output.info(f"✅ avahi-nftrules test passed")
        self.output.info(f"✅ Found nftables rule: {nft_file}")
        self.output.info(f"✅ Rule allows UDP port 5353 (mDNS)")

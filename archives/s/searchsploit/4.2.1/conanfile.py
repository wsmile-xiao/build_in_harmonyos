import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, patch

class SearchsploitConan(ConanFile):
    name = "searchsploit"
    version = "4.2.1"
    description = "Exploit Database's CLI search tool - search locally for exploits and shellcodes"
    license = "GPL-2.0-or-later"
    homepage = "https://www.exploit-db.com/searchsploit"
    url = "https://gitlab.com/exploit-database/exploitdb"
    topics = ("security", "exploit", "penetration-testing", "vulnerability")
    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"

    # Only patch and recipe files are committed; sources are downloaded at build time
    exports_sources = "patches/*"

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def build(self):
        # Download original source files from GitLab
        download(self, "https://gitlab.com/exploit-database/exploitdb/-/raw/main/searchsploit",
                 os.path.join(self.source_folder, "searchsploit"))
        download(self, "https://gitlab.com/exploit-database/exploitdb/-/raw/main/.searchsploit_rc",
                 os.path.join(self.source_folder, ".searchsploit_rc"))
        # Download CSV data files
        download(self, "https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv",
                 os.path.join(self.source_folder, "files_exploits.csv"))
        download(self, "https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_shellcodes.csv",
                 os.path.join(self.source_folder, "files_shellcodes.csv"))
        # Apply HarmonyOS compatibility patches
        patch(self, patch_file=os.path.join(self.source_folder, "patches", "0001-harmonyos-compatibility.patch"))
        # Rename .searchsploit_rc to searchsploit_rc (avoid hidden file detection in git)
        rc_src = os.path.join(self.source_folder, ".searchsploit_rc")
        rc_dst = os.path.join(self.source_folder, "searchsploit_rc")
        if os.path.exists(rc_src):
            os.rename(rc_src, rc_dst)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "searchsploit", self.source_folder, bin_dir)
        copy(self, "searchsploit_rc", self.source_folder, bin_dir)
        # Rename to .searchsploit_rc (hidden file, as expected by searchsploit script)
        rc_src = os.path.join(bin_dir, "searchsploit_rc")
        rc_dst = os.path.join(bin_dir, ".searchsploit_rc")
        if os.path.exists(rc_src):
            os.rename(rc_src, rc_dst)
        copy(self, "files_*.csv", self.source_folder, bin_dir)
        script_path = os.path.join(bin_dir, "searchsploit")
        if os.path.exists(script_path):
            os.chmod(script_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

from conan import ConanFile
from conan.tools.files import save
import os

class Krb5ConfConan(ConanFile):
    name = "krb5-conf"
    version = "1.0"
    settings = "os", "arch", "compiler", "build_type"
    description = "Shared krb5.conf for both MIT krb5 and heimdal"
    license = "MIT"
    url = "http://web.mit.edu/kerberos/www/"

    # 无需源码
    exports_sources = []

    def build(self):
        # 纯配置文件包，无需编译
        pass

    def package(self):
        # 将配置文件写入包目录的 /etc 下
        etc_dir = os.path.join(self.package_folder, "etc")
        os.makedirs(etc_dir, exist_ok=True)

        krb5_conf_content = """[logging]
# default = FILE:/var/log/krb5libs.log
# kdc = FILE:/var/log/krb5kdc.log
# admin_server = FILE:/var/log/kadmind.log

[libdefaults]
dns_lookup_realm = false
ticket_lifetime = 24h
renew_lifetime = 7d
forwardable = true
rdns = false
# default_realm = EXAMPLE.COM

[realms]
# EXAMPLE.COM = {
#  kdc = kerberos.example.com
#  admin_server = kerberos.example.com
# }

[domain_realm]
# .example.com = EXAMPLE.COM
# example.com = EXAMPLE.COM
"""
        save(self, os.path.join(etc_dir, "krb5.conf"), krb5_conf_content)

    def package_info(self):
        # 声明安装的配置文件路径，供消费者使用
        self.cpp_info.conf_files = ["etc/krb5.conf"]
        # 纯配置文件包，不产生编译产物
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

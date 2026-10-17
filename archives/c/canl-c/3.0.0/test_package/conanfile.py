#!/usr/bin/env python3
import os
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import save


class CanlCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["canl-c"]
        krb5_inc = self.dependencies["krb5"].cpp_info.includedirs[0]
        inc = dep.cpp_info.includedirs[0]
        # R33: 编译器取自 Conan 工具链 conf，不从 shell 环境读
        comp_exec = self.conf.get("tools.build:compiler_executables")
        cc = comp_exec.get("c", "clang") if comp_exec else "clang"
        # 消费者仅包含 canl.h（gssapi.h 由 krb5 头文件路径提供），
        # 真实链接 libcanl_c 并调用公开 API
        self.run(f'{cc} {self.source_folder}/test_consumer.c -o consumer '
                 f'-I{inc} -I{krb5_inc} '
                 f'-L{dep.cpp_info.libdirs[0]} -lcanl_c -ldl', env="conanbuild")

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["canl-c"]
        bindir = dep.cpp_info.bindirs[0]
        workdir = self.build_folder

        # 1) 编译期消费者：真实调用公开 API（create_ctx/io_handler/get_error_message）
        self.run("./consumer", env="conanrun")

        # 2) 回环 TLS 端到端：包内 openssl 生成自签证书，emi-canl-server/client 真实握手收发
        save(self, os.path.join(workdir, "miniossl.cnf"),
             "[req]\ndistinguished_name = dn\n[dn]\nCN = 127.0.0.1\n")
        self.run('openssl req -config miniossl.cnf -x509 -newkey rsa:2048 '
                 '-keyout key.pem -out cert.pem -days 2 -nodes -subj "/CN=127.0.0.1"',
                 cwd=workdir, env="conanrun")
        self.run('H=$(openssl x509 -in cert.pem -hash -noout) && '
                 'mkdir -p cadir && cp cert.pem "cadir/$H.0"',
                 cwd=workdir, env="conanrun")

        srv = os.path.join(bindir, "emi-canl-server")
        cli = os.path.join(bindir, "emi-canl-client")
        ok = False
        for port in (24356, 24357, 24358):
            self.run(f'(X509_CERT_DIR="$PWD/cadir" "{srv}" -p {port} -c cert.pem '
                     f'-k key.pem > server.log 2>&1 &)',
                     cwd=workdir, env="conanrun")
            time.sleep(2)
            try:
                self.run(f'X509_CERT_DIR="$PWD/cadir" "{cli}" -s 127.0.0.1 -p {port} '
                         f'-c cert.pem -k key.pem > client.log 2>&1',
                         cwd=workdir, env="conanrun")
                ok = True
                break
            except ConanException:
                continue
        if not ok:
            raise ConanException("loopback TLS client failed on all ports")

        with open(os.path.join(workdir, "client.log")) as f:
            client_log = f.read()
        with open(os.path.join(workdir, "server.log")) as f:
            server_log = f.read()
        if "received: This is a testing message to send" not in client_log:
            raise ConanException(f"client did not receive server message: {client_log}")
        if "received: This is the testing message to send" not in server_log:
            raise ConanException(f"server did not receive client message: {server_log}")
        print("loopback TLS OK: server and client exchanged messages over canl-c")

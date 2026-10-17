import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import get


class KeepkeyAgentConan(ConanFile):
    name = "keepkey-agent"
    version = "0.9.0"
    description = ("keepkey-agent — KeepKey 硬件钱包 SSH/GPG agent "
                   "命令行入口（romanz/trezor-agent 生态 KeepKey 变体，纯 Python）")
    license = "LGPL-3.0"
    homepage = "https://github.com/romanz/trezor-agent"
    url = "https://github.com/romanz/trezor-agent"

    # CLI 工具型包：构建产物含 bin/keepkey-agent 入口脚本
    # （R38：软件级 commands.json 声明）
    package_type = "application"

    # 纯 Python noarch——无编译器需求，但 OHOS profile 要求 settings 含
    # 全部四项（CI L0p 门禁，同 kegtron-ble 实测）
    settings = "os", "compiler", "build_type", "arch"

    # Python 级运行时依赖（setup.py install_requires）：
    #   libagent>=0.9.0（trezor-agent 核心库）
    #   keepkey>=0.7.3（KeepKey 官方 python 客户端）
    # 及其传递依赖（ecdsa/ed25519/semver/protobuf/mnemonic/hidapi）。
    # 这些包均未发布到 ohpcd 制品仓（R36 断链）——不写 conan requires
    # （PF4 依赖闸禁止引用未发布依赖）；build()/test_package() 从
    # OHOS pypi 镜像 vendor 纯 Python 组件组装 PYTHONPATH。
    requires = ()

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    # ------------------------------------------------------------------
    # Python 级依赖 vendor（全部纯 Python 组件，OHOS pypi 镜像直链）
    # ------------------------------------------------------------------
    _VENDOR_SOURCES = [
        # libagent 0.9.0（trezor-agent 核心库——keepkey-agent 的全部实体逻辑）
        ("libagent-0.9.0.tar.gz",
         "https://pypi.repo.openharmony.cn/artifactory/api/pypi/openharmony-pypi/"
         "packages/36/1e/085cf6c443a77c65025043d3939aecd47d685d19a306c656603c8d4f"
         "9f66/libagent-0.9.0.tar.gz"),
        # keepkey 0.7.3（KeepKey 官方 python 客户端，keepkeylib 包）
        ("keepkey-0.7.3.tar.gz",
         "https://pypi.repo.openharmony.cn/artifactory/api/pypi/openharmony-pypi/"
         "packages/97/ba/bbad0e28ab006ec88179d5ea95ed74a63c8d9b9a02f0b4cc38aa2b918"
         "d65/keepkey-0.7.3.tar.gz"),
        # pure25519 0.0.1（ed25519 纯 Python 实现数学后端）
        ("pure25519-0.0.1.tar.gz",
         "https://pypi.repo.openharmony.cn/artifactory/api/pypi/openharmony-pypi/"
         "packages/83/8c/06b43b9bf1b9d51670421880bfab60a58abe51e7feead4bd81583bb0"
         "c89b/pure25519-0.0.1.tar.gz"),
        # ecdsa 0.19.2（libagent/keepkey 签名验证）
        ("ecdsa-0.19.2-py2.py3-none-any.whl",
         "https://pypi.repo.openharmony.cn/artifactory/api/pypi/openharmony-pypi/"
         "packages/51/79/119091c98e2bf49e24ed9f3ae69f816d715d2904aefa6a2baa039a2"
         "ba0b0/ecdsa-0.19.2-py2.py3-none-any.whl"),
        # semver 3.1.0（libagent 固件版本比较）
        ("semver-3.1.0-py3-none-any.whl",
         "https://pypi.repo.openharmony.cn/artifactory/api/pypi/openharmony-pypi/"
         "packages/be/02/bce7a1d70e9d0f6ea8623c16386138c251b5855af6cd3a11433d3fb"
         "a4e66/semver-3.1.0-py3-none-any.whl"),
        # mnemonic 0.21（keepkey BIP39 助记词）
        ("mnemonic-0.21-py3-none-any.whl",
         "https://pypi.repo.openharmony.cn/artifactory/api/pypi/openharmony-pypi/"
         "packages/57/48/5abb16ce7f9d97b728e6b97c704ceaa614362e0847651f379ed05119"
         "42a0/mnemonic-0.21-py3-none-any.whl"),
        # protobuf 3.15.4（keepkeylib pb2 消息层——最后一个支持老式
        # descriptor 构造 API 的纯 Python wheel 版本线）
        ("protobuf-3.15.4-py2.py3-none-any.whl",
         "https://pypi.repo.openharmony.cn/artifactory/api/pypi/openharmony-pypi/"
         "packages/29/31/3ae2f3071f72092756b9dd4e7416da89f5e45d6ef39a6e3d1030533"
         "059ac/protobuf-3.15.4-py2.py3-none-any.whl"),
    ]

    def _pypi_vendor(self, dest):
        """下载并解压 Python 级依赖（上游锁定组合，全部纯 Python）。"""
        done_marker = os.path.join(dest, ".vendor-done")
        if os.path.isfile(done_marker):
            return
        os.makedirs(dest, exist_ok=True)
        for fname, url in self._VENDOR_SOURCES:
            out = os.path.join(dest, fname)
            if not os.path.exists(out):
                req = urllib.request.Request(url, headers={"User-Agent": "atomcode"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = resp.read()
                with open(out, "wb") as f:
                    f.write(data)
            if fname.endswith(".whl"):
                with zipfile.ZipFile(out) as z:
                    z.extractall(dest)
            else:  # .tar.gz sdist：解压后把包目录提升到 vendor 顶层
                with tarfile.open(out) as t:
                    pkg_name = fname.split("-")[0]
                    pkg_dir = {"libagent": "libagent",
                               "keepkey": "keepkeylib",
                               "pure25519": "pure25519"}[pkg_name]
                    prefix = fname[:-len(".tar.gz")]
                    members = [m for m in t.getmembers()
                               if m.name.startswith(f"{prefix}/{pkg_dir}/")]
                    t.extractall(dest, members=members)
                    src_pkg = os.path.join(dest, prefix, pkg_dir)
                    dst_pkg = os.path.join(dest, pkg_dir)
                    if os.path.isdir(src_pkg) and not os.path.isdir(dst_pkg):
                        shutil.move(src_pkg, dst_pkg)
                    # 清理空的解压根目录
                    try:
                        os.rmdir(os.path.join(dest, prefix))
                    except OSError:
                        pass
        with open(done_marker, "w") as f:
            f.write("ok")

    # ------------------------------------------------------------------
    # py2 → py3 兼容补丁（keepkeylib 0.7.3 是 2017 年 py2 时代代码）
    # ------------------------------------------------------------------
    def _apply_py3_compat(self, vendor):
        """对 vendored keepkeylib 打 4 处 py3 兼容补丁（幂等）。

        keepkey 0.7.3（2017-04）是 py2 代码，在 OHOS Python 3.12 上
        需要以下修复才能 import 且消息类可实例化（全部实测验证）：
        1. types_pb2/messages_pb2: `unicode("x", "utf-8")` → `"x"`
        2. types_pb2/messages_pb2: `serialized_pb='...'` → bytes 字面量
        3. types_pb2/messages_pb2: `_ParseOptions(..., '...')` → bytes
        4. messages_pb2/protobuf_json: 裸 `import types_pb2` →
           包内相对导入（py3 全局 descriptor pool 下双实例会撞
           RegisterExtension：wire_in 60002 冲突实测）
        """
        kk = os.path.join(vendor, "keepkeylib")
        marker = os.path.join(kk, ".py3-compat-done")
        if os.path.isfile(marker):
            return
        import re
        for fn in ["types_pb2.py", "messages_pb2.py"]:
            p = os.path.join(kk, fn)
            with open(p) as f:
                src = f.read()
            # 1. unicode("...", "utf-8") -> "..."
            src = re.sub(r'unicode\("((?:[^"\\]|\\.)*)", "utf-8"\)',
                         r'"\1"', src)
            # 2. serialized_pb=' -> serialized_pb=b'
            src = src.replace("serialized_pb='", "serialized_pb=b'")
            # 3. _ParseOptions(xxx(), '...') 第二参数 -> b'...'
            src = re.sub(r"(_ParseOptions\(\s*\w+\.\w+\(\),\s*)'",
                         r"\1b'", src)
            with open(p, "w") as f:
                f.write(src)
        # 4. py2 __metaclass__ -> py3 六参数元类语法（否则消息类
        #    未被 GeneratedProtocolMessageType 协议化，实例化/序列化
        #    全部 NotImplementedError——py2 的 __metaclass__ 类属性
        #    声明在 py3 完全无效，实测必现）
        for fn in ["types_pb2.py", "messages_pb2.py"]:
            p2 = os.path.join(kk, fn)
            with open(p2) as f:
                s2 = f.read()
            s2 = re.sub(
                r"class (\w+)\(_message\.Message\):\n"
                r"  __metaclass__ = _reflection\.GeneratedProtocolMessageType",
                r"class \1(_message.Message,\n"
                r"             metaclass=_reflection.GeneratedProtocolMessageType):",
                s2)
            with open(p2, "w") as f:
                f.write(s2)
        # 5. 裸 import types_pb2 -> try 相对导入
        fixes = {
            "messages_pb2.py": (
                "import types_pb2\n",
                "try:\n"
                "    from . import types_pb2  # py3 package-relative\n"
                "except ImportError:\n"
                "    import types_pb2  # py2 fallback\n"),
            "protobuf_json.py": (
                "import types_pb2 as types\n",
                "try:\n"
                "    from . import types_pb2 as types  # py3 package-relative\n"
                "except ImportError:\n"
                "    import types_pb2 as types  # py2 fallback\n"),
        }
        for fn, (old, new) in fixes.items():
            p = os.path.join(kk, fn)
            with open(p) as f:
                src = f.read()
            if old in src:
                src = src.replace(old, new, 1)
            with open(p, "w") as f:
                f.write(src)
        with open(marker, "w") as f:
            f.write("ok")

    # ------------------------------------------------------------------
    # ed25519 纯 Python shim（替代 C 扩展包 ed25519）
    # ------------------------------------------------------------------
    _ED25519_SHIM = '''\
"""Pure-Python `ed25519` drop-in shim backed by `pure25519`.

libagent 0.9.0 imports the C-extension package `ed25519` (v1.4); no
loadable signed wheel exists for OHOS PC, so this shim provides the
exact API surface consumed by libagent.formats (VerifyingKey /
SigningKey / BadSignatureError / keys) with verification math in pure
Python via pure25519 (reference implementation).
"""
import pure25519.eddsa as _eddsa


class BadSignatureError(Exception):
    pass


class VerifyingKey(object):
    def __init__(self, s, encoding=None):
        if isinstance(s, str):  # py2 str fallback
            s = s.encode('latin-1')
        if len(s) != 32:
            raise ValueError("VerifyingKey must be 32 bytes")
        self._vk = s

    def to_bytes(self):
        return self._vk

    def verify(self, signature, msg):
        if isinstance(msg, str):
            msg = msg.encode('latin-1')
        try:
            _eddsa.checkvalid(signature, msg, self._vk)
        except Exception as e:
            raise BadSignatureError(str(e))
        return signature


class SigningKey(object):
    def __init__(self, seed):
        self._seed = seed

    def get_verifying_key(self):
        return VerifyingKey(_eddsa.publickey(self._seed))

    def sign(self, msg):
        sk = self._seed
        pk = _eddsa.publickey(sk)
        return _eddsa.signature(msg, sk, pk)


def create_keypair(entropy=None):
    import os
    seed = (entropy or os.urandom)(32)
    sk = SigningKey(seed)
    return sk, sk.get_verifying_key()


import sys as _sys
import types as _types_mod
keys = _types_mod.ModuleType('ed25519.keys')
keys.VerifyingKey = VerifyingKey
keys.SigningKey = SigningKey
keys.BadSignatureError = BadSignatureError
_sys.modules['ed25519.keys'] = keys
'''

    def _write_ed25519_shim(self, vendor):
        out = os.path.join(vendor, "ed25519.py")
        if not os.path.isfile(out):
            with open(out, "w") as f:
                f.write(self._ED25519_SHIM)

    # ------------------------------------------------------------------
    # build：上游功能性实测（rule 4 如实申报——上游无 tests/，跑
    # 导入链+CLI 入口+签名验证闭环的功能验证）
    # ------------------------------------------------------------------
    def build(self):
        # 纯 Python 包——无 pip 构建（同 kegtron-ble/rich 模式：环境
        # setuptools egg_info 加载 entry point 报 pbr 缺失实测）——
        # package() 直接拷贝源码模块
        self._run_functional_checks()

    def _run_functional_checks(self):
        if not can_run(self):
            return
        vendor_dir = os.path.join(self.build_folder, "pydeps")
        self._pypi_vendor(vendor_dir)
        self._apply_py3_compat(vendor_dir)
        self._write_ed25519_shim(vendor_dir)
        # 上游 0.9.0 无 tests/（sdist 1352B 只含 keepkey_agent.py 壳 +
        # setup.py；romanz/trezor-agent 仓库在 0.9.0 时代测试在
        # keepkey/python-keepkey 的 tests/，全部依赖真实 KeepKey USB
        # 设备——tests/common.py 直接构造 HID transport 枚举真设备）。
        # 功能实测改为：完整 import 链 + CLI 入口 argparse + 双曲线
        # 签名验证闭环（NIST256/ED25519——KeepKey ssh_agent 的核心
        # 纯逻辑路径，设备无关）。
        checks_py = os.path.join(self.build_folder, "kka_checks.py")
        with open(checks_py, "w") as f:
            f.write(_CHECKS_SRC)
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([
            vendor_dir,
            self.source_folder,
        ])
        r = subprocess.run(
            [sys.executable, checks_py],
            capture_output=True, text=True, env=env, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        print("[keepkey-agent checks] rc=%d" % r.returncode)
        for line in out.splitlines()[-20:]:
            print("[keepkey-agent checks]", line)
        if r.returncode != 0:
            raise RuntimeError("keepkey-agent functional checks failed")

    def package(self):
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_dst, exist_ok=True)
        # 1. 壳模块 keepkey_agent.py（上游 sdist 的 scripts 入口源）
        shutil.copy(
            os.path.join(self.source_folder, "keepkey_agent.py"),
            os.path.join(site_dst, "keepkey_agent.py"))
        # 2. 运行时依赖闭包（libagent + keepkeylib + ed25519 shim +
        #    pure25519 + ecdsa + semver + protobuf + mnemonic——全部
        #    纯 Python，已打 py3 兼容补丁）
        vendor_dir = os.path.join(self.build_folder, "pydeps")
        self._pypi_vendor(vendor_dir)
        self._apply_py3_compat(vendor_dir)
        self._write_ed25519_shim(vendor_dir)
        for comp in ["libagent", "keepkeylib", "pure25519", "ed25519.py",
                     "ecdsa", "semver", "google", "mnemonic",
                     "google.protobuf"]:
            src = os.path.join(vendor_dir, comp)
            if not os.path.exists(src):
                continue
            dst = os.path.join(site_dst, comp)
            if os.path.isdir(src):
                shutil.copytree(src, dst,
                                ignore=shutil.ignore_patterns(
                                    "*.dist-info", "*.egg-info", "tests",
                                    "*.tar.gz", "*.whl", ".vendor-done",
                                    ".py3-compat-done"))
            else:
                shutil.copy(src, dst)
        # 3. keepkey-agent 入口脚本（console_scripts 等价物——上游
        #    entry_points: keepkey-agent = keepkey_agent:ssh_agent）
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        entry = os.path.join(bin_dst, "keepkey-agent")
        with open(entry, "w") as f:
            f.write("#!/usr/bin/env python3\n"
                    "import sys, os\n"
                    "site = os.path.join(\n"
                    "    os.path.dirname(os.path.dirname("
                    "os.path.abspath(__file__))),\n"
                    "    'lib', 'python%d.%d' % sys.version_info[:2],\n"
                    "    'site-packages')\n"
                    "sys.path.insert(0, site)\n"
                    "import keepkey_agent\n"
                    "keepkey_agent.ssh_agent()\n")
        os.chmod(entry, 0o755)

    def package_info(self):
        # Pure Python — expose the site-packages path via PYTHONPATH
        py_ver = self._py_ver()
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.env_info.PYTHONPATH.append(site)
        self.cpp_info.libs = []


# 功能实测脚本（build() 与 test_package 复用同一套断言）
_CHECKS_SRC = r'''
import struct
import sys

failures = []


def check(name, fn):
    try:
        fn()
        print("PASS:", name)
    except Exception as e:
        failures.append((name, repr(e)))
        print("FAIL:", name, "->", repr(e))


def t_import_chain():
    import keepkey_agent
    import libagent, libagent.ssh, libagent.gpg
    from libagent.device import keepkey as kdev
    from libagent.device.keepkey import KeepKey
    assert callable(keepkey_agent.ssh_agent)
    assert issubclass(KeepKey, object)
    # KeepKey 设备类支持性约束（上游 _verify_support 语义）
    assert kdev.KeepKey.required_version == ">=1.0.4"


def t_cli_entry():
    # ssh_agent 入口 argparse 全链（无参 -> usage + SystemExit 2）
    import keepkey_agent
    try:
        keepkey_agent.ssh_agent()
        raise AssertionError("expected SystemExit")
    except SystemExit as e:
        assert e.code == 2, e.code


def t_keepkeylib_protocol():
    # keepkeylib 协议层（protobuf 3.15.4 + py3 补丁后）
    import keepkeylib.client
    import keepkeylib.messages_pb2 as m
    from keepkeylib.types_pb2 import IdentityType
    from keepkeylib.transport_fake import FakeTransport
    assert callable(FakeTransport)
    assert m.Initialize is not None
    ident = IdentityType()
    ident.proto = "ssh"
    ident.user = "u"
    ident.host = "h"
    assert ident.proto == "ssh"
    # 消息序列化往返（设备协议 wire 格式）
    msg = m.Ping()
    msg.message = "hello"
    msg.button_protection = True
    raw = msg.SerializeToString()
    back = m.Ping()
    back.ParseFromString(raw)
    assert back.message == "hello" and back.button_protection


def t_nist256_sign_verify():
    # KeepKey SSH 主曲线路径：NIST256p 签名验证闭环（设备无关纯逻辑）
    from libagent import formats
    import ecdsa, ecdsa.util, hashlib

    def frame(b):
        return struct.pack(">I", len(b)) + b

    sk = ecdsa.SigningKey.generate(curve=ecdsa.NIST256p)
    vk = sk.get_verifying_key()
    blob = (frame(formats.SSH_NIST256_KEY_TYPE) +
            frame(formats.SSH_NIST256_CURVE_NAME) +
            frame(formats.SSH_NIST256_DER_OCTET + vk.to_string()))
    r = formats.parse_pubkey(blob)
    assert r["curve"] == formats.CURVE_NIST256
    msg = b"keepkey-agent-auth-test"
    sig = sk.sign(msg, sigencode=ecdsa.util.sigencode_string,
                  hashfunc=hashlib.sha256)
    ssh_sig = r["verifier"](sig, msg)
    assert len(ssh_sig) == 74  # 2 x (4B frame + 1B 0x00 + 32B)


def t_ed25519_sign_verify():
    # ED25519 曲线路径（ed25519 shim + pure25519 数学）
    from libagent import formats
    import ed25519

    def frame(b):
        return struct.pack(">I", len(b)) + b

    seed = bytes(range(32))
    sk = ed25519.SigningKey(seed)
    vk = sk.get_verifying_key()
    blob = frame(formats.SSH_ED25519_KEY_TYPE) + frame(vk.to_bytes())
    r = formats.parse_pubkey(blob)
    assert r["curve"] == formats.CURVE_ED25519
    msg = b"keepkey-agent-auth-test"
    sig = sk.sign(msg)
    r["verifier"](sig, msg)
    # 篡改签名必须被拒——"接受即失败"的判定移出 try 块
    # （raise 放 try 内会被同一个 except 吞掉，形成永真断言）
    rejected = False
    try:
        r["verifier"](b"\x00" + sig[1:], msg)
    except Exception:
        rejected = True
    assert rejected, "tampered sig accepted"


def t_ed25519_rfc8032():
    # ed25519 shim 数学正确性：RFC 8032 TEST 1 向量
    import ed25519
    seed = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc4"
        "4449c5697b326919703bac031cae7f60")
    pub = bytes.fromhex(
        "d75a980182b10ab7d54bfed3c964073a"
        "0ee172f3daa62325af021a68f707511a")
    sig = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a"
        "84877f1eb8e5d974d873e065224901555"
        "fb8821590a33bacc61e39701cf9b46bd"
        "25bf5f0595bbe24655141438e7a100b")
    sk = ed25519.SigningKey(seed)
    assert sk.get_verifying_key().to_bytes() == pub
    assert sk.sign(b"").hex() == sig.hex()
    ed25519.VerifyingKey(pub).verify(sig, b"")


def t_identity_parsing():
    # ssh:// identity 字符串解析（ssh_agent CLI 首步逻辑）
    from libagent.device import interface
    d = interface.string_to_identity("ssh://user@host:22")
    assert d == {"proto": "ssh", "user": "user",
                 "host": "host", "port": "22"}
    from libagent.device import keepkey as kdev
    ident = kdev.device_interface.Identity if hasattr(
        kdev, "device_interface") else interface.Identity
    i = interface.Identity("ssh://user@host", "curve/nist256")
    assert i.get_curve_name() == "curve/nist256"


check("import_chain (keepkey_agent->libagent->keepkeylib)", t_import_chain)
check("cli_entry (argparse usage)", t_cli_entry)
check("keepkeylib_protocol (protobuf wire round-trip)", t_keepkeylib_protocol)
check("nist256_sign_verify (SSH 主曲线闭环)", t_nist256_sign_verify)
check("ed25519_sign_verify (shim+pure25519 闭环)", t_ed25519_sign_verify)
check("ed25519_rfc8032 (数学正确性向量)", t_ed25519_rfc8032)
check("identity_parsing (ssh:// URI)", t_identity_parsing)

if failures:
    print("TOTAL: %d FAILED" % len(failures))
    sys.exit(1)
print("TOTAL: 7/7 PASSED")
'''

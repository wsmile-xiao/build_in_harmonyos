#!/usr/bin/env python3
"""kubeseal 0.35.0 消费者用例 + 交付形态自检。

用法:
    python3 consumer_check.py <package_folder> [--expect-machine aarch64]
                              [--require-signature] [--expect-version v0.35.0]

消费者用例（C1–C11）**真跑交付出来的 bin/kubeseal 与 bin/controller**，断言真实
stdout / stderr / 退出码。核心是**离线的 SealedSecret 加解密往返**（外部可核对真值）：

    Secret YAML  --(kubeseal --cert 证书)-->  SealedSecret  --(kubeseal
    --recovery-unseal --recovery-private-key 私钥)-->  原 Secret（逐字段比对）

配套的**反向证据**：拿另一对钥匙的私钥去解封同一份 SealedSecret 必须失败
（`no key could decrypt secret`）——证明密文确实绑定在封印用的那张证书的公钥上，
不是"原样搬抄"。

证书/私钥来源（两条路径都能得到真实 RSA-2048 密钥对，往返断言完全相同）：
  1. 若运行环境有 `openssl`（本机预检/多数 worker）⇒ 现场生成；
  2. 否则使用脚本内嵌的 self-signed 测试夹具（**仅供离线往返验证的公开测试数据**，
     非任何真实环境的凭据；`CN=sealed-secrets-test-1/2`，2036 年到期）。
脚本会打印实际使用的路径。

临时目录同样做可写探针（OHOS 上 `/tmp` 只读，优先落到 ext2 分区）。

交付形态自检（M1–M14）检查两个二进制的 ELF 事实与包内容纯净性。
任一 check 失败 → 退出码 1（R34 反空壳：把 bin/ 挪走后本脚本必然失败）。
"""
import os
import shutil
import subprocess
import sys
import tempfile

_MACHINE_ID = {"aarch64": 0xB7, "x86_64": 0x3E}
_CODESIGN = b".codesign"
_WORKDIR_MARKERS = (b"conan-go-build", b".go-work")

# 与软件级 commands.json 的 versions."0.35.0".commands 严格一致（交付集合）
_DECLARED_COMMANDS = ("controller", "kubeseal")

_SECRET_YAML = """apiVersion: v1
kind: Secret
metadata:
  name: mysecret
  namespace: mynamespace
data:
  foo: YmFy
  hello: d29ybGQ=
"""

# ── 内嵌离线测试夹具（openssl 不可用时的 fallback；公开测试数据，非真实凭据）──
_EMBEDDED_CERT_A = """-----BEGIN CERTIFICATE-----
MIIDaTCCAlGgAwIBAgIUdRTTjNb3Wkj08Xgm79XkdR6gbHkwDQYJKoZIhvcNAQEL
BQAwRDEeMBwGA1UEAwwVc2VhbGVkLXNlY3JldHMtdGVzdC0xMSIwIAYDVQQKDBlv
ZmZsaW5lLXJvdW5kdHJpcC1maXh0dXJlMB4XDTI2MTAwMTExNDUxOFoXDTM2MDky
ODExNDUxOFowRDEeMBwGA1UEAwwVc2VhbGVkLXNlY3JldHMtdGVzdC0xMSIwIAYD
VQQKDBlvZmZsaW5lLXJvdW5kdHJpcC1maXh0dXJlMIIBIjANBgkqhkiG9w0BAQEF
AAOCAQ8AMIIBCgKCAQEAoraxJfNHQ9FvGpWZqVZdtVPL8m4f7Y+FwS6elWslHbm6
apMc1tfB963nhZ4rAzXZGeO4qQzOm4peDTLyK43xGmgzP1wLA5s0o9D39mVzt+uN
CNsAy+gTmXRAoWUqnuJaZR/mGzPi2f4lksYXaBWy/iJ07GbemqE15Uu2UJWga2qi
uvXGc0NQaL/S55U9wQY4NT6DyKGOunOPL+tnHNIv9GV84Wta3Pxh3+FjcxvuoIAe
JSh0LLlKhVSYJ231F/pYltVB/tVFcRN+CvyvvBj+0fHNv4zwabvVEss1SdUe7Fue
Wmp0SLSFgtgDxin3BOCZ8avyt7Dx14LuDN+NFWifOwIDAQABo1MwUTAdBgNVHQ4E
FgQU6ihXL1gUFfXtaVD2Epkd+F0xv9swHwYDVR0jBBgwFoAU6ihXL1gUFfXtaVD2
Epkd+F0xv9swDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAOHce
p6rQCDb8K/Mjlj3FkVGUs1CPacM8zb6Y/noZO8dMdXHhgMJbUVCPUjBWhjxOS/Gh
1s2SlsGm/LBMUghAhFBHtfQ4FWlzxC9PRNFCqzXlxBKX6ducnC8sP8hR+lRASM1a
fm9zFHlVD86p479+RTAVFzQeaZu/hhjc8oIOn4wtZ3dBSRa4idU50TxcRJd5DzcQ
EF2Zdvos5K3zarTX/xJVrp4kOR+wwtRMK34Zm3u4F8ScFE1Dzm8Y+wOAsfrBoX7q
tnVK38PkOohnMEgGZOx4fLv0sgt6sEOhwB3mnd9hyQ/UwWY1A+p9IwqzHbiDYch4
/3dj5H0ti56L1GPDhQ==
-----END CERTIFICATE-----
"""

_EMBEDDED_KEY_A = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCitrEl80dD0W8a
lZmpVl21U8vybh/tj4XBLp6VayUdubpqkxzW18H3reeFnisDNdkZ47ipDM6bil4N
MvIrjfEaaDM/XAsDmzSj0Pf2ZXO3640I2wDL6BOZdEChZSqe4lplH+YbM+LZ/iWS
xhdoFbL+InTsZt6aoTXlS7ZQlaBraqK69cZzQ1Bov9LnlT3BBjg1PoPIoY66c48v
62cc0i/0ZXzha1rc/GHf4WNzG+6ggB4lKHQsuUqFVJgnbfUX+liW1UH+1UVxE34K
/K+8GP7R8c2/jPBpu9USyzVJ1R7sW55aanRItIWC2APGKfcE4Jnxq/K3sPHXgu4M
340VaJ87AgMBAAECggEACCvVifAwLYCIgaoZR+Q9m3wO+2iQCOg9ZtNWWm7sM78e
f034/km32h4tHiGFy8j5/e9Y2CsmUFsAAyNXqbFHS4oHvNBSAJyG5bfPpAY56/a+
eT808zMp53nA6c9V9xmrQXXQd/WV7a2c1G9HQKO0/pyGCP3XgvttOfZ15uZvYnAp
cKByd8mplC4am0VEu4TYldHx/5nkBnzvoI/iMpy8I6ECopiWYd4l6isI3f8S4c+E
BMkk7ldVrzxwJhRVKf0+j6jjpoh2GbghYGosve2xV7AXVtPuui60H+sA+sGvcIsu
FYolS6bpqfoYBrKGdaHiFaq+e3Ydj4fNeaCkj0F1aQKBgQDZ4wsbZAqdWEUkNnbd
PSJ6lgzcuPbXawUVjKziwpryQboWCQIBX2hqxXPVOQNmsT935TqORXvkJxM8rE2O
s6tIcoK1CSfoeWOuSHyTP82khAxDMpfPbznZZDxkmAuNGqRLlhTdtcZYWA+3yIII
UQHIx2Ytvga1ETifLEQuJq2kAwKBgQC/LP7Emy7/8/7/Hgajw1RMiXbDySoQgxH0
grQoc3LvAQ0akeVgtwg0Ug91zORIV5uQ884UnRqg4dSPO1utp+JhyJsmmh3kqRtk
bWaZUh1V3e6JP19xN3uYC0rTuIQN6y5ZSKCByFAYRxoFiOlFj+UCioSA6UirLXSV
UPGXv6geaQKBgGuBaumI4vPfqb3EYcGneGujvZTqbmC7nTaUwnjgLDN72qUkrKig
upRz+EMsblEtA3PU1p98CTT5UrSND3dpjwmf9n38loRN4LENcun0gTK7NJGzVNQ0
vQZWPrYjjw+AJbBlzMXX+pV8XcUAWahgz9CREglfyU9tv9JJtRpQWzyhAoGAMPCK
07fKQ1mp+JMuLfQN+33hOmOf8hQrn4VqK0TKsmZ5fUjGCIkyf3pWXNizw9UxjNzs
75f8Ph0xte0DHiRxLokVNr+TUXr8+SuMbUl5GwcyTk4715bVe+nAIQ0GOS3wcojG
FhM6dcyV277dwKIChTEClKGjqbZ8NtE+15MHrakCgYEAnaMWKrmR86Bk3fIEVl10
2mSTQhnc9+0n7RqBMiuEWNbuhJL32BEh9kIQk7yehdX+/Z7e5gB8Glpp5oR2NUrk
1kQJYNeIlG22rxx/F/7XadpzfqjOueG3yXjWm/uobq3LGqLwXOUUMWzVjX8eEhef
qMxCnaVo/WDOvtPz7FSAbzY=
-----END PRIVATE KEY-----
"""

_EMBEDDED_KEY_B = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC6bwgqf2iHlrQ7
ABgeITqs9M1EjEziNfg6O8EKHePQuMAeJx0lL2yPAMFiFOUkaMJ+sGuEDUJbvPvS
No1BKtG815NFrKYsK6PcHl61I3J1wYMA37LEK7m8XUDCMpAlYx25mBj92guwP0i7
GcbajNFNaqD5NX4kn+z8NCx2iH8DPGtN6VGnjPbQmriJvmldWHDeEiaR9Q5GT5jc
Hsce0VXPrPrK3glNt0Oz6Om3JbpPBXclxFttHO/BgeV2pNP4N8q7g18e4g+Lg1dK
NSZNIm7s8Np6ahJcRzPBLhWMTSrOemoiGBZS4dGyM+ZCWs4vmmEvcwojKFM1l4ju
K5hmsW0/AgMBAAECggEAEVMEBT71rbPZZ6ook5Qu6aeN85K+Cj9No8utsoz4gIrK
f4LO+IehpOBDGCQs7uc1O6SVOR4qTnAPTod3NNkPyGaX7t+OSYh8n5XK4zY6CqtC
yy/+YrBVgCWCQQmFz5OYTYjOubgrYeNflNNeYSy4vmLsNnw8Dpc15HHMt+8TLm+k
IsyPKH5BM8dBL3+WmmU5Gv23oUyVNUbh9fkxZ+byOfdgd7bcLk77w2OwQVY3N/Wb
c3V1NA+rwP5ReuOj1M2Ti4ARXMv4v+M9F9i+nGS1H1tcOSwMWZaAAG8zFfTFg5Q6
K5Kus/o1Xt8KhnLX5wMmTYMltjIdhWxYANYKOz6UMQKBgQDtcC2Z2RAs5ijtzAx+
YHYR9A2s5QFSU2iv58Xf6SKpHOVBYsmphz8cKZ/eS0FV55VGgfWuCmfjhfCGzdka
/TxVhUf4DWbvQz8xcXOyIiV4rQEE0+8zj9mEeVJqgvgNcj39yX02obWFbipSIKyE
iJ2w3yt7AZNIGu1fi4+pbeUPzQKBgQDJAht6Y72Jg9tuJVLT8+VVkrdFVwVzvJZm
m0Qp1TyVSbTfspiKREbNEBE8TvOV/9OWkx9xYNIlAY4SL9pSJDPbD+lP0/fTBps0
mQkl7tIwglVpV8bkR05tVCqMTS9N8HdeUH+J6SB4nEvE1LJ5//mw39BglTBWMzgv
DXEuDl7tOwKBgFLwxa0hSuo0OAXhKlgXAAeDdid4E38bjc0srE1sFeR3KIovpPwo
N15yF9tB9H+6lsV7bkOudN3gksW0MGuiHCpPlXVL0TIxDmkKFX0bOnWuEVYLZlpf
nH8PFkAIofeoeYkmkiu8Tzld40CvEzR0uIjpXDnqsfUVGuguSy/HKKXdAoGBAKkA
ypWm0q+SW6ZKX0+x2vqN9uWn+v+KanIuzarWjK+AX0FN6g8mxNiZT8SDJS7S/9W0
MVWkcEuI+Si1bzxtD+R5hlMGB3I4NbqNiTGJkNQUYTfHA4Tfp0Mo5vU72DARpGt6
ByGvDwwZbWM66izFWeyq4YqzJQb03aJCDQ0KLCoNAoGBAJk1u1h6uk50EvuweYc5
2MN5Uhn6dgY9iHeWYbw/UC6ivBi6I3kvg3hB1LTuF+xe7Vgz8AIVwj5bAq597h8j
OXnCoQwqmkcuNxLJ8pRFPucNceSutxBT6p4if2bFTeIEbvvki0ZRrx4on2MyslQ7
PGWVUJDSlgcYy/ybSC8LnASK
-----END PRIVATE KEY-----
"""


class Report(object):
    def __init__(self):
        self.ok = 0
        self.fail = 0
        self.note = 0

    def check(self, condition, label):
        if condition:
            self.ok += 1
            print("        [ok] %s" % label)
        else:
            self.fail += 1
            print("        [FAIL] %s" % label)
        return bool(condition)

    def skip(self, label):
        self.note += 1
        print("        [skip] %s" % label)


def _run(binary, args, stdin_text=None, timeout=120):
    proc = subprocess.Popen([binary] + args, cwd="/",
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    payload = stdin_text.encode() if stdin_text is not None else b""
    try:
        out, err = proc.communicate(input=payload, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return None, "", "timeout after %ss" % timeout
    return (proc.returncode, out.decode("utf-8", "replace"),
            err.decode("utf-8", "replace"))


def _tmp_root():
    """挑一个可写的临时根（OHOS 上 /tmp 只读，优先 ext2 分区）。"""
    candidates = [
        os.environ.get("OHOS_GO_WORKROOT"),
        "/data/storage/el2/base/cache",
        "/data/storage/el2/base/haps/entry/files",
        os.environ.get("TMPDIR"),
        tempfile.gettempdir(),
        os.getcwd(),
    ]
    for cand in candidates:
        if not cand or not os.path.isdir(cand):
            continue
        probe_dir = os.path.join(cand, "kubeseal-consumer-check-%d" % os.getpid())
        try:
            os.makedirs(probe_dir, exist_ok=True)
            probe = os.path.join(probe_dir, ".wprobe")
            with open(probe, "wb") as handle:
                handle.write(b"0")
            os.remove(probe)
            return probe_dir
        except OSError:
            continue
    raise SystemExit("[FAIL] no writable temp directory found")


def _make_key_material(work):
    """返回 (cert_a, key_a, key_b, source_note)。"""
    cert_a = os.path.join(work, "test-cert-a.pem")
    key_a = os.path.join(work, "test-key-a.pem")
    key_b = os.path.join(work, "test-key-b.pem")
    openssl = shutil.which("openssl")
    if openssl:
        rc = subprocess.call(
            [openssl, "req", "-x509", "-nodes", "-newkey", "rsa:2048",
             "-keyout", key_a, "-out", cert_a, "-days", "3650",
             "-subj", "/CN=sealed-secrets-consumer-check/O=offline-roundtrip"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if rc == 0 and os.path.isfile(cert_a) and os.path.isfile(key_a):
            with open(key_b, "w", encoding="utf-8") as handle:
                handle.write(_EMBEDDED_KEY_B)
            return cert_a, key_a, key_b, "openssl(现场生成 cert/key A) + 内嵌 key B"
    with open(cert_a, "w", encoding="utf-8") as handle:
        handle.write(_EMBEDDED_CERT_A)
    with open(key_a, "w", encoding="utf-8") as handle:
        handle.write(_EMBEDDED_KEY_A)
    with open(key_b, "w", encoding="utf-8") as handle:
        handle.write(_EMBEDDED_KEY_B)
    return cert_a, key_a, key_b, "内嵌离线测试夹具（openssl 不可用）"


def _elf(data):
    ei_class, ei_data = data[4], data[5]
    e_machine = int.from_bytes(data[18:20], "little")
    e_phoff = int.from_bytes(data[32:40], "little")
    e_phentsize = int.from_bytes(data[54:56], "little")
    e_phnum = int.from_bytes(data[56:58], "little")
    ptypes = []
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        if off + 4 > len(data):
            break
        ptypes.append(int.from_bytes(data[off:off + 4], "little"))
    return ei_class, ei_data, e_machine, ptypes


def _iter_entries(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            yield dirpath, name
        for name in dirnames:
            yield dirpath, name


def main(argv):
    if len(argv) < 2:
        print("usage: consumer_check.py <package_folder> [options]")
        return 2
    package_folder = os.path.abspath(argv[1])
    expect_machine = "aarch64"
    require_signature = False
    expect_version = "v0.35.0"
    rest = argv[2:]
    while rest:
        opt = rest.pop(0)
        if opt == "--expect-machine":
            expect_machine = rest.pop(0)
        elif opt == "--require-signature":
            require_signature = True
        elif opt == "--expect-version":
            expect_version = rest.pop(0)
        else:
            print("unknown option: %s" % opt)
            return 2

    report = Report()
    bin_dir = os.path.join(package_folder, "bin")
    kubeseal = os.path.join(bin_dir, "kubeseal")
    controller = os.path.join(bin_dir, "controller")
    print("[step] package folder: %s" % package_folder)
    print("[step] expect machine=%s version=%s require_signature=%s"
          % (expect_machine, expect_version, require_signature))

    if not (os.path.isfile(kubeseal) and os.path.isfile(controller)):
        print("[FAIL] bin/{kubeseal,controller} missing — nothing to test")
        return 1

    work = _tmp_root()
    print("[step] temp dir: %s" % work)
    cert_a, key_a, key_b, source = _make_key_material(work)
    print("[step] key material: %s" % source)

    # ── C: 消费者用例（真跑交付出来的二进制）──────────────────────
    print("[step] C1: kubeseal --version")
    code, out, err = _run(kubeseal, ["--version"])
    report.check(code == 0, "C1 exit code 0 (got %s)" % code)
    report.check(out == "kubeseal version: %s\n" % expect_version,
                 "C1 stdout == 'kubeseal version: %s' (got %r)"
                 % (expect_version, out))

    print("[step] C2: kubeseal --help")
    code, out, err = _run(kubeseal, ["--help"])
    report.check(code == 0, "C2 exit code 0 (got %s)" % code)
    report.check(all(flag in out for flag in (
        "--cert", "--recovery-unseal", "--recovery-private-key",
        "--fetch-cert", "--scope", "--format")),
        "C2 stdout documents --cert/--recovery-unseal/"
        "--recovery-private-key/--fetch-cert/--scope/--format")

    print("[step] C3: seal Secret -> SealedSecret (json)")
    code, sealed_json, err = _run(
        kubeseal, ["--cert", cert_a, "--format", "json"], stdin_text=_SECRET_YAML)
    report.check(code == 0, "C3 exit code 0 (got %s)" % code)
    sealed = None
    try:
        import json as _json
        sealed = _json.loads(sealed_json)
    except ValueError as exc:
        print("        [info] sealed output not JSON: %s" % exc)
    if sealed:
        report.check(sealed.get("kind") == "SealedSecret",
                     "C3 kind == SealedSecret (got %r)" % sealed.get("kind"))
        report.check(sealed.get("apiVersion") == "bitnami.com/v1alpha1",
                     "C3 apiVersion == bitnami.com/v1alpha1")
        meta = sealed.get("metadata") or {}
        report.check(meta.get("name") == "mysecret"
                     and meta.get("namespace") == "mynamespace",
                     "C3 metadata name/namespace preserved (%r/%r)"
                     % (meta.get("name"), meta.get("namespace")))
        enc = (sealed.get("spec") or {}).get("encryptedData") or {}
        report.check(sorted(enc) == ["foo", "hello"],
                     "C3 spec.encryptedData keys == [foo, hello] (got %r)"
                     % sorted(enc))
        report.check(all(isinstance(v, str) and len(v) > 64
                         for v in enc.values()),
                     "C3 every encryptedData value is non-trivial ciphertext")
    else:
        report.check(False, "C3 sealed output must be parseable JSON")

    print("[step] C4: recovery-unseal -> original Secret (json, field by field)")
    code, unsealed_json, err = _run(
        kubeseal, ["--recovery-unseal", "--recovery-private-key", key_a,
                   "-o", "json"], stdin_text=sealed_json)
    report.check(code == 0, "C4 exit code 0 (got %s)" % code)
    unsealed = None
    try:
        import json as _json
        unsealed = _json.loads(unsealed_json)
    except ValueError as exc:
        print("        [info] unsealed output not JSON: %s" % exc)
    if unsealed:
        report.check(unsealed.get("kind") == "Secret",
                     "C4 kind == Secret (got %r)" % unsealed.get("kind"))
        meta = unsealed.get("metadata") or {}
        report.check(meta.get("name") == "mysecret"
                     and meta.get("namespace") == "mynamespace",
                     "C4 round-trip metadata name/namespace match the input")
        data = unsealed.get("data") or {}
        report.check(data.get("foo") == "YmFy",
                     "C4 data.foo round-tripped to 'YmFy' (got %r)"
                     % data.get("foo"))
        report.check(data.get("hello") == "d29ybGQ=",
                     "C4 data.hello round-tripped to 'd29ybGQ=' (got %r)"
                     % data.get("hello"))
        import base64 as _b64
        report.check(_b64.b64decode(data.get("foo", "")) == b"bar",
                     "C4 base64-decoded data.foo == b'bar'")
    else:
        report.check(False, "C4 unsealed output must be parseable JSON")

    print("[step] C5: seal -> SealedSecret (yaml path)")
    code, sealed_yaml, err = _run(
        kubeseal, ["--cert", cert_a, "--format", "yaml"], stdin_text=_SECRET_YAML)
    report.check(code == 0, "C5 exit code 0 (got %s)" % code)
    report.check("kind: SealedSecret" in sealed_yaml
                 and "apiVersion: bitnami.com/v1alpha1" in sealed_yaml,
                 "C5 yaml carries kind/apiVersion")
    report.check("name: mysecret" in sealed_yaml
                 and "namespace: mynamespace" in sealed_yaml,
                 "C5 yaml carries the Secret name/namespace")
    report.check("foo:" in sealed_yaml and "hello:" in sealed_yaml
                 and "encryptedData:" in sealed_yaml,
                 "C5 yaml carries spec.encryptedData for foo and hello")

    print("[step] C6: recovery-unseal of the yaml SealedSecret")
    code, unsealed_yaml, err = _run(
        kubeseal, ["--recovery-unseal", "--recovery-private-key", key_a,
                   "-o", "yaml"], stdin_text=sealed_yaml)
    report.check(code == 0, "C6 exit code 0 (got %s)" % code)
    report.check("kind: Secret" in unsealed_yaml,
                 "C6 yaml kind == Secret")
    report.check("foo: YmFy" in unsealed_yaml and "hello: d29ybGQ=" in unsealed_yaml,
                 "C6 yaml data matches the original Secret byte for byte")

    print("[step] C7: wrong private key must NOT decrypt")
    code, out, err = _run(
        kubeseal, ["--recovery-unseal", "--recovery-private-key", key_b,
                   "-o", "json"], stdin_text=sealed_json)
    report.check(code == 1, "C7 exit code 1 with a foreign key (got %s)" % code)
    report.check("no key could decrypt secret" in err,
                 "C7 stderr says 'no key could decrypt secret'")
    report.check(out == "", "C7 stdout empty on failure")

    print("[step] C8: missing --cert file")
    code, out, err = _run(
        kubeseal, ["--cert", os.path.join(work, "nope.pem"), "--format",
                   "json"], stdin_text=_SECRET_YAML)
    report.check(code == 1, "C8 exit code 1 (got %s)" % code)
    report.check("no such file or directory" in err,
                 "C8 stderr reports the missing certificate file")

    print("[step] C9: invalid input with a valid --cert")
    code, out, err = _run(
        kubeseal, ["--cert", cert_a, "--format", "json"],
        stdin_text="not: a secret\n")
    report.check(code == 1, "C9 exit code 1 (got %s)" % code)
    report.check("no secrets found" in err,
                 "C9 stderr says 'no secrets found'")

    print("[step] C10: controller --version")
    code, out, err = _run(controller, ["--version"])
    report.check(code == 0, "C10 exit code 0 (got %s)" % code)
    report.check(out == "controller version: %s\n" % expect_version,
                 "C10 stdout == 'controller version: %s' (got %r)"
                 % (expect_version, out))

    print("[step] C11: controller --help")
    code, out, err = _run(controller, ["--help"])
    report.check(code == 0, "C11 exit code 0 (got %s)" % code)
    # 控制器用的是 k8s 的 flag 包，--help 走 stderr（kubeseal 走 stdout）
    help_text = out + err
    report.check("--key-prefix" in help_text and "--key-renew-period" in help_text
                 and "--key-size" in help_text,
                 "C11 combined output documents "
                 "--key-prefix/--key-renew-period/--key-size")

    # ── M: 交付形态自检 ───────────────────────────────────────────
    blobs = {}
    for name, path in (("kubeseal", kubeseal), ("controller", controller)):
        with open(path, "rb") as handle:
            blobs[name] = handle.read()
    sizes = dict((name, os.path.getsize(os.path.join(bin_dir, name)))
                 for name in _DECLARED_COMMANDS)

    print("[step] M1: both declared binaries exist")
    report.check(all(os.path.isfile(os.path.join(bin_dir, name))
                     for name in _DECLARED_COMMANDS),
                 "M1 bin/ has %s" % (list(_DECLARED_COMMANDS),))

    print("[step] M2: plausible binary sizes")
    report.check(all(5 * 1024 * 1024 <= size <= 300 * 1024 * 1024
                     for size in sizes.values()),
                 "M2 sizes within 5MiB..300MiB (%r)" % sizes)

    print("[step] M3: owner execute bit")
    report.check(all(os.access(os.path.join(bin_dir, name), os.X_OK)
                     for name in _DECLARED_COMMANDS),
                 "M3 both binaries are executable by the current user")

    print("[step] M4: ELF magic")
    report.check(all(blob[:4] == b"\x7fELF" for blob in blobs.values()),
                 "M4 both start with the ELF magic")

    print("[step] M5: ELF machine is %s" % expect_machine)
    machines = {}
    perms = {}
    for name, blob in blobs.items():
        ei_class, ei_data, e_machine, ptypes = _elf(blob)
        machines[name] = (ei_class, ei_data, e_machine)
        perms[name] = ptypes
    report.check(all(cls == 2 and dat == 1 for cls, dat, _ in machines.values()),
                 "M5 both are ELF64 little-endian (%r)" % (machines,))
    report.check(all(mach == _MACHINE_ID[expect_machine]
                     for _, _, mach in machines.values()),
                 "M5 both e_machine == 0x%X (%s)"
                 % (_MACHINE_ID[expect_machine], expect_machine))

    print("[step] M6: statically linked (no PT_INTERP)")
    report.check(all(3 not in ptypes for ptypes in perms.values()),
                 "M6 neither binary has PT_INTERP (%r)"
                 % dict((n, len(p)) for n, p in perms.items()))

    print("[step] M7: HongMeng ELF signature")
    if require_signature:
        report.check(all(_CODESIGN in blob for blob in blobs.values()),
                     "M7 both binaries carry a .codesign section (E128)")
    else:
        report.skip("M7 signature not required for %s" % expect_machine)

    print("[step] M8: bin/ matches the commands.json declaration")
    entries = sorted(os.listdir(bin_dir))
    report.check(entries == sorted(_DECLARED_COMMANDS),
                 "M8 bin/ listing %r == commands.json commands %r"
                 % (entries, sorted(_DECLARED_COMMANDS)))

    print("[step] M9: license shipped")
    license_path = os.path.join(package_folder, "licenses", "LICENSE")
    license_text = ""
    if os.path.isfile(license_path):
        with open(license_path, "r", encoding="utf-8", errors="replace") as handle:
            license_text = handle.read()
    report.check("Apache License" in license_text
                 and "Version 2.0" in license_text,
                 "M9 licenses/LICENSE is the Apache-2.0 text (%d bytes)"
                 % len(license_text))

    print("[step] M10-M12: package content hygiene")
    go_sources, hidden, objects = [], [], []
    for dirpath, name in _iter_entries(package_folder):
        rel = os.path.relpath(os.path.join(dirpath, name), package_folder)
        if name.endswith(".go") or name in ("go.mod", "go.sum") \
                or name.endswith(".test"):
            go_sources.append(rel)
        if name.startswith(".") or name in ("__pycache__", "go-build"):
            hidden.append(rel)
        if name.endswith((".o", ".a", ".c", ".s", ".h")):
            objects.append(rel)
    report.check(not go_sources,
                 "M10 no Go sources/module files in the package (got %r)"
                 % go_sources[:5])
    report.check(not hidden,
                 "M11 no hidden files or build caches in the package (got %r)"
                 % hidden[:5])
    report.check(not objects,
                 "M12 no intermediate object/source files in the package (got %r)"
                 % objects[:5])

    print("[step] M13: build work directory path not embedded (-trimpath)")
    embedded = sorted(marker.decode() for blob in blobs.values()
                      for marker in _WORKDIR_MARKERS if marker in blob)
    report.check(not embedded,
                 "M13 no build work-dir marker in either binary (got %r)"
                 % embedded)

    print("[step] M14: both binaries report the pinned version")
    report.check(out_version_ok(kubeseal, expect_version)
                 and out_version_ok(controller, expect_version),
                 "M14 --version of both binaries embeds %s" % expect_version)

    print("[summary] consumer checks: %d passed, %d failed, %d skipped"
          % (report.ok, report.fail, report.note))
    try:
        shutil.rmtree(work, ignore_errors=True)
    except OSError:
        pass
    if report.fail:
        print("[summary] kubeseal consumer check FAILED")
        return 1
    print("[summary] kubeseal consumer check PASSED")
    return 0


def out_version_ok(binary, expect_version):
    code, out, err = _run(binary, ["--version"])
    return code == 0 and out.rstrip().endswith(expect_version)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

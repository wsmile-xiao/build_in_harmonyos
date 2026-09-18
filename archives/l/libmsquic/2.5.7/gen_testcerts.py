#!/usr/bin/env python3
"""Generate static localhost test PFX for libmsquic TlsTest.HandshakeCertFromFile.

Route differs from prior dynamic `openssl req -x509` rounds: no openssl CLI
is invoked on the HarmonyOS preflight client at all for the primary path.
A long-lived (10y) self-signed localhost cert is generated once with the
`cryptography` library (SAN + EKU present so handshake validation can pass),
exported as PKCS#12 (password PLACEHOLDER == upstream PfxPass), and committed
under testcerts/. Because GitCode PR diffs (/pull/N.diff applied by CI
checkout-pr via `git apply`) cannot carry binary content, the PFX ships as
base64 TEXT in selfsignedservercert.pfx.b64 (byte-identical after decode);
the recipe decodes it with the Python stdlib at test time. The recipe copies
the materialized PFX to the writable TMPDIR at build time;
`openssl pkcs12 -export` from committed PEMs is a fallback,
dynamic `req` generation is the last resort.
"""
import base64
import datetime
import ipaddress
import os

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    serialize_key_and_certificates,
)
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testcerts")
os.makedirs(OUT, exist_ok=True)

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
now = datetime.datetime.now(datetime.timezone.utc)
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now - datetime.timedelta(days=1))
    .not_valid_after(now + datetime.timedelta(days=3650))
    .add_extension(
        x509.SubjectAlternativeName(
            [
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                x509.IPAddress(ipaddress.ip_address("::1")),
            ]
        ),
        critical=False,
    )
    .add_extension(
        x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
        critical=False,
    )
    .add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    )
    .add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )
    .sign(private_key=key, algorithm=hashes.SHA256())
)

key_pem = key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
)
cert_pem = cert.public_bytes(serialization.Encoding.PEM)
pfx = serialize_key_and_certificates(
    b"localhost", key, cert, None, serialization.BestAvailableEncryption(b"PLACEHOLDER")
)

with open(os.path.join(OUT, "localhost_key.pem"), "wb") as f:
    f.write(key_pem)
with open(os.path.join(OUT, "localhost_cert.pem"), "wb") as f:
    f.write(cert_pem)
with open(os.path.join(OUT, "selfsignedservercert.pfx"), "wb") as f:
    f.write(pfx)
with open(os.path.join(OUT, "selfsignedservercert.pfx.b64"), "w") as f:
    f.write(base64.b64encode(pfx).decode("ascii") + "\n")
print("wrote %d key / %d cert / %d pfx bytes (+b64 text) to %s" % (len(key_pem), len(cert_pem), len(pfx), OUT))

"""Exercise packaged socksio without a live proxy or network access."""

import json
import os
import sys
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    import socksio
    from socksio import ProtocolError, socks4, socks5

    results = []

    def check(name, action):
        try:
            action()
            results.append({"name": name, "passed": True})
            print("PASS", name, flush=True)
        except Exception as exc:
            results.append({"name": name, "passed": False,
                            "error": f"{type(exc).__name__}: {exc}"})
            print("FAIL", name, flush=True)

    def packaged_import():
        imported = Path(socksio.__file__).resolve()
        assert os.path.commonpath([str(imported), str(package)]) == str(package), imported
        assert socksio.__version__ == "1.0.0"

    def socks4_ipv4():
        conn = socks4.SOCKS4Connection(user_id=b"u")
        conn.send(socks4.SOCKS4Request.from_address(
            socks4.SOCKS4Command.CONNECT, ("127.0.0.1", 1080)))
        assert conn.data_to_send() == bytes.fromhex("040104387f0000017500")
        assert conn.data_to_send() == b""
        reply = conn.receive_data(bytes.fromhex("005a04387f000001"))
        assert reply.reply_code == socks4.SOCKS4ReplyCode.REQUEST_GRANTED

    def socks4a_domain():
        conn = socks4.SOCKS4Connection(user_id=b"u")
        conn.send(socks4.SOCKS4ARequest.from_address(
            socks4.SOCKS4Command.CONNECT, ("example.com", 80)))
        assert conn.data_to_send() == bytes.fromhex(
            "04010050000000ff75006578616d706c652e636f6d00")

    def socks5_no_auth():
        conn = socks5.SOCKS5Connection()
        conn.send(socks5.SOCKS5AuthMethodsRequest(
            [socks5.SOCKS5AuthMethod.NO_AUTH_REQUIRED]))
        assert conn.data_to_send() == bytes.fromhex("050100")
        reply = conn.receive_data(bytes.fromhex("0500"))
        assert reply.method == socks5.SOCKS5AuthMethod.NO_AUTH_REQUIRED
        conn.send(socks5.SOCKS5CommandRequest.from_address(
            socks5.SOCKS5Command.CONNECT, ("example.com", 80)))
        assert conn.data_to_send() == bytes.fromhex(
            "050100030b6578616d706c652e636f6d0050")
        reply = conn.receive_data(bytes.fromhex("050000017f0000011f90"))
        assert reply.reply_code == socks5.SOCKS5ReplyCode.SUCCEEDED
        assert reply.addr == "127.0.0.1" and reply.port == 8080
        assert conn.state == socks5.SOCKS5State.TUNNEL_READY

    def malformed_reply():
        conn = socks5.SOCKS5Connection()
        conn.send(socks5.SOCKS5AuthMethodsRequest(
            [socks5.SOCKS5AuthMethod.NO_AUTH_REQUIRED]))
        conn.data_to_send()
        try:
            conn.receive_data(b"\x05")
        except ProtocolError:
            return
        raise AssertionError("truncated authentication reply was accepted")

    for name, action in (("packaged_import", packaged_import),
                         ("socks4_ipv4", socks4_ipv4),
                         ("socks4a_domain", socks4a_domain),
                         ("socks5_no_auth", socks5_no_auth),
                         ("malformed_reply", malformed_reply)):
        check(name, action)

    summary = {"package_folder": str(package), "total": len(results),
               "passed": sum(item["passed"] for item in results),
               "cases": results}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} passed", flush=True)
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())

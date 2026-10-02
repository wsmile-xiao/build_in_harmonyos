// libsignal-core 0.103.1 消费者探针（HarmonyOS PC aarch64 实测）
//
// 编译：rustc --edition 2024 probe.rs \
//        --extern libsignal_core=<pkg>/lib/liblibsignal_core.rlib \
//        --extern rand=<pkg>/lib/librand-<hash>.rlib \
//        -L dependency=<pkg>/lib
//
// 覆盖 crate 公开导出面（rust/core/src/lib.rs pub use）：
// VERSION / try_scoped / derive_arrays / E164 / DeviceId / ProtocolAddress /
// ServiceId（Aci/Pni 下转 + 字符串解析）/ curve 密钥对生成 + X25519。
// 断言只使用上游 0.103.1 公开 API，不依赖任何外部 crate 类型命名。
use libsignal_core::curve::{KeyPair, PrivateKey, PublicKey};
use libsignal_core::{
    derive_arrays, try_scoped, Aci, DeviceId, E164, Pni, ProtocolAddress, ServiceId,
    ServiceIdKind, VERSION,
};

fn main() {
    let mut asserts: u32 = 0;
    let mut fails: u32 = 0;
    macro_rules! check {
        ($cond:expr, $name:expr) => {{
            asserts += 1;
            if $cond {
                println!("[OK]   {}", $name);
            } else {
                fails += 1;
                println!("[FAIL] {}", $name);
            }
        }};
    }

    // --- crate 根导出 ---
    check!(VERSION == "0.103.1", "VERSION == 0.103.1");
    check!(try_scoped(|| Ok::<_, &str>(42)) == Ok(42), "try_scoped Ok");
    check!(try_scoped(|| Err::<(), _>("boom")) == Err("boom"), "try_scoped Err");

    // --- derive_arrays 切片派生 ---
    let (a2, a4, a6) = derive_arrays::<2, 4, 6>(|buf| buf.fill(7));
    check!(a2 == [7u8; 2] && a4 == [7u8; 4] && a6 == [7u8; 6], "derive_arrays lengths");

    // --- E164 ---
    let e: E164 = "+14155550123".parse().expect("parse e164");
    check!(e.to_string() == "+14155550123", "E164 Display");
    check!(E164::from_be_bytes(e.to_be_bytes()) == Some(e), "E164 bytes round-trip");
    check!("+0".parse::<E164>().is_err(), "E164 rejects zero");
    check!("-123".parse::<E164>().is_err(), "E164 rejects negative");

    // --- DeviceId / ProtocolAddress ---
    let dev = DeviceId::try_from(2u32).expect("device id 2");
    check!(DeviceId::try_from(0u8).is_err(), "DeviceId rejects 0");
    let pa = ProtocolAddress::new("alice.example".to_string(), dev);
    check!(pa.name() == "alice.example" && pa.device_id() == dev, "ProtocolAddress fields");
    check!(pa.to_string() == "alice.example.2", "ProtocolAddress Display");

    // --- ServiceId / Aci / Pni ---
    let sid = ServiceId::parse_from_service_id_string("8c78cd2a-16ff-427d-83dc-1a5e36ce713d")
        .expect("parse aci service id");
    check!(sid.kind() == ServiceIdKind::Aci, "ServiceId Aci kind");
    check!(
        sid.service_id_string() == "8c78cd2a-16ff-427d-83dc-1a5e36ce713d",
        "ServiceId string round-trip"
    );
    let aci = Aci::try_from(sid).expect("downcast to Aci");
    check!(ServiceId::from(aci) == sid, "Aci -> ServiceId round-trip");
    let pni_sid =
        ServiceId::parse_from_service_id_string("PNI:8c78cd2a-16ff-427d-83dc-1a5e36ce713d")
            .expect("parse pni service id");
    check!(pni_sid.kind() == ServiceIdKind::Pni, "ServiceId Pni kind");
    check!(Aci::try_from(pni_sid).is_err(), "Aci rejects Pni kind");
    let pni = Pni::try_from(pni_sid).expect("downcast to Pni");
    check!(ServiceId::from(pni) == pni_sid, "Pni -> ServiceId round-trip");
    check!(
        ServiceId::parse_from_service_id_string("8c78cd2a16ff427d83dc1a5e36ce713d").is_none(),
        "reject unhyphenated uuid"
    );
    check!(
        ServiceId::parse_from_service_id_string("BAD:{uuid}").is_none(),
        "reject bad prefix"
    );

    // --- curve：密钥对生成 + X25519 ---
    let mut rng = rand::rng();
    let kp_a = KeyPair::generate(&mut rng);
    let kp_b = KeyPair::generate(&mut rng);
    check!(
        kp_a.public_key.is_canonical() && kp_b.public_key.is_canonical(),
        "generated public keys canonical"
    );
    let pk_bytes = kp_a.public_key.serialize();
    check!(
        PublicKey::deserialize(&pk_bytes).ok().map(|p| p == kp_a.public_key) == Some(true),
        "PublicKey serialize round-trip"
    );
    let sk_bytes = kp_a.private_key.serialize();
    check!(
        PrivateKey::deserialize(&sk_bytes)
            .ok()
            .and_then(|k| k.public_key().ok())
            == Some(kp_a.public_key),
        "PrivateKey serialize round-trip"
    );
    let shared_ab = kp_a
        .private_key
        .calculate_agreement(&kp_b.public_key)
        .expect("agreement ab");
    let shared_ba = kp_b
        .private_key
        .calculate_agreement(&kp_a.public_key)
        .expect("agreement ba");
    check!(shared_ab == shared_ba, "X25519 agreement symmetric");
    let kp_rt =
        KeyPair::from_public_and_private(&pk_bytes, &sk_bytes).expect("KeyPair from bytes");
    check!(kp_rt.public_key == kp_a.public_key, "KeyPair from_public_and_private");

    // --- ServiceId -> ProtocolAddress ---
    let sid_pa = sid.to_protocol_address(dev);
    check!(
        sid_pa.device_id() == dev && sid_pa.name() == sid.service_id_string(),
        "ServiceId to_protocol_address"
    );

    println!("PROBE_ASSERTS={} FAILS={}", asserts, fails);
    if fails != 0 {
        std::process::exit(1);
    }
}

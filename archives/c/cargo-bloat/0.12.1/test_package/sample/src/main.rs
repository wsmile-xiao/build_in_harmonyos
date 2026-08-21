fn main() {
    let values: Vec<u64> = (0..128).map(|value| value * value).collect();
    println!("cargo-bloat fixture: {}", values.iter().sum::<u64>());
}

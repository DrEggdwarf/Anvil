// bof_rust.rs — Unsafe buffer overflow in Rust
use std::io::{self, Read};

fn vuln() {
    let mut buf = [0u8; 64];
    let mut input = Vec::new();
    io::stdin().read_to_end(&mut input).unwrap();

    // Intentionally unsafe: copy without bounds check
    unsafe {
        std::ptr::copy_nonoverlapping(
            input.as_ptr(),
            buf.as_mut_ptr(),
            input.len(),  // no size limit → overflow
        );
    }
    println!("Echo: {}", String::from_utf8_lossy(&buf));
}

fn win() {
    println!("[*] Flag: ANVIL{{rust_uns4fe_bof}}");
    std::process::exit(0);
}

fn main() {
    println!("Input:");
    vuln();
    // win() never called normally
    let _ = win;
}

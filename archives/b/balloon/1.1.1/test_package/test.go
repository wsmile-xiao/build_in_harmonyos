package main

import (
    "crypto/sha256"
    "crypto/sha512"
    "encoding/hex"
    "fmt"
    "os"

    "go.cypherpunks.ru/balloon"
)

func main() {
    passed := 0
    total := 3

    h1 := balloon.B(sha256.New(), []byte("password"), []byte("salt"), 4, 2)
    if len(h1) != sha256.Size {
        fmt.Printf("FAIL B length %d != %d\n", len(h1), sha256.Size)
        os.Exit(1)
    }
    fmt.Printf("PASS B sha256 len %d hex %s\n", len(h1), hex.EncodeToString(h1[:4]))
    passed++

    h2 := balloon.B(sha512.New(), []byte("hello"), []byte("world"), 2, 1)
    if len(h2) != sha512.Size {
        fmt.Printf("FAIL B sha512 length\n")
        os.Exit(1)
    }
    fmt.Printf("PASS B sha512 hex %s\n", hex.EncodeToString(h2[:4]))
    passed++

    h3 := balloon.H(sha512.New, []byte("passwd"), []byte("salty"), 4, 2, 2)
    if len(h3) != sha512.Size {
        fmt.Printf("FAIL H length\n")
        os.Exit(1)
    }
    fmt.Printf("PASS H sha512 hex %s\n", hex.EncodeToString(h3[:4]))
    passed++

    fmt.Printf("TEST_SUMMARY discovered=%d passed=%d\n", total, passed)
    if passed != total {
        os.Exit(1)
    }
}

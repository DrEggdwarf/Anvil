/* 06_rop_chain.c — ROP gadget practice binary
 * Tests: Pwn ROP tool, gadget search, symbols, GOT/PLT analysis
 * Compile: gcc -fno-stack-protector -no-pie -o 06_rop_chain 06_rop_chain.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void gadget_pop_rdi(void) {
    __asm__("pop %rdi; ret;");
}

void gadget_pop_rsi(void) {
    __asm__("pop %rsi; ret;");
}

void setup(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
}

void vuln(void) {
    char buf[64];
    printf("Overflow me: ");
    read(0, buf, 512);
}

int main(void) {
    setup();
    puts("=== ROP Challenge ===");
    puts("Hint: call system(\"/bin/sh\")");
    vuln();
    return 0;
}

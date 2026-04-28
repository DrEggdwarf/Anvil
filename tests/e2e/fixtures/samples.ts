// Sprint 18: deterministic source samples used by ASM and Pwn e2e specs.
// Inlined as TS strings (instead of separate .asm/.c files) so the entire
// fixture lives in one place and renames don't break tests silently.

/** NASM x86-64 syscall write+exit — minimal happy path. */
export const ASM_NASM_HELLO = `section .data
    msg db "Hello, e2e!", 10
    len equ $ - msg

section .text
    global _start

_start:
    mov rax, 1
    mov rdi, 1
    mov rsi, msg
    mov rdx, len
    syscall

    mov rax, 60
    xor rdi, rdi
    syscall
`

/** Same program in GAS (AT&T) syntax. */
export const ASM_GAS_HELLO = `.section .data
msg: .ascii "Hello, GAS!\\n"
len = . - msg

.section .text
.globl _start

_start:
    movq $1, %rax
    movq $1, %rdi
    leaq msg(%rip), %rsi
    movq $len, %rdx
    syscall

    movq $60, %rax
    xorq %rdi, %rdi
    syscall
`

/** NASM source with a deliberate typo on line 5 — used to assert error reporting. */
export const ASM_BROKEN = `section .text
    global _start

_start:
    movzz rax, 1     ; bogus mnemonic on line 5
    syscall
`

/** Trivial NASM where each step changes a different register — used by reverse-step tests. */
export const ASM_STEP_DIVERGE = `section .text
    global _start

_start:
    mov rax, 0x11
    mov rbx, 0x22
    mov rcx, 0x33
    mov rdi, 60
    xor rax, rax
    syscall
`

/** Minimal C source with a buffer-overflow primitive — exercises the Pwn pipeline. */
export const C_BOF_BASIC = `#include <stdio.h>
#include <string.h>

void vuln(char *input) {
    char buf[16];
    strcpy(buf, input);
    printf("Got: %s\\n", buf);
}

int main(int argc, char **argv) {
    if (argc > 1) vuln(argv[1]);
    return 0;
}
`

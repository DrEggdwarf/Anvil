; 01_hello.asm — Minimal x86-64 Linux hello world (no libc)
; Tests: ASM mode compile, load, run, basic registers, stepping
section .data
    msg db "Hello from Anvil!", 10
    len equ $ - msg

section .text
    global _start

_start:
    ; write(1, msg, len)
    mov rax, 1          ; sys_write
    mov rdi, 1          ; stdout
    lea rsi, [rel msg]  ; message
    mov rdx, len        ; length
    syscall

    ; exit(0)
    mov rax, 60         ; sys_exit
    xor rdi, rdi        ; code 0
    syscall

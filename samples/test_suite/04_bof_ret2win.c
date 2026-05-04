/* 04_bof_ret2win.c — Stack overflow with ret2win
 * Tests: Pwn mode checksec, cyclic, symbols, GOT/PLT, exploit writing
 * Compile: gcc -fno-stack-protector -no-pie -z execstack -o 04_bof_ret2win 04_bof_ret2win.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void win(void) {
    puts("[*] Flag: ANVIL{r3t2w1n_cl4ss1c}");
    exit(0);
}

void vulnerable(void) {
    char buffer[64];
    puts("Enter your name:");
    read(0, buffer, 256);  /* intentionally vulnerable — reads way more than buf */
    printf("Hello, %s!\n", buffer);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    vulnerable();
    return 0;
}

/* 05_format_string.c — Format string vulnerability
 * Tests: Pwn FmtStr tool, strings tab, vulnerability pattern detection
 * Compile: gcc -fno-stack-protector -no-pie -o 05_format_string 05_format_string.c
 */
#include <stdio.h>
#include <stdlib.h>

int secret = 0xdeadbeef;

void check_secret(void) {
    if (secret == 0x41414141) {
        puts("[*] Flag: ANVIL{fmt_str_w1n}");
        exit(0);
    }
    printf("secret = 0x%08x (need 0x41414141)\n", secret);
}

int main(void) {
    char buf[256];
    setvbuf(stdout, NULL, _IONBF, 0);

    for (int i = 0; i < 3; i++) {
        printf("Input [%d/3]: ", i + 1);
        fgets(buf, sizeof(buf), stdin);
        printf(buf);  /* intentionally vulnerable — format string */
        check_secret();
    }
    puts("Game over.");
    return 0;
}

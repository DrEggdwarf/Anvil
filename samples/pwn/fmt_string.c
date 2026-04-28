/* fmt_string.c — Format string vulnerability */
#include <stdio.h>
#include <stdlib.h>

int secret = 0xdeadbeef;

void win(void) {
    puts("[*] Flag: ANVIL{fmt_str_w1n}");
    exit(0);
}

void vuln(void) {
    char buf[128];
    printf("Input: ");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);  /* intentionally vulnerable — no format string */
    printf("\nsecret = 0x%x\n", secret);
    if (secret == 0x41414141) {
        win();
    }
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    vuln();
    return 0;
}

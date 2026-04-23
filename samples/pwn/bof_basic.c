/* bof_basic.c — Classic stack buffer overflow */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void win(void) {
    puts("[*] Flag: ANVIL{b0f_g3ts_ez}");
    exit(0);
}

void vuln(void) {
    char buf[64];
    printf("Input: ");
    read(0, buf, 256);  /* intentionally vulnerable — reads way more than buf */
    printf("You said: %s\n", buf);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    vuln();
    return 0;
}

/* ret2libc.c — NX enabled, need ret2libc/ROP */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void vuln(void) {
    char buf[64];
    printf("Input: ");
    read(0, buf, 256);  /* overflow but NX on → need ROP */
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("system@%p\n", (void *)system);  /* leak libc */
    vuln();
    return 0;
}

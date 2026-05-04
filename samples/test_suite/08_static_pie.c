/* 08_static_pie.c — PIE + full RELRO + canary binary
 * Tests: RE checksec badges (all green), GOT read-only, different CFG
 * Compile: gcc -fPIE -pie -fstack-protector-all -Wl,-z,relro,-z,now -o 08_static_pie 08_static_pie.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void process(const char *input) {
    if (strlen(input) > 10) {
        printf("Long input: %.10s...\n", input);
    } else {
        printf("Short input: %s\n", input);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <text>\n", argv[0]);
        return 1;
    }
    process(argv[1]);
    return 0;
}

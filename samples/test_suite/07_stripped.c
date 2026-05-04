/* 07_stripped.c — Stripped binary (no debug symbols)
 * Tests: RE with stripped binary — function discovery, strings-only analysis
 * Compile: gcc -O2 -s -o 07_stripped 07_stripped.c
 */
#include <stdio.h>
#include <string.h>

static int cipher(const char *input, char *output, int key) {
    int len = strlen(input);
    for (int i = 0; i < len; i++)
        output[i] = input[i] ^ key;
    output[len] = '\0';
    return len;
}

static void decrypt_flag(void) {
    char encrypted[] = {0x2b, 0x09, 0x1c, 0x17, 0x14, 0x3b,
                        0x53, 0x44, 0x52, 0x45, 0x5f, 0x44,
                        0x44, 0x41, 0x55, 0x00};
    char flag[32];
    cipher(encrypted, flag, 0x42);
    printf("Decoded: %s\n", flag);
}

int main(void) {
    char password[64];
    printf("Password: ");
    scanf("%63s", password);

    if (strcmp(password, "anvil2026") == 0) {
        puts("Access granted!");
        decrypt_flag();
    } else {
        puts("Access denied.");
    }
    return 0;
}

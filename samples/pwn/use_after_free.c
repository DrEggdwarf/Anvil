/* use_after_free.c — Heap UAF */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct user {
    char name[32];
    void (*greet)(struct user *);
};

void normal_greet(struct user *u) {
    printf("Hello, %s!\n", u->name);
}

void win(struct user *u) {
    (void)u;
    puts("[*] Flag: ANVIL{us3_aft3r_fr33}");
    exit(0);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);

    struct user *u = malloc(sizeof(*u));
    strcpy(u->name, "alice");
    u->greet = normal_greet;

    printf("1) Greet  2) Free  3) Edit  4) Greet again\n");

    int choice;
    while (scanf("%d", &choice) == 1) {
        switch (choice) {
            case 1: u->greet(u); break;
            case 2: free(u); puts("Freed!"); break;
            case 3:
                printf("New name: ");
                read(0, u, sizeof(*u));  /* write to freed chunk */
                break;
            case 4: u->greet(u); break;  /* UAF → call overwritten ptr */
        }
        printf("> ");
    }
    return 0;
}

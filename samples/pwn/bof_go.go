// bof_go.go — Buffer overflow in Go via CGo (unsafe)
package main

/*
#include <stdio.h>
#include <string.h>

void vuln(const char *input) {
    char buf[32];
    strcpy(buf, input);  // overflow
    printf("Echo: %s\n", buf);
}
*/
import "C"
import (
	"bufio"
	"fmt"
	"os"
)

func main() {
	fmt.Print("Input: ")
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Scan()
	C.vuln(C.CString(scanner.Text()))
}

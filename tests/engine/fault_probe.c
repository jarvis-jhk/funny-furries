#include "fault.h"
#include <signal.h>
int main(void) {ff_fault_init();raise(SIGABRT);return 0;}

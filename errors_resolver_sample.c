//#define WITH_INCLUDES
#ifdef WITH_INCLUDES
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#endif

int main(void)
{
	char buffer[1024];
	struct hostent *he;
	struct hostent resbuf = {0,};
	int ret, herrno;

	ret = gethostbyname_r("localhost", &resbuf, buffer, sizeof(buffer), &he, &herrno);
	if ( ret >= 0) {
		unsigned char *p = (unsigned char*)he->h_addr_list[0];
		printf("addr=%u.%u.%u.%u\n", p[0], p[1], p[2], p[3]);
	}
	sub(NULL);
	pthread_t thread;
	pthread_create(&thread, NULL, &sub, NULL);
	exit(EXIT_SUCCESS);
}

all: libsub.so

lib%.so: sub.o
	$(CC) -shared $(LDFLAGS) $(LDFLAGS-lib%.so) $^ -o $@


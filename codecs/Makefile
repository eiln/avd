CFLAGS := -fpic
H264_OBJECTS := h264.o h264_print.o
H264_OBJECTS := $(patsubst %,build/%,$(H264_OBJECTS))

.PHONY: all h264 clean
all: h264
h264: deh264 libh264.so

build/%.o: %.c
	@mkdir -p "$(dir $@)"
	$(CC) -c $(CFLAGS) -o $@ $<

deh264: $(H264_OBJECTS)
	$(CC) $@.c $(CFLAGS) -o $@ $^

libh264.so: $(H264_OBJECTS)
	$(CC) -shared -pthread -fPIC -fno-strict-aliasing libh264.c -o $@ $^

clean:
	rm -rf build/*
	rm -f *.so deh264


CFLAGS := -fpic -Wall -Wextra -pedantic -Wmissing-prototypes -Wstrict-prototypes
H264_OBJECTS := h264.o h2645.o h264_print.o
H264_OBJECTS := $(patsubst %,build/%,$(H264_OBJECTS))

H265_OBJECTS := h265.o h2645.o
H265_OBJECTS := $(patsubst %,build/%,$(H265_OBJECTS))

VP9_OBJECTS := ivf.o vp9.o vp9_data.o vp9_probs.o vpx_rac.o
VP9_OBJECTS := $(patsubst %,build/%,$(VP9_OBJECTS))

.PHONY: all h264 h265 vp9 clean

all: h264 h265 vp9
h265: deh265
h264: deh264 libh264.so
vp9: devp9 libvp9.so

build/%.o: %.c
	@mkdir -p "$(dir $@)"
	$(CC) -c $(CFLAGS) -o $@ $<

deh264: $(H264_OBJECTS)
	$(CC) $@.c $(CFLAGS) -o $@ $^

deh265: $(H265_OBJECTS)
	$(CC) $@.c $(CFLAGS) -o $@ $^

devp9: $(VP9_OBJECTS)
	$(CC) $@.c $(CFLAGS) -o $@ $^

libh264.so: $(H264_OBJECTS)
	$(CC) -shared -pthread -fPIC -fno-strict-aliasing libh264.c -o $@ $^

libvp9.so: $(VP9_OBJECTS)
	$(CC) -shared -pthread -fPIC -fno-strict-aliasing libvp9.c -o $@ $^

clean:
	rm -rf build/*
	rm -f *.so deh264 deh265 devp9

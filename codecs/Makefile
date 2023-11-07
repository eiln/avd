CFLAGS := -fpic
H264_OBJECTS := h264.o h264_print.o
H264_OBJECTS := $(patsubst %,build/%,$(H264_OBJECTS))

VP9_OBJECTS := ivf.o vp9.o vp9_data.o vp9_probs.o vpx_rac.o
VP9_OBJECTS := $(patsubst %,build/%,$(VP9_OBJECTS))

.PHONY: all h264 vp9 clean

all: h264 vp9
h264: deh264 libh264.so
vp9: devp9

build/%.o: %.c
	@mkdir -p "$(dir $@)"
	$(CC) -c $(CFLAGS) -o $@ $<

deh264: $(H264_OBJECTS)
	$(CC) $@.c $(CFLAGS) -o $@ $^

devp9: $(VP9_OBJECTS)
	$(CC) $@.c $(CFLAGS) -o $@ $^

libh264.so: $(H264_OBJECTS)
	$(CC) -shared -pthread -fPIC -fno-strict-aliasing libh264.c -o $@ $^

clean:
	rm -rf build/* out/*
	rm -f *.so deh264 devp9

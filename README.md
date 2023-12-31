
# Apple Video Decoder

Reverse-engineering the Apple Video Decoder (AVD) found on Apple Silicon, primarily the custom instruction streams driving each of the 3 (or 4) programmable per-codec processors of the first stage of the decoding pipeline. Given a stream of little-endian u32 words and the slice data, if all goes well, the processors will emit a codec-agnostic residual IR to be transformed by the shared stage two prediction block.


## Layout

- `avid/`: AVD Instruction model + Python stateless decoder glue. The "i" is to make Python happy
- `codecs/`: In-house C bitstream parsers
- `tools/`: Nifty tools/wrapper scripts to assist RE
- `avd_emu.py`: Coprocessor firmware emulator repurposed to spit out the instruction stream FIFO


## Status

All for my J293AP only, but different hardware revisions should only require minor encoding changes at the instruction HAL. The processors are really glue for a unified IR (this helps reuse silicon), and the hard part is figuring out the codec-specific quirks.

| Codec | Tracer | Emulator | Parser | FParser | Decoder | Matrixbench | Works? |
|-------|--------|----------|--------|---------|---------|-------------|--------|
| H.264 | Y      | Y        | Y      | Y       | Y       | Y           | Y      |
| H.265 | Y      | Y        | Y      | Y       | Y       | Y           | N      |
| VP9   | Y      | Y        | Y      | Y       | N       | Y           | N      |
| AV1   | N      | N        | N      | N       | N       | N           | N      |

Where
- **Tracer**: m1n1-side hypervisor hooks for tracing and dumping reference macOS source data.
- **Emulator**: `avd_emu.py` support for extracting the instruction stream out of trace dumps.
- **Parser**: Bitstream parser, demuxer if needed. "Syntax" in Apple driver terms.
- **FParser**: macOS frame_params struct + other blobs (e.g. VP9 probabilities blob) documentation.
- **Decoder**: Reference List Management (RLM) / DPB management logic. Includes memory allocation calculations.
- [**Matrixbench**](http://trac.ffmpeg.org/wiki/FancyFilteringExamples#waveformwithenvelope): Valid instruction stream generation for
	```
	ffmpeg -i matrixbench_mpeg2.mpg -s 1024x512 -pix_fmt yuv420p -c:v libx264 matrixbench.h264
	```
	Basically a POC and that it'll happen soon™.
- **Works?**: Stuff's never "done", but it's reasonably feature-complete in my view, e.g. supports all resolutions up to hardware cap (usually 4K), supports all notable features the macOS driver does, has been battle-tested with gnarly samples, etc. But all of the following asterisks apply.



### Notes & Caveats

### H.264 / AVC / JVT / MPEG-4 Part 10 / ISO/IEC 14496-10..

https://github.com/eiln/avd/assets/113484710/e7ab13fb-6472-47bf-93d3-1dbfb2667994

- What works:
	- High Profile i.e. 8-bit 4:2:0 I/P/B (i.e. normal x264 output)
	- High 4:2:2 Profile. Tested less than 4:2:0 but I haven't seen it not work
	- High 10 Profile (10-bit)
	- High 10 4:2:2 Profile
	- Up to hardware cap of 4096x4096 (that includes 4K)

- Works in macOS but not in mine:
	- frame_num gaps. This is a 10-line fix if I can see a sample.
	- Multiple slice groups. Ditto but 20

- Unsupported by hardware:
	- MBAFF/PAFF interlaced. Though you will not see this unless you work in broadcast.
	- Top/bottom field coding (x264 doesn't support)



### H.265 / HEVC

- H.264 but worse. Doable

- 12/16/2023: It works for normal videos encoded with normal parameters, e.g. a youtube video, but it's not passing all of the ITU-T conformance suite, which are samples designed to stress the decoder. We have most features down e.g. I/P/B, dequant/deblock, scaling lists, tiling/WPP, multiple slices, PCM, etc. Motion vector merging needs work. There's also some PPS extensions supported in hardware. Also 4:2:2 and 10-bit, but those shouldn't take long.


### VP9

- Looks easier than H.264. Up next


### AV1

- Would you like to buy me an M3? :D



## TODO

Other than RE-ing

- Add (more) tests
- Add SoC/Revision/Codenames/Caps matrix

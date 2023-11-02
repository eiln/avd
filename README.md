
# Apple Video Decoder

Reverse-engineering the Apple Video Decoder (AVD) found on Apple Silicon, primarily the custom instruction streams driving each of the 3 (or 4) programmable per-codec processors in the first stage of the decoding pipeline. Given a stream of little-endian u32 words and the slice data, if all goes well, the processors will emit codec-agnostic motion vector difference (MVD) predictions to be transformed by the shared stage two block.


## Layout

- `avid/`: AVD Instruction model + Python stateless decoder glue. The "i" is to make Python happy
- `codecs/`: In-house C bitstream parsers
- `tools/`: Nifty tools/wrapper scripts to assist RE
- `avd_emu.py`: Coprocessor firmware emulator that now serves to spit out the instruction stream FIFO


## Status

All for my J293AP only, but different hardware revisions should only require minor encoding changes at the instruction HAL. The processors are really glue for a unified IR (this helps reuse silicon), and the hard part is figuring out the codec quirks (mostly reference frames).

| Codec | Emulator | Parser | Decoder | Fparser | testsrc | matrixbench |
|-------|----------|--------|---------|---------|---------|-------------|
| H.264 | Y        | Y      | Y       | Y       | Y       | Y           |
| H.265 | N        | N      | N       | N       | N       | N           |
| VP9   | Y        | N      | N       | N       | N       | N           |
| AV1   | N        | N      | N       | N       | N       | N           |

Where
- Emulator: `avd_emu.py` support for extracting the instruction stream
- Parser: Bitstream parser, demuxer if needed (e.g. .ivf)
- Decoder: Reference/DPB management logic
- Fparser: Hypervisor trace (frame_params) parser utility
- testsrc/[matrixbench](http://trac.ffmpeg.org/wiki/FancyFilteringExamples#waveformwithenvelope): Valid instruction stream generation for
```
ffmpeg -f lavfi -i testsrc=duration=30:size=128x64:rate=1,format=yuv420p -c:v libx264 testsrc.h264
ffmpeg -i matrixbench_mpeg2.mpg -s 1024x512 -pix_fmt yuv420p -c:v libx264 matrixbench.h264
```

### Notes & Caveats

### H.264 / AVC / JVT / MPEG-4 Part 10 / ISO/IEC 14496-10..


https://github.com/eiln/avd/assets/113484710/2b03d4e5-430b-4f98-9647-ee07da402c6a

- What works:
	- High Profile (100) i.e. 8-bit 4:2:0 I/P/B (i.e. normal x264 output)
	- .. Almost

- Works in macOS but not in mine:
	- Long term references. This is mainly blocked by my parser/decoder impl
	- div16/div32 height/width works but the display buffer gets tiled/scaled weirdly. WIP
	- frame_num gaps
	- Scaling lists
	- Refresh on SPS change
	- 4:2:2

- Don't know if it works in macOS:
	- 4:4:4, 4:0:0 (monochrome)
	- Bitdepth > 8-bit
	- Top/bottom field coding (x264 doesn't support)
	- Display formats other than NV12
	- SPS Extensions
	- I_PCM or anything else funny that I'll have to literally make a sample for

- No:
	- SVC/MVC


### H.265 / HEVC

- H.264 but worse. Doable


### VP9

- Looks easier than H.264. Up next


### AV1

- Would you like to buy me an M3? :D



## TODO

Other than RE-ing

- Add tests
- Add SoC/Revision/Codenames/Caps matrix
- Write updated hw docs

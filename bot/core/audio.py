import asyncio
import logging

logger = logging.getLogger("audio")

async def convert_pcm_to_wav(pcm_data):
    """
    Uses FFmpeg to convert Raw 48k Stereo PCM -> 16k Mono WAV.
    """
    try:
        process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-f', 's16le', '-ar', '48000', '-ac', '2', '-i', 'pipe:0', # Input
            '-f', 'wav', '-ar', '16000', '-ac', '1', 'pipe:1',         # Output
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        wav_data, _ = await process.communicate(input=pcm_data)
        return wav_data
    except Exception as e:
        logger.error(f"FFmpeg Error: {e}")
        return None

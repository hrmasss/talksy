import { streamTextToSpeech } from "./speech-api";

const WAV_HEADER_BYTES = 44;
const AUDIO_START_LEAD_SECONDS = 0.05;

export interface StreamingAudioPlayback {
  finished: Promise<void>;
  stop: () => void;
}

function concatBytes(
  left: Uint8Array<ArrayBufferLike>,
  right: Uint8Array<ArrayBufferLike>,
): Uint8Array<ArrayBuffer> {
  if (left.length === 0) {
    return Uint8Array.from(right);
  }
  if (right.length === 0) {
    return Uint8Array.from(left);
  }

  const merged = new Uint8Array(left.length + right.length);
  merged.set(left);
  merged.set(right, left.length);
  return merged;
}

function looksLikeWavHeader(bytes: Uint8Array<ArrayBufferLike>): boolean {
  return (
    bytes.length >= 12 &&
    bytes[0] === 0x52 &&
    bytes[1] === 0x49 &&
    bytes[2] === 0x46 &&
    bytes[3] === 0x46 &&
    bytes[8] === 0x57 &&
    bytes[9] === 0x41 &&
    bytes[10] === 0x56 &&
    bytes[11] === 0x45
  );
}

function pcm16ToFloat32(bytes: Uint8Array<ArrayBufferLike>): Float32Array<ArrayBuffer> {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const samples = new Float32Array(bytes.byteLength / 2);

  for (let i = 0; i < samples.length; i += 1) {
    samples[i] = view.getInt16(i * 2, true) / 32768;
  }

  return samples;
}

async function playPcmResponse(response: Response): Promise<StreamingAudioPlayback> {
  if (!response.body) {
    throw new Error("Streaming audio is not available in this browser.");
  }

  const audioContext = new AudioContext();
  const reader = response.body.getReader();
  const scheduledSources: AudioBufferSourceNode[] = [];
  const sampleRate = Number(response.headers.get("X-Audio-Sample-Rate") ?? "24000");

  let stopped = false;
  let nextStartTime = 0;
  let leftoverByte = new Uint8Array(0);
  let headerProbeBuffer = new Uint8Array(0);
  let probingForWavHeader = true;

  const stop = () => {
    if (stopped) {
      return;
    }

    stopped = true;
    void reader.cancel().catch(() => undefined);
    for (const source of scheduledSources) {
      try {
        source.stop();
      } catch {
        // Ignore already-ended sources.
      }
    }
    void audioContext.close().catch(() => undefined);
  };

  const finished = (async () => {
    try {
      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }

      nextStartTime = audioContext.currentTime;

      while (!stopped) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        if (!value || value.byteLength === 0) {
          continue;
        }

        let chunk = value;

        if (probingForWavHeader) {
          headerProbeBuffer = concatBytes(headerProbeBuffer, chunk);
          if (headerProbeBuffer.length < 12) {
            continue;
          }

          if (looksLikeWavHeader(headerProbeBuffer)) {
            if (headerProbeBuffer.length < WAV_HEADER_BYTES) {
              continue;
            }
            chunk = headerProbeBuffer.slice(WAV_HEADER_BYTES);
          } else {
            chunk = headerProbeBuffer;
          }

          headerProbeBuffer = new Uint8Array(0);
          probingForWavHeader = false;
        }

        if (leftoverByte.length > 0) {
          chunk = concatBytes(leftoverByte, chunk);
          leftoverByte = new Uint8Array(0);
        }

        if (chunk.byteLength % 2 === 1) {
          leftoverByte = chunk.slice(chunk.byteLength - 1);
          chunk = chunk.slice(0, chunk.byteLength - 1);
        }

        if (chunk.byteLength === 0) {
          continue;
        }

        const samples = pcm16ToFloat32(chunk);
        const audioBuffer = audioContext.createBuffer(1, samples.length, sampleRate);
        audioBuffer.getChannelData(0).set(samples);

        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        scheduledSources.push(source);

        const startAt = Math.max(audioContext.currentTime + AUDIO_START_LEAD_SECONDS, nextStartTime);
        source.start(startAt);
        nextStartTime = startAt + audioBuffer.duration;
      }

      if (!stopped) {
        const remainingMs = Math.max(0, (nextStartTime - audioContext.currentTime) * 1000);
        if (remainingMs > 0) {
          await new Promise((resolve) => window.setTimeout(resolve, remainingMs));
        }
      }
    } finally {
      void reader.cancel().catch(() => undefined);
      void audioContext.close().catch(() => undefined);
    }
  })();

  return { finished, stop };
}

export async function playStreamingTextToSpeech(
  text: string,
  voice = "Kore",
): Promise<StreamingAudioPlayback> {
  const response = await streamTextToSpeech(text, voice);
  return playPcmResponse(response);
}

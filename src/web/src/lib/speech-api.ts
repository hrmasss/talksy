import { requestArrayBuffer, requestJson, requestResponse } from "./api-client";

export interface UserSettings {
  groq_api_keys: string[];
  has_groq_keys: boolean;
}

export async function speechToText(audio: Blob): Promise<string> {
  const formData = new FormData();
  formData.append("data", audio, "recording.webm");

  const response = await requestJson<{ text: string }>("/speech/stt", {
    method: "POST",
    body: formData,
  });

  return response.text;
}

export function textToSpeech(text: string, voice = "troy"): Promise<ArrayBuffer> {
  return requestArrayBuffer("/speech/tts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text, voice }),
  });
}

export function streamTextToSpeech(text: string, voice = "troy"): Promise<Response> {
  return requestResponse("/speech/tts/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text, voice }),
  });
}

export function getUserSettings(): Promise<UserSettings> {
  return requestJson<UserSettings>("/users/me/settings");
}

export function updateUserSettings(payload: {
  groq_api_keys?: string[];
}): Promise<UserSettings> {
  return requestJson<UserSettings>("/users/me/settings", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

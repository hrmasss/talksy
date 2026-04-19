import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  RiAddLine,
  RiCheckLine,
  RiDeleteBinLine,
  RiKey2Line,
  RiLoader4Line,
  RiShieldKeyholeLine,
} from "@remixicon/react";
import { getUserSettings, updateUserSettings, type UserSettings } from "@/lib/speech-api";
import { toast } from "sonner";
import { getUserFacingErrorMessage } from "@/lib/app-errors";

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [keys, setKeys] = useState<string[]>([""]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    getUserSettings()
      .then((s) => {
        setSettings(s);
        if (s.groq_api_keys.length > 0) {
          // Pre-fill with masked values (user needs to replace to update)
          setKeys(s.groq_api_keys);
        }
      })
      .catch(() => {
        toast.error("Failed to load settings");
      })
      .finally(() => setLoading(false));
  }, []);

  const handleKeyChange = (index: number, value: string) => {
    const updated = [...keys];
    updated[index] = value;
    setKeys(updated);
    setDirty(true);
  };

  const addKey = () => {
    setKeys([...keys, ""]);
    setDirty(true);
  };

  const removeKey = (index: number) => {
    const updated = keys.filter((_, i) => i !== index);
    setKeys(updated.length ? updated : [""]);
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Send all non-empty keys, even masked ones (backend will handle them).
      // A masked key means "leave as is".
      const cleanKeys = keys.filter((k) => k.trim());
      const response = await updateUserSettings({ groq_api_keys: cleanKeys });
      setSettings(response);
      setKeys(response.groq_api_keys.length > 0 ? response.groq_api_keys : [""]);
      setDirty(false);
      toast.success("Settings saved successfully");
    } catch (e) {
      toast.error(getUserFacingErrorMessage(e, "Failed to save settings"));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <RiLoader4Line className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your API keys and preferences
        </p>
      </div>

      {/* API Keys Section */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <RiShieldKeyholeLine className="h-4.5 w-4.5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base">Groq API Keys</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                Add your own Groq API keys to use platform features.
                You can add multiple keys for better rate limits.
              </p>
            </div>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="pt-5">
          {settings?.has_groq_keys && (
            <div className="mb-4 flex items-center gap-2">
              <Badge variant="secondary" className="gap-1 text-xs">
                <RiCheckLine className="h-3 w-3" />
                {settings.groq_api_keys.length} key{settings.groq_api_keys.length !== 1 ? "s" : ""} configured
              </Badge>
            </div>
          )}

          <div className="space-y-3">
            {keys.map((key, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="relative flex-1">
                  <RiKey2Line className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    type="password"
                    placeholder="gsk_..."
                    value={key}
                    onChange={(e) => handleKeyChange(index, e.target.value)}
                    className="pl-9 font-mono text-sm"
                  />
                </div>
                {keys.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 text-muted-foreground hover:text-destructive"
                    onClick={() => removeKey(index)}
                  >
                    <RiDeleteBinLine className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            className="mt-3 gap-1.5"
            onClick={addKey}
          >
            <RiAddLine className="h-3.5 w-3.5" />
            Add another key
          </Button>

          <Separator className="my-5" />

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Keys are stored securely and never shared. Get a key from{" "}
              <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline underline-offset-2 hover:text-primary/80"
              >
                Groq Console
              </a>
              .
            </p>
            <Button
              size="sm"
              disabled={!dirty || saving}
              onClick={handleSave}
            >
              {saving ? (
                <RiLoader4Line className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <RiCheckLine className="mr-1.5 h-3.5 w-3.5" />
              )}
              Save
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  RiMicLine,
  RiSendPlaneLine,
  RiStopCircleLine,
  RiBookOpenLine,
  RiQuestionLine,
  RiVoiceprintLine,
  RiLoader4Line,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { speechToText } from "@/lib/speech-api";
import { toast } from "sonner";

const practiceTypes = [
  {
    id: "speaking",
    icon: RiVoiceprintLine,
    label: "Speaking",
    description: "Practice pronunciation and fluency",
  },
  {
    id: "quiz",
    icon: RiQuestionLine,
    label: "Quiz",
    description: "Test your knowledge",
  },
  {
    id: "guide",
    icon: RiBookOpenLine,
    label: "Guide",
    description: "Learn exam strategies",
  },
];

export default function AppHome() {
  const [message, setMessage] = useState("");
  const [selectedType, setSelectedType] = useState("speaking");
  const [transcribing, setTranscribing] = useState(false);
  const { isRecording, startRecording, stopRecording } = useAudioRecorder();

  const handleSend = () => {
    if (!message.trim()) return;
    // TODO: Send message to AI
    setMessage("");
  };

  const toggleRecording = async () => {
    if (isRecording) {
      setTranscribing(true);
      try {
        const blob = await stopRecording();
        if (blob.size > 0) {
          const text = await speechToText(blob);
          setMessage((prev) => (prev ? prev + " " + text : text));
        }
      } catch (e) {
        toast.error("Could not transcribe audio. Check your API key in Settings.");
      } finally {
        setTranscribing(false);
      }
    } else {
      try {
        await startRecording();
      } catch {
        toast.error("Microphone access denied.");
      }
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-7rem)] max-w-3xl flex-col px-6 py-6 md:h-[calc(100vh-3.5rem)]">
      {/* Practice Type Selector */}
      <div className="mb-6 flex items-center justify-center gap-2">
        {practiceTypes.map((type) => (
          <Button
            key={type.id}
            variant={selectedType === type.id ? "default" : "outline"}
            size="sm"
            className="gap-2"
            onClick={() => setSelectedType(type.id)}
          >
            <type.icon className="h-4 w-4" />
            <span className="hidden sm:inline">{type.label}</span>
          </Button>
        ))}
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto">
        {/* Empty State */}
        <div className="flex h-full flex-col items-center justify-center text-center">
          <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <RiMicLine className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-xl font-medium">
            {selectedType === "speaking" && "Ready to practice speaking?"}
            {selectedType === "quiz" && "Test your knowledge"}
            {selectedType === "guide" && "Learn exam strategies"}
          </h2>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground">
            {selectedType === "speaking" &&
              "Start a conversation or use voice to practice your English speaking skills with AI feedback."}
            {selectedType === "quiz" &&
              "Answer questions and get instant feedback on your responses."}
            {selectedType === "guide" &&
              "Ask about exam tips, strategies, or get explanations on any topic."}
          </p>

          {/* Quick Prompts */}
          <div className="mt-8 flex flex-wrap justify-center gap-2">
            {selectedType === "speaking" && (
              <>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  Describe a memorable trip
                </Badge>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  Talk about your hometown
                </Badge>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  Discuss a book you read
                </Badge>
              </>
            )}
            {selectedType === "quiz" && (
              <>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  IELTS Reading Quiz
                </Badge>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  Grammar Practice
                </Badge>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  Vocabulary Test
                </Badge>
              </>
            )}
            {selectedType === "guide" && (
              <>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  IELTS Writing Tips
                </Badge>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  Speaking Band Scores
                </Badge>
                <Badge variant="secondary" className="cursor-pointer hover:bg-accent">
                  Test Day Preparation
                </Badge>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Input Area */}
      <Card className="mt-4 flex items-end gap-2 p-3">
        <Button
          variant={isRecording ? "destructive" : "outline"}
          size="icon"
          className={cn(
            "shrink-0 rounded-full transition-all",
            isRecording && "animate-pulse"
          )}
          onClick={toggleRecording}
          disabled={transcribing}
        >
          {transcribing ? (
            <RiLoader4Line className="h-5 w-5 animate-spin" />
          ) : isRecording ? (
            <RiStopCircleLine className="h-5 w-5" />
          ) : (
            <RiMicLine className="h-5 w-5" />
          )}
        </Button>

        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message or click the mic to speak..."
          className="min-h-[44px] max-h-32 resize-none border-0 bg-transparent p-2 focus-visible:ring-0"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
        />

        <Button
          size="icon"
          className="shrink-0 rounded-full"
          onClick={handleSend}
          disabled={!message.trim()}
        >
          <RiSendPlaneLine className="h-5 w-5" />
        </Button>
      </Card>
    </div>
  );
}

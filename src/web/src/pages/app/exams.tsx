import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RiBookLine, RiTimeLine, RiArrowRightLine } from "@remixicon/react";
import { useOnboardingGate } from "./onboarding-gate";

const examTypes = [
  {
    id: "ielts",
    name: "IELTS Academic",
    description: "Practice all four sections",
    duration: "2h 45m",
    sections: ["Listening", "Reading", "Writing", "Speaking"],
  },
  {
    id: "ielts-general",
    name: "IELTS General",
    description: "General Training version",
    duration: "2h 45m",
    sections: ["Listening", "Reading", "Writing", "Speaking"],
  },
  {
    id: "pte",
    name: "PTE Academic",
    description: "Computer-based test practice",
    duration: "3h",
    sections: ["Speaking & Writing", "Reading", "Listening"],
  },
  {
    id: "toefl",
    name: "TOEFL iBT",
    description: "Internet-based test practice",
    duration: "3h 30m",
    sections: ["Reading", "Listening", "Speaking", "Writing"],
  },
];

export default function ExamsPage() {
  const { requireOnboarding } = useOnboardingGate();

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Exams</h1>
        <p className="text-muted-foreground">
          Choose an exam type to start practicing
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {examTypes.map((exam) => (
          <Card
            key={exam.id}
            className="group cursor-pointer transition-all hover:border-primary/50 hover:shadow-sm"
          >
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <RiBookLine className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{exam.name}</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {exam.description}
                    </p>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <RiTimeLine className="h-4 w-4" />
                {exam.duration}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {exam.sections.map((section) => (
                  <Badge key={section} variant="secondary" className="text-xs">
                    {section}
                  </Badge>
                ))}
              </div>
              <Button
                variant="ghost"
                className="w-full justify-between group-hover:bg-accent"
                onClick={() => requireOnboarding()}
              >
                Start Practice
                <RiArrowRightLine className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

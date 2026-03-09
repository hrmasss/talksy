import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  RiArrowDownLine,
  RiArrowUpLine,
  RiBarChartLine,
  RiBookOpenLine,
  RiCalendarLine,
  RiEdit2Line,
  RiHeadphoneLine,
  RiLoader4Line,
  RiMicLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import {
  getProgress,
  getTestHistory,
  type ProgressOverview,
  type TestHistory,
} from "@/lib/ielts-api";
import { useAuth } from "@/lib/auth";

const sectionMeta: Record<string, { icon: typeof RiMicLine; color: string; bg: string }> = {
  listening: { icon: RiHeadphoneLine, color: "text-blue-600", bg: "bg-blue-500/10" },
  reading: { icon: RiBookOpenLine, color: "text-emerald-600", bg: "bg-emerald-500/10" },
  writing: { icon: RiEdit2Line, color: "text-amber-600", bg: "bg-amber-500/10" },
  speaking: { icon: RiMicLine, color: "text-purple-600", bg: "bg-purple-500/10" },
};

export default function ProgressPage() {
  const { user } = useAuth();
  const userId = user?.id;
  const [progress, setProgress] = useState<ProgressOverview | null>(null);
  const [history, setHistory] = useState<TestHistory | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    const currentUserId = userId;
    async function load() {
      try {
        const [p, h] = await Promise.all([
          getProgress(currentUserId).catch(() => null),
          getTestHistory(currentUserId).catch(() => null),
        ]);
        setProgress(p);
        setHistory(h);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [userId]);

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <RiLoader4Line className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const scoreHistory = progress?.score_history ?? [];
  const sectionScores = progress?.section_scores ?? {};

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="mb-6 text-2xl font-bold tracking-tight">Progress</h1>

      {/* Score Trend Chart (simplified bar visualization) */}
      {scoreHistory.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <RiBarChartLine className="h-4 w-4" />
              Band Score Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 h-32">
              {scoreHistory.slice(-12).map((entry, i) => {
                const band = entry.overall_band ?? 0;
                const height = (band / 9) * 100;
                return (
                  <div
                    key={i}
                    className="group relative flex flex-1 flex-col items-center"
                  >
                    <div className="relative w-full flex justify-center">
                      <div
                        className={cn(
                          "w-full max-w-8 rounded-t transition-all",
                          band >= 7
                            ? "bg-emerald-500"
                            : band >= 5.5
                              ? "bg-amber-500"
                              : "bg-red-400"
                        )}
                        style={{ height: `${height}%`, minHeight: band > 0 ? 4 : 0 }}
                      />
                    </div>
                    <span className="mt-1 text-[10px] text-muted-foreground">
                      {new Date(entry.date).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                    {/* Tooltip on hover */}
                    <div className="absolute -top-7 hidden rounded bg-foreground px-1.5 py-0.5 text-[10px] text-background group-hover:block">
                      {band}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Section Score Cards */}
      <div className="mb-6 grid gap-3 sm:grid-cols-4">
        {(["listening", "reading", "writing", "speaking"] as const).map((section) => {
          const meta = sectionMeta[section];
          const score = sectionScores[section] ?? 0;

          // Compute trend from score_history
          const sectionHistory = scoreHistory
            .map((e) => e[section])
            .filter((v): v is number => v != null);
          const trend =
            sectionHistory.length >= 2
              ? sectionHistory[sectionHistory.length - 1] -
                sectionHistory[sectionHistory.length - 2]
              : 0;

          return (
            <Card key={section}>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", meta.bg)}>
                    <meta.icon className={cn("h-4 w-4", meta.color)} />
                  </div>
                  {trend !== 0 && (
                    <span
                      className={cn(
                        "flex items-center gap-0.5 text-xs font-medium",
                        trend > 0 ? "text-emerald-600" : "text-red-500"
                      )}
                    >
                      {trend > 0 ? (
                        <RiArrowUpLine className="h-3 w-3" />
                      ) : (
                        <RiArrowDownLine className="h-3 w-3" />
                      )}
                      {Math.abs(trend).toFixed(1)}
                    </span>
                  )}
                </div>
                <div className="mt-2 text-2xl font-bold">{score || "—"}</div>
                <div className="text-xs capitalize text-muted-foreground">
                  {section}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Test History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <RiCalendarLine className="h-4 w-4" />
            Test History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {history && history.items.length > 0 ? (
            <div className="divide-y divide-border/50">
              {history.items.map((item) => {
                const meta = sectionMeta[item.section] || sectionMeta.listening;
                return (
                  <div key={item.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                    <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", meta.bg)}>
                      <meta.icon className={cn("h-4 w-4", meta.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium capitalize">
                        {item.section} Test
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(item.date).toLocaleDateString(undefined, {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                        })}
                      </div>
                    </div>
                    <Badge
                      variant="secondary"
                      className={cn(
                        "text-sm font-semibold",
                        (item.band_score ?? 0) >= 7
                          ? "text-emerald-600"
                          : (item.band_score ?? 0) >= 5.5
                            ? "text-amber-600"
                            : "text-red-500"
                      )}
                    >
                      {item.band_score ?? "—"}
                    </Badge>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No test results yet. Take a mock test to see your progress.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

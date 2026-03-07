import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { RiEyeLine, RiEyeOffLine, RiArrowRightLine } from "@remixicon/react";

const EXAM_OPTIONS = [
  { value: "ielts", label: "IELTS" },
  { value: "pte", label: "PTE" },
  { value: "toefl", label: "TOEFL" },
];

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [targetExam, setTargetExam] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signup({
        email,
        password,
        full_name: fullName,
        target_exam: targetExam || undefined,
      });
      navigate("/app");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border/50">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
          <Link to="/" className="text-xl font-semibold tracking-tight">
            Talksy
          </Link>
          <nav className="flex items-center gap-4">
            <Link to="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Content */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="text-2xl">Create your account</CardTitle>
              <CardDescription>
                Start preparing for your English exam today
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {error}
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="fullName">Full Name</Label>
                  <Input
                    id="fullName"
                    type="text"
                    placeholder="Jane Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    autoComplete="name"
                    autoFocus
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Min 8 chars, upper + lower + digit"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      className="pr-10"
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => setShowPassword((v) => !v)}
                      tabIndex={-1}
                      aria-label={
                        showPassword ? "Hide password" : "Show password"
                      }
                    >
                      {showPassword ? (
                        <RiEyeOffLine className="size-4" />
                      ) : (
                        <RiEyeLine className="size-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="targetExam">Target Exam (optional)</Label>
                  <div className="flex gap-2">
                    {EXAM_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        className={`flex-1 rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                          targetExam === opt.value
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-input bg-transparent text-muted-foreground hover:border-ring hover:text-foreground"
                        }`}
                        onClick={() =>
                          setTargetExam((v) =>
                            v === opt.value ? "" : opt.value
                          )
                        }
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Creating account…
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      Get Started
                      <RiArrowRightLine className="size-4" />
                    </span>
                  )}
                </Button>
              </form>

              <div className="mt-6 text-center text-sm text-muted-foreground">
                Already have an account?{" "}
                <Link
                  to="/login"
                  className="font-medium text-primary hover:underline underline-offset-4"
                >
                  Sign in
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

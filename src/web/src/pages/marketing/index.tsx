import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  RiMicLine,
  RiBookOpenLine,
  RiTimeLine,
  RiBarChartLine,
  RiGlobalLine,
  RiShieldCheckLine,
} from "@remixicon/react";

const features = [
  {
    icon: RiMicLine,
    title: "Voice Practice",
    description:
      "Natural AI conversations for speaking practice. Get instant feedback on pronunciation and fluency.",
  },
  {
    icon: RiBookOpenLine,
    title: "Exam Preparation",
    description:
      "Full mock exams for IELTS, PTE, and TOEFL. Practice with real exam formats and timing.",
  },
  {
    icon: RiTimeLine,
    title: "Flexible Learning",
    description:
      "Study at your own pace, anytime. Short sessions or full practice tests—you decide.",
  },
  {
    icon: RiBarChartLine,
    title: "Progress Tracking",
    description:
      "Detailed analytics on your performance. See where you excel and where to improve.",
  },
  {
    icon: RiGlobalLine,
    title: "Multiple Exams",
    description:
      "One platform for IELTS, PTE, and TOEFL. Switch between exams seamlessly.",
  },
  {
    icon: RiShieldCheckLine,
    title: "AI-Powered Scoring",
    description:
      "Get accurate scores that match real exam criteria. Detailed feedback on every response.",
  },
];

export default function MarketingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/50">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
          <Link to="/" className="text-xl font-semibold tracking-tight">
            Talksy
          </Link>
          <nav className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link to="/app">
              <Button size="sm">Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 py-24 text-center">
        <div className="mx-auto max-w-2xl">
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Master English exams with AI-powered practice
          </h1>
          <p className="mt-6 text-lg text-muted-foreground">
            Prepare for IELTS, PTE, and TOEFL with natural voice conversations
            and authentic mock exams. Practice speaking, listening, reading, and
            writing—all in one place.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link to="/app">
              <Button size="lg" className="h-12 px-8">
                Start Practicing Free
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border/50 bg-muted/30">
        <div className="mx-auto max-w-5xl px-6 py-24">
          <h2 className="text-center text-2xl font-semibold tracking-tight">
            Everything you need to succeed
          </h2>
          <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.title} className="space-y-3">
                <feature.icon className="h-6 w-6 text-primary" />
                <h3 className="font-medium">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border/50">
        <div className="mx-auto max-w-5xl px-6 py-24 text-center">
          <h2 className="text-2xl font-semibold tracking-tight">
            Ready to improve your score?
          </h2>
          <p className="mt-4 text-muted-foreground">
            Join thousands of learners preparing for their English exams.
          </p>
          <div className="mt-8">
            <Link to="/app">
              <Button size="lg" className="h-12 px-8">
                Get Started Now
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50">
        <div className="mx-auto max-w-5xl px-6 py-8">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>© 2025 Talksy. All rights reserved.</span>
            <div className="flex gap-6">
              <a href="#" className="hover:text-foreground transition-colors">
                Privacy
              </a>
              <a href="#" className="hover:text-foreground transition-colors">
                Terms
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

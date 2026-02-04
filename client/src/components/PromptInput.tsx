import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Sparkles, Send, Loader2 } from "lucide-react";

interface PromptInputProps {
  onSubmit: (prompt: string) => void;
  isLoading: boolean;
}

const EXAMPLE_PROMPTS = [
  "귀여운 고양이 캐릭터, 큰 눈, 분홍색 귀",
  "SF 로봇 전사, 메탈릭 블루 아머",
  "판타지 엘프 마법사, 녹색 로브",
  "카툰 스타일 용, 날개와 뿔",
];

export function PromptInput({ onSubmit, isLoading }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = () => {
    if (prompt.trim() && !isLoading) {
      onSubmit(prompt.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <Card className="border-card-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center gap-2 text-primary">
          <Sparkles className="w-5 h-5" />
          <span className="font-semibold text-foreground">캐릭터 프롬프트</span>
        </div>

        <div className="relative">
          <Textarea
            placeholder="생성하고 싶은 3D 휴머노이드 캐릭터를 설명하세요..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="min-h-[120px] resize-none pr-12 text-base"
            data-testid="input-prompt"
          />
          <Button
            size="icon"
            className="absolute right-2 bottom-2"
            onClick={handleSubmit}
            disabled={!prompt.trim() || isLoading}
            data-testid="button-generate"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>

        <div className="space-y-2">
          <span className="text-xs text-muted-foreground">예시 프롬프트:</span>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((example, index) => (
              <button
                key={index}
                onClick={() => setPrompt(example)}
                disabled={isLoading}
                className="px-3 py-1.5 text-xs rounded-md bg-accent text-accent-foreground hover-elevate active-elevate-2 transition-colors disabled:opacity-50"
                data-testid={`button-example-${index}`}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

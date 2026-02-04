import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sparkles, Send, Loader2 } from "lucide-react";

interface GenerationOptions {
  prompt: string;
  style: string;
  polyLevel: string;
}

interface PromptInputProps {
  onSubmit: (options: GenerationOptions) => void;
  isLoading: boolean;
}

const STYLE_OPTIONS = [
  { value: "stylized", label: "스타일라이즈드", desc: "5-6등신" },
  { value: "chibi", label: "치비", desc: "1.5-2등신, 큰 머리" },
  { value: "sd", label: "SD", desc: "2-3등신" },
  { value: "mobile", label: "모바일", desc: "초저폴리" },
  { value: "minifig", label: "미니피규어", desc: "레고 스타일" },
  { value: "cartoon", label: "카툰", desc: "과장된 비율" },
  { value: "realistic", label: "리얼리스틱", desc: "8등신" },
];

const POLY_LEVEL_OPTIONS = [
  { value: "ultra_low", label: "초저폴리", desc: "~300 tris, 모바일" },
  { value: "low", label: "저폴리", desc: "~800 tris" },
  { value: "medium", label: "중간", desc: "~1500 tris" },
  { value: "high", label: "고폴리", desc: "~3000 tris, PC/콘솔" },
];

const EXAMPLE_PROMPTS = [
  "귀여운 고양이 캐릭터, 큰 눈, 분홍색 귀",
  "SF 로봇 전사, 메탈릭 블루 아머",
  "판타지 엘프 마법사, 녹색 로브",
  "카툰 스타일 용, 날개와 뿔",
];

export function PromptInput({ onSubmit, isLoading }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("stylized");
  const [polyLevel, setPolyLevel] = useState("medium");

  const handleSubmit = () => {
    if (prompt.trim() && !isLoading) {
      onSubmit({ prompt: prompt.trim(), style, polyLevel });
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

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">캐릭터 스타일</label>
            <Select value={style} onValueChange={setStyle} disabled={isLoading}>
              <SelectTrigger data-testid="select-style" className="w-full">
                <SelectValue placeholder="스타일 선택" />
              </SelectTrigger>
              <SelectContent>
                {STYLE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{opt.label}</span>
                      <span className="text-muted-foreground text-xs">({opt.desc})</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">폴리곤 레벨</label>
            <Select value={polyLevel} onValueChange={setPolyLevel} disabled={isLoading}>
              <SelectTrigger data-testid="select-poly-level" className="w-full">
                <SelectValue placeholder="폴리곤 레벨" />
              </SelectTrigger>
              <SelectContent>
                {POLY_LEVEL_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{opt.label}</span>
                      <span className="text-muted-foreground text-xs">({opt.desc})</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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

export type { GenerationOptions };

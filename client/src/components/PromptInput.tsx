import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Sparkles, Send, Loader2, ImagePlus, X, Wand2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface GenerationOptions {
  prompt: string;
  referenceImage?: string;
}

interface ImageAnalysisResult {
  success: boolean;
  attributes: {
    description: string;
    style: string;
    colors: string[];
    bodyType: {
      preset: string;
      muscular?: number;
      fat?: number;
    };
    gender: string;
    archetype: string;
    suggestedPrompt: string;
  };
  generationOptions: {
    prompt: string;
    style: string;
    bodyType: string;
    gender: string;
  };
}

interface PromptInputProps {
  onSubmit: (options: GenerationOptions) => void;
  isLoading: boolean;
}

const EXAMPLE_PROMPTS = [
  "로우폴리 기사, 은색 갑옷, 검을 들고 있음, 근육질 남성",
  "귀여운 고양이 휴머노이드, 분홍색 귀, 큰 눈, 꼬리, 치비 스타일",
  "SF 로봇 전사, 메탈릭 블루, 각진 어깨, 바이저 헬멧, 높은 폴리곤",
  "판타지 마법사 엘프 여성, 뾰족한 귀, 보라색 로브, 지팡이",
];

export function PromptInput({ onSubmit, isLoading }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");
  const [referenceImage, setReferenceImage] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const analyzeImageMutation = useMutation({
    mutationFn: async (imageData: string) => {
      const response = await apiRequest("POST", "/api/analyze-image", { image: imageData });
      return response.json() as Promise<ImageAnalysisResult>;
    },
    onSuccess: (data) => {
      if (data.success && data.generationOptions) {
        setPrompt(data.generationOptions.prompt);
        toast({
          title: "이미지 분석 완료",
          description: `${data.attributes.archetype} 캐릭터로 인식되었습니다. 프롬프트가 자동으로 채워졌습니다.`,
        });
      }
    },
    onError: (error) => {
      toast({
        title: "이미지 분석 실패",
        description: error instanceof Error ? error.message : "알 수 없는 오류",
        variant: "destructive",
      });
    },
  });

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      toast({
        title: "잘못된 파일",
        description: "이미지 파일만 업로드할 수 있습니다.",
        variant: "destructive",
      });
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "파일이 너무 큽니다",
        description: "5MB 이하의 이미지를 업로드해주세요.",
        variant: "destructive",
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setImagePreview(dataUrl);
      setReferenceImage(dataUrl);
    };
    reader.readAsDataURL(file);
  };

  const handleAnalyzeImage = () => {
    if (referenceImage) {
      analyzeImageMutation.mutate(referenceImage);
    }
  };

  const handleClearImage = () => {
    setReferenceImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = () => {
    // Allow submit with either prompt OR image (or both)
    const hasPrompt = prompt.trim().length > 0;
    const hasImage = !!referenceImage;
    
    if ((hasPrompt || hasImage) && !isLoading) {
      onSubmit({ 
        prompt: prompt.trim() || "(이미지 기반 생성)",
        referenceImage: referenceImage || undefined
      });
    }
  };
  
  const canSubmit = (prompt.trim().length > 0 || !!referenceImage) && !isLoading;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <Card className="border-card-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-primary">
            <Sparkles className="w-5 h-5" />
            <span className="font-semibold text-foreground">캐릭터 프롬프트</span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            className="hidden"
            data-testid="input-image-upload"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || analyzeImageMutation.isPending}
            data-testid="button-upload-image"
          >
            <ImagePlus className="w-4 h-4 mr-2" />
            레퍼런스 이미지
          </Button>
        </div>

        {imagePreview && (
          <div className="relative flex items-start gap-3 p-3 rounded-lg bg-accent/30" data-testid="container-image-preview">
            <img
              src={imagePreview}
              alt="레퍼런스 이미지"
              className="w-20 h-20 object-cover rounded-md border"
              data-testid="img-reference-preview"
            />
            <div className="flex-1 space-y-2">
              <p className="text-sm text-muted-foreground" data-testid="text-analyze-hint">
                이미지를 분석하여 프롬프트를 자동으로 생성합니다.
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleAnalyzeImage}
                  disabled={analyzeImageMutation.isPending || isLoading}
                  data-testid="button-analyze-image"
                >
                  {analyzeImageMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Wand2 className="w-4 h-4 mr-2" />
                  )}
                  이미지 분석
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleClearImage}
                  disabled={analyzeImageMutation.isPending || isLoading}
                  data-testid="button-clear-image"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        )}

        <div className="relative">
          <Textarea
            placeholder="생성하고 싶은 3D 휴머노이드 캐릭터를 설명하세요... (예: 로우폴리 여성 마법사, 치비 스타일, 파란 로브)"
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
            disabled={!canSubmit}
            data-testid="button-generate"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>

        <div className="p-3 rounded-lg bg-muted/50 text-xs text-muted-foreground">
          <p className="font-medium mb-1">프롬프트 팁:</p>
          <p>텍스트 프롬프트, 이미지, 또는 둘 다 사용할 수 있습니다. 이미지만 업로드하면 Gemini Vision이 자동으로 캐릭터를 분석하여 생성합니다.</p>
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

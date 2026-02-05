import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Sparkles, Send, Loader2, ImagePlus, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface GenerationOptions {
  prompt: string;
  referenceImage?: string;
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

  const resizeImage = (file: File, maxWidth: number = 800, maxHeight: number = 800, quality: number = 0.8): Promise<string> => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const reader = new FileReader();
      const isPng = file.type === "image/png";
      
      reader.onload = (e) => {
        img.src = e.target?.result as string;
      };
      
      img.onload = () => {
        let { width, height } = img;
        
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }
        
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Canvas context not available"));
          return;
        }
        
        ctx.drawImage(img, 0, 0, width, height);
        const outputType = isPng ? "image/png" : "image/jpeg";
        const dataUrl = canvas.toDataURL(outputType, isPng ? undefined : quality);
        resolve(dataUrl);
      };
      
      img.onerror = () => reject(new Error("Failed to load image"));
      reader.onerror = () => reject(new Error("Failed to read file"));
      reader.readAsDataURL(file);
    });
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
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

    try {
      const optimizedDataUrl = await resizeImage(file, 800, 800, 0.85);
      setImagePreview(optimizedDataUrl);
      setReferenceImage(optimizedDataUrl);
      
      const originalSizeKB = Math.round(file.size / 1024);
      const base64Part = optimizedDataUrl.split(",")[1] || "";
      const optimizedSizeKB = Math.round((base64Part.length * 3) / 4 / 1024);
      
      if (originalSizeKB > 100 && originalSizeKB > optimizedSizeKB * 1.3) {
        toast({
          title: "이미지 최적화됨",
          description: `${originalSizeKB}KB → ${optimizedSizeKB}KB`,
        });
      }
    } catch (error) {
      toast({
        title: "이미지 처리 실패",
        description: "이미지를 처리하는 중 오류가 발생했습니다.",
        variant: "destructive",
      });
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
            disabled={isLoading}
            data-testid="button-upload-image"
          >
            <ImagePlus className="w-4 h-4 mr-2" />
            레퍼런스 이미지
          </Button>
        </div>

        {imagePreview && (
          <div className="relative flex items-center gap-3 p-3 rounded-lg bg-accent/30" data-testid="container-image-preview">
            <img
              src={imagePreview}
              alt="레퍼런스 이미지"
              className="w-16 h-16 object-cover rounded-md border"
              data-testid="img-reference-preview"
            />
            <div className="flex-1">
              <p className="text-sm text-foreground font-medium">레퍼런스 이미지 첨부됨</p>
              <p className="text-xs text-muted-foreground">전송 시 자동 분석됩니다</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleClearImage}
              disabled={isLoading}
              data-testid="button-clear-image"
            >
              <X className="w-4 h-4" />
            </Button>
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

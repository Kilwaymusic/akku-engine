import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sparkles, Send, Loader2, ImagePlus, X, Wand2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface GenerationOptions {
  prompt: string;
  style: string;
  polyLevel: string;
  bodyType: string;
  gender: string;
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

const BODY_TYPE_OPTIONS = [
  { value: "default", label: "기본", desc: "표준 체형" },
  { value: "muscular", label: "근육질", desc: "넓은 어깨, 좁은 허리" },
  { value: "thin", label: "마른", desc: "날씬한 체형" },
  { value: "fat", label: "뚱뚱한", desc: "넓은 몸통" },
  { value: "tall", label: "키큰", desc: "긴 팔다리" },
  { value: "athletic", label: "운동선수", desc: "균형잡힌 근육" },
  { value: "heroic", label: "영웅", desc: "근육 + 키큼" },
  { value: "chibi", label: "치비", desc: "큰 머리, 작은 몸" },
];

const GENDER_OPTIONS = [
  { value: "male", label: "남성" },
  { value: "female", label: "여성" },
];

const EXAMPLE_PROMPTS = [
  "로우폴리 기사 캐릭터, 은색 갑옷, 검을 들고 있음",
  "귀여운 고양이 휴머노이드, 분홍색 귀, 큰 눈, 꼬리 있음",
  "SF 로봇 전사, 메탈릭 블루, 각진 어깨, 바이저 헬멧",
  "판타지 마법사 엘프, 뾰족한 귀, 보라색 로브, 지팡이",
];

export function PromptInput({ onSubmit, isLoading }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("stylized");
  const [polyLevel, setPolyLevel] = useState("medium");
  const [bodyType, setBodyType] = useState("default");
  const [gender, setGender] = useState("male");
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
        const opts = data.generationOptions;
        setPrompt(opts.prompt);
        setStyle(opts.style);
        setBodyType(opts.bodyType);
        setGender(opts.gender);
        toast({
          title: "이미지 분석 완료",
          description: `${data.attributes.archetype} 캐릭터로 인식되었습니다.`,
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
    if (prompt.trim() && !isLoading) {
      onSubmit({ prompt: prompt.trim(), style, polyLevel, bodyType, gender });
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
                이미지를 분석하여 캐릭터 속성을 자동으로 추출합니다.
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

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
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
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">체형</label>
            <Select value={bodyType} onValueChange={setBodyType} disabled={isLoading}>
              <SelectTrigger data-testid="select-body-type" className="w-full">
                <SelectValue placeholder="체형 선택" />
              </SelectTrigger>
              <SelectContent>
                {BODY_TYPE_OPTIONS.map((opt) => (
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
            <label className="text-xs text-muted-foreground">성별</label>
            <Select value={gender} onValueChange={setGender} disabled={isLoading}>
              <SelectTrigger data-testid="select-gender" className="w-full">
                <SelectValue placeholder="성별 선택" />
              </SelectTrigger>
              <SelectContent>
                {GENDER_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    <span className="font-medium">{opt.label}</span>
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

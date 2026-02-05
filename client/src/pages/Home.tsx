import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { BabylonViewer } from "@/components/BabylonViewer";
import { PromptInput, type GenerationOptions } from "@/components/PromptInput";
import { JobHistory } from "@/components/JobHistory";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Download, RotateCcw, Moon, Sun, Monitor } from "lucide-react";
import type { Job } from "@shared/schema";

function ViewerFallback({ modelUrl }: { modelUrl?: string | null }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-[#14141a] rounded-lg h-full min-h-[400px]">
      <div className="w-20 h-20 mb-4 rounded-full bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
        <Monitor className="w-10 h-10 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        3D 뷰어를 로드할 수 없습니다
      </h3>
      <p className="text-sm text-muted-foreground max-w-sm">
        WebGL을 지원하는 브라우저가 필요합니다.
      </p>
      {modelUrl && (
        <a
          href={modelUrl}
          download
          className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover-elevate"
        >
          모델 다운로드
        </a>
      )}
    </div>
  );
}

export default function Home() {
  const { toast } = useToast();
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  const { data: jobs = [], isLoading: isLoadingJobs } = useQuery<Job[]>({
    queryKey: ["/api/jobs"],
    refetchInterval: 3000,
  });

  const createJobMutation = useMutation({
    mutationFn: async (options: GenerationOptions) => {
      // Use the agent (code generation) endpoint for creative character generation
      const response = await apiRequest("POST", "/api/jobs/agent", {
        prompt: options.prompt,
      });
      return response.json();
    },
    onSuccess: (newJob: Job) => {
      queryClient.invalidateQueries({ queryKey: ["/api/jobs"] });
      setSelectedJob(newJob);
      toast({
        title: "생성 시작",
        description: "3D 캐릭터 생성을 시작했습니다.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "오류 발생",
        description: error.message || "생성에 실패했습니다.",
        variant: "destructive",
      });
    },
  });

  useEffect(() => {
    if (selectedJob && jobs.length > 0) {
      const updatedJob = jobs.find((j) => j.id === selectedJob.id);
      if (updatedJob && updatedJob.status !== selectedJob.status) {
        setSelectedJob(updatedJob);
        if (updatedJob.status === "completed") {
          toast({
            title: "생성 완료",
            description: "3D 캐릭터가 성공적으로 생성되었습니다!",
          });
        } else if (updatedJob.status === "failed") {
          toast({
            title: "생성 실패",
            description: updatedJob.error || "알 수 없는 오류가 발생했습니다.",
            variant: "destructive",
          });
        }
      }
    }
  }, [jobs, selectedJob, toast]);

  const handleDownload = () => {
    if (selectedJob?.modelUrl) {
      const link = document.createElement("a");
      link.href = selectedJob.modelUrl;
      link.download = `character-${selectedJob.id}.glb`;
      link.click();
    }
  };

  const isGenerating = selectedJob?.status === "pending" || selectedJob?.status === "processing";

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center">
              <svg
                className="w-6 h-6 text-primary-foreground"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">Akku Engine</h1>
              <p className="text-xs text-muted-foreground">AI 3D Character Generator</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setIsDark(!isDark)}
              data-testid="button-theme-toggle"
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="relative aspect-[4/3] lg:aspect-[16/10] rounded-xl overflow-hidden border border-border">
              <ErrorBoundary fallback={<ViewerFallback modelUrl={selectedJob?.modelUrl} />}>
                <BabylonViewer
                  modelUrl={selectedJob?.modelUrl || null}
                  isLoading={isGenerating}
                />
              </ErrorBoundary>
              
              {selectedJob?.status === "completed" && selectedJob.modelUrl && (
                <div className="absolute bottom-4 right-4 flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setSelectedJob(null)}
                    data-testid="button-reset-view"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    초기화
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleDownload}
                    data-testid="button-download"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    다운로드
                  </Button>
                </div>
              )}
            </div>

            <PromptInput
              onSubmit={(options) => createJobMutation.mutate(options)}
              isLoading={createJobMutation.isPending || isGenerating}
            />
          </div>

          <div className="lg:col-span-1">
            <JobHistory
              jobs={jobs}
              selectedJobId={selectedJob?.id || null}
              onSelectJob={setSelectedJob}
            />
          </div>
        </div>
      </main>

      <footer className="border-t border-border mt-auto">
        <div className="container mx-auto px-4 py-4 text-center text-xs text-muted-foreground">
          <p>Powered by Blender + Babylon.js</p>
        </div>
      </footer>
    </div>
  );
}

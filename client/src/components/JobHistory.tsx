import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Clock, CheckCircle2, XCircle, Loader2, Eye } from "lucide-react";
import type { Job } from "@shared/schema";
import { formatDistanceToNow } from "date-fns";
import { ko } from "date-fns/locale";

interface JobHistoryProps {
  jobs: Job[];
  selectedJobId: string | null;
  onSelectJob: (job: Job) => void;
}

const statusConfig = {
  pending: {
    label: "대기 중",
    icon: Clock,
    variant: "secondary" as const,
  },
  processing: {
    label: "생성 중",
    icon: Loader2,
    variant: "default" as const,
  },
  completed: {
    label: "완료",
    icon: CheckCircle2,
    variant: "default" as const,
  },
  failed: {
    label: "실패",
    icon: XCircle,
    variant: "destructive" as const,
  },
};

export function JobHistory({ jobs, selectedJobId, onSelectJob }: JobHistoryProps) {
  if (jobs.length === 0) {
    return (
      <Card className="border-card-border h-full">
        <CardHeader className="pb-3">
          <h3 className="font-semibold text-foreground">생성 기록</h3>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-3">
              <Clock className="w-8 h-8 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">
              아직 생성된 캐릭터가 없습니다
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-card-border h-full">
      <CardHeader className="pb-3">
        <h3 className="font-semibold text-foreground">생성 기록</h3>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[calc(100vh-400px)] min-h-[200px]">
          <div className="px-4 pb-4 space-y-2">
            {jobs.map((job) => {
              const config = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.pending;
              const Icon = config.icon;
              const isSelected = job.id === selectedJobId;

              return (
                <button
                  key={job.id}
                  onClick={() => onSelectJob(job)}
                  className={`w-full p-3 rounded-lg text-left transition-colors hover-elevate ${
                    isSelected
                      ? "bg-accent border border-accent-border"
                      : "bg-card border border-transparent"
                  }`}
                  data-testid={`job-item-${job.id}`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <Badge variant={config.variant} className="text-xs shrink-0">
                      <Icon className={`w-3 h-3 mr-1 ${job.status === "processing" ? "animate-spin" : ""}`} />
                      {config.label}
                    </Badge>
                    {job.status === "completed" && job.modelUrl && (
                      <Eye className="w-4 h-4 text-muted-foreground shrink-0" />
                    )}
                  </div>
                  <p className="text-sm text-foreground line-clamp-2 mb-1">
                    {job.prompt}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(job.createdAt), {
                      addSuffix: true,
                      locale: ko,
                    })}
                  </p>
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

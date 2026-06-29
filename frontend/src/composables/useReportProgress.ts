import { ref } from "vue";

export type ProgressStepStatus = "pending" | "active" | "complete";

export interface ProgressStep {
  key: string;
  label: string;
  status: ProgressStepStatus;
}

const initialSteps: ProgressStep[] = [
  { key: "search", label: "匹配基金代码", status: "pending" },
  { key: "collect", label: "采集真实数据", status: "pending" },
  { key: "report", label: "计算指标并生成报告", status: "pending" },
  { key: "charts", label: "加载图表数据", status: "pending" },
  { key: "done", label: "完成体检", status: "pending" }
];

export function useReportProgress() {
  const progressValue = ref(0);
  const progressMessage = ref("");
  const progressSteps = ref<ProgressStep[]>(cloneInitialSteps());
  let progressTimer: ReturnType<typeof setInterval> | null = null;

  function resetProgress() {
    progressValue.value = 0;
    progressMessage.value = "";
    progressSteps.value = cloneInitialSteps();
  }

  function setProgress(key: string, status: ProgressStepStatus, value: number, message: string) {
    progressSteps.value = progressSteps.value.map((step) => {
      if (step.key === key) return { ...step, status };
      return step;
    });
    progressValue.value = Math.max(progressValue.value, value);
    progressMessage.value = message;
  }

  function startProgressPulse(target: number) {
    stopProgressPulse();
    progressTimer = window.setInterval(() => {
      if (progressValue.value < target) {
        progressValue.value += progressValue.value < 55 ? 2 : 0.6;
      }
    }, 650);
  }

  function stopProgressPulse() {
    if (progressTimer) {
      window.clearInterval(progressTimer);
      progressTimer = null;
    }
  }

  function setProgressMessage(message: string) {
    progressMessage.value = message;
  }

  return {
    progressValue,
    progressMessage,
    progressSteps,
    resetProgress,
    setProgress,
    setProgressMessage,
    startProgressPulse,
    stopProgressPulse
  };
}

function cloneInitialSteps() {
  return initialSteps.map((step) => ({ ...step }));
}

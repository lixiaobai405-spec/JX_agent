import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sparkles, CheckCircle2, RefreshCw } from 'lucide-react'
import { useCurrentUser, useCurrentPeriod, useCurrentGoal } from '@/hooks'
import { planApi } from '@/api/do'
import { normalizeAgreementTerm } from '@/lib/copy'
import type { JobAnalysis, PerformanceContract } from '@/types'

const PROTOTYPE_NAMES: Record<string, string> = {
  S: 'S类 · 铁军销售型',
  P: 'P类 · 项目攻坚型',
  O: 'O类 · 运营效能型',
  F: 'F类 · 职能支撑型',
  M: 'M类 · 管理统筹型',
}

type ContractIndicator = {
  name: string
  weight: number
  is_redline?: boolean
  target?: number
  type?: 'positive' | 'negative' | 'qualitative' | 'redline'
  unit?: string
  target_display?: string
  target_logic?: string
  scoring_rule?: string
}

const INDICATOR_TYPE_LABELS: Record<string, string> = {
  positive: '定量 · 正向',
  negative: '定量 · 反向',
  qualitative: '定性',
  redline: '红线',
}

function indicatorTargetText(indicator: ContractIndicator): string | null {
  if (indicator.target_display) return indicator.target_display
  if (indicator.target == null) return null
  return `${indicator.target}${indicator.unit ?? ''}`
}

function ContractIndicatorRow({ indicator }: { indicator: ContractIndicator }) {
  const targetText = indicatorTargetText(indicator)

  return (
    <div className="flex items-start justify-between gap-3 py-2.5 text-sm">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{normalizeAgreementTerm(indicator.name)}</span>
          {indicator.type && (
            <Badge variant="outline" className="text-xs">
              {INDICATOR_TYPE_LABELS[indicator.type] ?? indicator.type}
            </Badge>
          )}
        </div>
        <div className="flex flex-col gap-0.5 text-xs text-muted-foreground">
          {targetText && <span>目标值：{targetText}</span>}
          {indicator.target_logic && <span>目标依据：{indicator.target_logic}</span>}
          {indicator.scoring_rule && <span>评分标准：{indicator.scoring_rule}</span>}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {!indicator.is_redline && <Badge variant="secondary">{Math.round(indicator.weight)}%</Badge>}
        {indicator.is_redline && <Badge variant="destructive">一票否决</Badge>}
      </div>
    </div>
  )
}

function JobAnalysisStep({ onDone }: { onDone: (a: JobAnalysis) => void }) {
  const { data: user } = useCurrentUser()
  const [jd, setJd] = useState('')
  const { mutate, isPending } = useMutation({
    mutationFn: () => planApi.analyzeJob(user!.id, jd),
    onSuccess: (data) => { toast.success('岗位分析完成'); onDone(data) },
  })
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label>岗位描述（JD）</Label>
        <Textarea rows={8} placeholder="粘贴岗位职责，AI 自动识别岗位类型..." value={jd} onChange={(e) => setJd(e.target.value)} />
      </div>
      <Button onClick={() => mutate()} disabled={isPending || !jd.trim() || !user} className="self-start">
        {isPending ? <><RefreshCw data-icon="inline-start" className="animate-spin" />分析中...</> : <><Sparkles data-icon="inline-start" />开始分析</>}
      </Button>
    </div>
  )
}

function AnalysisResult({ analysis }: { analysis: JobAnalysis }) {
  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <CheckCircle2 className="size-4 text-primary" />
          分析完成
        </CardTitle>
        <CardDescription>AI 置信度：{analysis.confidence != null ? `${Math.round(analysis.confidence * 100)}%` : '—'}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">岗位类型</span>
          <Badge>{PROTOTYPE_NAMES[analysis.job_prototype_code ?? ''] ?? analysis.job_prototype_code ?? '—'}</Badge>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: '可量化性', value: analysis.quantifiability_score },
            { label: '产出周期性', value: analysis.output_cycle_score },
            { label: '工作性质', value: analysis.work_nature_score },
          ].map(({ label, value }) => (
            <div key={label} className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">{label}</span>
              <Progress value={(value ?? 0) * 10} />
              <span className="text-xs text-right">{value ?? '—'}/10</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function GenerateContractStep({ analysis, periodId, onDone }: {
  analysis: JobAnalysis; periodId: string; onDone: (c: PerformanceContract) => void
}) {
  const { data: user } = useCurrentUser()
  const [contract, setContract] = useState<PerformanceContract | null>(null)
  const { mutate, isPending } = useMutation({
    mutationFn: () => planApi.generateContract({ period_id: periodId, user_id: user!.id, job_analysis_id: analysis.id }),
    onSuccess: (data) => { toast.success('合约生成完成'); setContract(data) },
  })

  const indicators = (contract?.contract_data as { indicators?: ContractIndicator[] } | undefined)?.indicators ?? []

  return (
    <div className="flex flex-col gap-4">
      {contract && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">生成的指标（{indicators.length} 条）</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-col divide-y">
              {indicators.map((ind, i) => (
                <ContractIndicatorRow key={i} indicator={ind} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      <div className="flex items-center gap-2">
        <Button onClick={() => mutate()} disabled={isPending} variant={contract ? 'outline' : 'default'}>
          {isPending ? <><RefreshCw data-icon="inline-start" className="animate-spin" />生成中...</> : contract ? <><RefreshCw data-icon="inline-start" />重新生成</> : <><Sparkles data-icon="inline-start" />AI 生成合约</>}
        </Button>
        {contract && (
          <Button onClick={() => onDone(contract)}>
            <CheckCircle2 data-icon="inline-start" />
            下一步：确认合约
          </Button>
        )}
      </div>
    </div>
  )
}

function ConfirmContractStep({ contract, onConfirmed }: { contract: PerformanceContract; onConfirmed: () => void }) {
  const { data: user } = useCurrentUser()
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const { mutate, isPending } = useMutation({
    mutationFn: () => planApi.confirmContract(contract.id, user!.id),
    onSuccess: () => {
      toast.success('合约已生效，目标正式创建')
      qc.invalidateQueries({ queryKey: ['goal', (contract.contract_data as { period_id?: string }).period_id] })
      qc.invalidateQueries({ queryKey: ['periods', 'current'] })
      setOpen(false); onConfirmed()
    },
  })

  const indicators = (contract.contract_data as { indicators?: ContractIndicator[] }).indicators ?? []

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">合约指标总览（{PROTOTYPE_NAMES[contract.job_prototype_code] ?? contract.job_prototype_code}）</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col divide-y">
            {indicators.map((ind, i) => (
              <ContractIndicatorRow key={i} indicator={ind} />
            ))}
          </div>
        </CardContent>
      </Card>
      <Button className="self-start" onClick={() => setOpen(true)}>
        <CheckCircle2 data-icon="inline-start" />
        确认合约
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>确认绩效合约</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground py-2">确认后合约正式生效，将自动创建目标和指标，无法撤销。</p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
            <Button onClick={() => mutate()} disabled={isPending}>
              {isPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
              确认生效
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className={`flex size-6 items-center justify-center rounded-full text-xs font-medium transition-colors ${i < current ? 'bg-primary text-primary-foreground' : i === current ? 'border-2 border-primary text-primary' : 'border border-muted-foreground/30 text-muted-foreground'}`}>
            {i < current ? <CheckCircle2 className="size-3.5" /> : i + 1}
          </div>
          {i < total - 1 && <div className={`h-px w-8 ${i < current ? 'bg-primary' : 'bg-border'}`} />}
        </div>
      ))}
    </div>
  )
}

const STEP_LABELS = ['岗位分析', '生成合约', '确认合约']

export function PlanPage() {
  const [step, setStep] = useState(0)
  const [analysis, setAnalysis] = useState<JobAnalysis | null>(null)
  const [contract, setContract] = useState<PerformanceContract | null>(null)
  const { data: period } = useCurrentPeriod()
  const { data: existingGoal } = useCurrentGoal(period?.id)

  const isDone = !!existingGoal || !!contract?.confirmed_at

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">P - 目标设定</h1>
        <p className="text-sm text-muted-foreground mt-1">通过 AI 分析岗位职责，生成个性化绩效合约</p>
      </div>
      {!period ? (
        <Card><CardContent className="py-10 text-center text-muted-foreground">暂无考核期，请联系经理创建</CardContent></Card>
      ) : isDone ? (
        <Card>
          <CardContent className="flex items-center gap-3 py-6">
            <CheckCircle2 className="size-5 text-primary" />
            <div>
              <p className="font-medium">绩效合约已生效</p>
              <p className="text-sm text-muted-foreground">请前往「D - 执行追踪」开始打卡记录</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex items-center gap-4">
            <StepIndicator current={step} total={3} />
            <div className="flex gap-1">
              {STEP_LABELS.map((label, i) => (
                <span key={i} className={`text-sm ${i === step ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                  {i > 0 && <span className="mx-1 text-muted-foreground">/</span>}
                  {label}
                </span>
              ))}
            </div>
          </div>
          <Separator />
          {step === 0 && (
            <div className="flex flex-col gap-4">
              <JobAnalysisStep onDone={(a) => { setAnalysis(a); setStep(1) }} />
              {analysis && <AnalysisResult analysis={analysis} />}
            </div>
          )}
          {step === 1 && analysis && (
            <div className="flex flex-col gap-4">
              <AnalysisResult analysis={analysis} />
              <Separator />
              <GenerateContractStep analysis={analysis} periodId={period.id} onDone={(c) => { setContract(c); setStep(2) }} />
            </div>
          )}
          {step === 2 && contract && (
            <ConfirmContractStep contract={contract} onConfirmed={() => setStep(3)} />
          )}
          {step > 0 && (
            <Button variant="ghost" size="sm" className="self-start" onClick={() => setStep((s) => s - 1)}>← 返回上一步</Button>
          )}
        </>
      )}
    </div>
  )
}

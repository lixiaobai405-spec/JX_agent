import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi } from '@/api/auth'
import { periodsApi, doApi } from '@/api/do'
import { checkApi } from '@/api/check'
import { usersApi } from '@/api/users'
import { actionApi } from '@/api/action'
import { authStorage } from '@/lib/authStorage'

const C_PHASE_SYNC_INTERVAL_MS = 5000

// Auth
export const useCurrentUser = () =>
  useQuery({ queryKey: ['me'], queryFn: authApi.me, staleTime: 5 * 60 * 1000 })

export const useSessions = () =>
  useQuery({ queryKey: ['sessions'], queryFn: authApi.sessions })

// Periods
export const usePeriods = () =>
  useQuery({ queryKey: ['periods'], queryFn: periodsApi.list })

export const useCurrentPeriod = () =>
  useQuery({
    queryKey: ['periods', 'current'],
    queryFn: periodsApi.current,
    retry: false,
  })

export const useTeamOpenPeriods = () =>
  useQuery({ queryKey: ['periods', 'open'], queryFn: () => periodsApi.listByStatus('open') })

// Goals & Indicators
export const useCurrentGoal = (period_id?: string) =>
  useQuery({
    queryKey: ['goal', period_id],
    queryFn: () => doApi.currentGoal(period_id!),
    enabled: !!period_id,
  })

export const useMemberGoal = (period_id?: string, user_id?: string) =>
  useQuery({
    queryKey: ['goal', 'member', user_id, period_id],
    queryFn: () => doApi.currentGoal(period_id!, user_id),
    enabled: !!period_id && !!user_id,
    retry: false,
  })

export const useIndicators = (goal_id?: string) =>
  useQuery({
    queryKey: ['indicators', goal_id],
    queryFn: () => doApi.indicators(goal_id!),
    enabled: !!goal_id,
  })

// D Phase
export const useLatestDiagnostic = (goal_id?: string) =>
  useQuery({
    queryKey: ['diagnostic', goal_id],
    queryFn: () => doApi.latestDiagnostic(goal_id!),
    enabled: !!goal_id,
    retry: false,
  })

export const useIndicatorCheckins = (indicator_id?: string) =>
  useQuery({
    queryKey: ['checkins', indicator_id],
    queryFn: () => doApi.indicatorCheckins(indicator_id!),
    enabled: !!indicator_id,
  })

export const useMyCoachingRequests = () =>
  useQuery({
    queryKey: ['coaching', 'my'],
    queryFn: doApi.myCoachingRequests,
    refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
    refetchIntervalInBackground: false,
  })

export const useTeamCoachingRequests = () =>
  useQuery({
    queryKey: ['coaching', 'team'],
    queryFn: doApi.teamCoachingRequests,
    refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
    refetchIntervalInBackground: false,
  })

// C Phase
export const useSelfAssessment = (goal_id?: string) =>
  useQuery({
    queryKey: ['self-assessment', goal_id],
    queryFn: () => checkApi.getSelfAssessment(goal_id!),
    enabled: !!goal_id,
    retry: false,
    refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
    refetchIntervalInBackground: false,
  })

export const useEvaluationTasks = () =>
  useQuery({ queryKey: ['eval-tasks'], queryFn: () => checkApi.listEvaluationTasks() })

export const usePendingEvaluationTasks = () =>
  useQuery({
    queryKey: ['eval-tasks', 'pending'],
    queryFn: checkApi.pendingEvaluationTasks,
    refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
    refetchIntervalInBackground: false,
  })

export const useGoalEvaluations = (goal_id?: string) =>
  useQuery({
    queryKey: ['evaluations', goal_id],
    queryFn: () => checkApi.getGoalEvaluations(goal_id!),
    enabled: !!goal_id,
    refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
    refetchIntervalInBackground: false,
  })

export const useFinalResult = (goal_id?: string) =>
  useQuery({
    queryKey: ['final-result', goal_id],
    queryFn: () => checkApi.getFinalResult(goal_id!),
    enabled: !!goal_id,
    retry: false,
    refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
    refetchIntervalInBackground: false,
  })

// A Phase
export const useMyPlans = () =>
  useQuery({ queryKey: ['my-plans'], queryFn: actionApi.myPlans })

export const useTeamPlans = () =>
  useQuery({ queryKey: ['team-plans'], queryFn: actionApi.teamPlans })

export const useReviewReportByUser = (user_id?: string, period_id?: string) =>
  useQuery({
    queryKey: ['review-report-user', user_id, period_id],
    queryFn: () => actionApi.getReviewReportByUser(user_id!, period_id!),
    enabled: !!user_id && !!period_id,
    retry: false,
  })

export const useInheritanceSuggestions = (user_id?: string, period_id?: string) =>
  useQuery({
    queryKey: ['inheritance-suggestions', user_id, period_id],
    queryFn: () => actionApi.getInheritanceSuggestions(user_id!, period_id!),
    enabled: !!user_id && !!period_id,
  })

// Users
export const useSubordinates = (userId?: string) =>
  useQuery({
    queryKey: ['subordinates', userId],
    queryFn: () => usersApi.subordinates(userId!),
    enabled: !!userId,
  })

export const useTeam = () =>
  useQuery({ queryKey: ['team'], queryFn: usersApi.myTeam })

export const useAllUsers = (params?: { role?: string }) =>
  useQuery({ queryKey: ['users', params], queryFn: () => usersApi.list(params) })

// Mutations
export const useLogout = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      authStorage.clearTokens()
      qc.clear()
      window.location.href = '/login'
    },
  })
}

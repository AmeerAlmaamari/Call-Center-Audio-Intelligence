import { useQuery } from "@tanstack/react-query"
import {
  TrendingUp,
  TrendingDown,
  Target,
  AlertTriangle,
  CheckCircle,
  BarChart3,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { dashboardApi } from "@/lib/api"
import { getScoreColor } from "@/lib/utils"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"

export default function Insights() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: dashboardApi.getOverview,
  })

  const { data: agentPerformance } = useQuery({
    queryKey: ["dashboard", "agents"],
    queryFn: dashboardApi.getAgentPerformance,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const agentChartData = agentPerformance?.map((agent) => ({
    name: agent.agent_name.split(" ")[0],
    performance: agent.avg_performance_score || 0,
    conversion: agent.avg_conversion_likelihood || 0,
    calls: agent.total_calls,
  })) || []

  const topPerformers = [...(agentPerformance || [])]
    .sort((a, b) => (b.avg_performance_score || 0) - (a.avg_performance_score || 0))
    .slice(0, 3)

  const needsImprovement = [...(agentPerformance || [])]
    .filter((a) => (a.avg_performance_score || 0) < 70)
    .slice(0, 3)

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Overall Performance</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getScoreColor(overview?.avg_performance_score)}`}>
              {overview?.avg_performance_score?.toFixed(1) || "N/A"}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Average across all analyzed calls
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getScoreColor(overview?.avg_conversion_likelihood)}`}>
              {overview?.avg_conversion_likelihood?.toFixed(1) || "N/A"}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Average conversion likelihood
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Analyzed</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {overview?.analyzed_calls || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Out of {overview?.total_calls || 0} total calls
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Agent Performance Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Performance Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={agentChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="performance" name="Performance %" fill="#3b82f6" />
                <Bar dataKey="conversion" name="Conversion %" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Top Performers & Needs Improvement */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-600">
              <TrendingUp className="h-5 w-5" />
              Top Performers
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topPerformers.length === 0 ? (
              <p className="text-muted-foreground">No data available</p>
            ) : (
              <div className="space-y-4">
                {topPerformers.map((agent, i) => (
                  <div key={agent.agent_id} className="flex items-center gap-4">
                    <div className="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center text-green-600 font-bold">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{agent.agent_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {agent.total_calls} calls
                      </p>
                    </div>
                    <div className={`text-lg font-bold ${getScoreColor(agent.avg_performance_score)}`}>
                      {agent.avg_performance_score?.toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-600">
              <AlertTriangle className="h-5 w-5" />
              Needs Improvement
            </CardTitle>
          </CardHeader>
          <CardContent>
            {needsImprovement.length === 0 ? (
              <p className="text-muted-foreground">All agents performing well!</p>
            ) : (
              <div className="space-y-4">
                {needsImprovement.map((agent) => (
                  <div key={agent.agent_id} className="flex items-center gap-4">
                    <div className="h-8 w-8 rounded-full bg-orange-100 flex items-center justify-center">
                      <TrendingDown className="h-4 w-4 text-orange-600" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{agent.agent_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {agent.total_calls} calls
                      </p>
                    </div>
                    <div className={`text-lg font-bold ${getScoreColor(agent.avg_performance_score)}`}>
                      {agent.avg_performance_score?.toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

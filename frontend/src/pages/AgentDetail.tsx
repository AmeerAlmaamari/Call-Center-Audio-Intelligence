import { useParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Users, Mail, Building, Phone } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { agentsApi, callsApi } from "@/lib/api"
import { formatDate, getStatusColor, getScoreColor } from "@/lib/utils"

export default function AgentDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: agent, isLoading } = useQuery({
    queryKey: ["agent", id],
    queryFn: () => agentsApi.get(id!),
    enabled: !!id,
  })

  const { data: performance } = useQuery({
    queryKey: ["agent", id, "performance"],
    queryFn: () => agentsApi.getPerformance(id!),
    enabled: !!id,
  })

  const { data: calls } = useQuery({
    queryKey: ["calls", "agent", id],
    queryFn: () => callsApi.list({ agent_id: id }),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="text-center py-12">
        <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium">Agent not found</h3>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Agent Header */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Users className="h-8 w-8 text-primary" />
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-bold">{agent.name}</h1>
              <div className="flex flex-wrap gap-4 mt-2 text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Mail className="h-4 w-4" />
                  {agent.email}
                </span>
                {agent.department && (
                  <span className="flex items-center gap-1">
                    <Building className="h-4 w-4" />
                    {agent.department}
                  </span>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Calls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.total_calls || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Avg Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getScoreColor(performance?.avg_performance_score)}`}>
              {performance?.avg_performance_score?.toFixed(0) || "N/A"}%
            </div>
            <Progress value={performance?.avg_performance_score || 0} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getScoreColor(performance?.avg_conversion_likelihood)}`}>
              {performance?.avg_conversion_likelihood?.toFixed(0) || "N/A"}%
            </div>
            <Progress value={performance?.avg_conversion_likelihood || 0} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Successful Sales</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {performance?.successful_sales || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Calls */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Calls</CardTitle>
        </CardHeader>
        <CardContent>
          {calls?.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No calls found for this agent.
            </p>
          ) : (
            <div className="space-y-3">
              {calls?.slice(0, 10).map((call) => (
                <Link
                  key={call.id}
                  to={`/calls/${call.id}`}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{call.filename}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatDate(call.created_at)}
                      </p>
                    </div>
                  </div>
                  <Badge className={getStatusColor(call.status)}>{call.status}</Badge>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

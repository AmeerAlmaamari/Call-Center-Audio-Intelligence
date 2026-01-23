import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import {
  FileText,
  BarChart3,
  CheckSquare,
  AlertTriangle,
  TrendingUp,
  Target,
  Clock,
  Loader2,
  Zap,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { callsApi } from "@/lib/api"
import { formatDate, formatDuration, getStatusColor, getScoreColor } from "@/lib/utils"

export default function CallDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const { data: call, isLoading } = useQuery({
    queryKey: ["call", id],
    queryFn: () => callsApi.get(id!),
    enabled: !!id,
  })

  const { data: transcript } = useQuery({
    queryKey: ["transcript", id],
    queryFn: () => callsApi.getTranscript(id!),
    enabled: !!id && (call?.status === "transcribed" || call?.status === "analyzed"),
  })

  const { data: analysis } = useQuery({
    queryKey: ["analysis", id],
    queryFn: () => callsApi.getAnalysis(id!),
    enabled: !!id && call?.status === "analyzed",
  })

  const { data: actionItems } = useQuery({
    queryKey: ["actionItems", id],
    queryFn: () => callsApi.getActionItems(id!),
    enabled: !!id && call?.status === "analyzed",
  })

  const transcribeMutation = useMutation({
    mutationFn: () => callsApi.transcribe(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["call", id] })
    },
  })

  const analyzeMutation = useMutation({
    mutationFn: () => callsApi.analyze(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["call", id] })
      queryClient.invalidateQueries({ queryKey: ["analysis", id] })
      queryClient.invalidateQueries({ queryKey: ["actionItems", id] })
    },
  })

  const processMutation = useMutation({
    mutationFn: () => callsApi.process(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["call", id] })
    },
  })

  const { data: processingStatus } = useQuery({
    queryKey: ["callStatus", id],
    queryFn: () => callsApi.getStatus(id!),
    enabled: !!id && (call?.status === "transcribing" || call?.status === "analyzing"),
    refetchInterval: 2000,
  })

  useEffect(() => {
    if (processingStatus?.is_complete || processingStatus?.is_failed) {
      queryClient.invalidateQueries({ queryKey: ["call", id] })
      queryClient.invalidateQueries({ queryKey: ["transcript", id] })
      queryClient.invalidateQueries({ queryKey: ["analysis", id] })
      queryClient.invalidateQueries({ queryKey: ["actionItems", id] })
    }
  }, [processingStatus, queryClient, id])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!call) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium">Call not found</h3>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{call.filename}</h1>
          <div className="flex items-center gap-4 mt-2 text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              {formatDuration(call.duration_seconds)}
            </span>
            <span>{formatDate(call.created_at)}</span>
            {call.agent && (
              <span className="font-medium text-primary">
                Agent: {call.agent.name}
              </span>
            )}
            <Badge className={getStatusColor(call.status)}>{call.status}</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          {call.status === "pending" && (
            <>
              <Button
                onClick={() => processMutation.mutate()}
                disabled={processMutation.isPending}
                className="bg-green-600 hover:bg-green-700"
              >
                <Zap className="h-4 w-4 mr-2" />
                {processMutation.isPending ? "Starting..." : "Process All"}
              </Button>
              <Button
                onClick={() => transcribeMutation.mutate()}
                disabled={transcribeMutation.isPending}
                variant="outline"
              >
                <FileText className="h-4 w-4 mr-2" />
                {transcribeMutation.isPending ? "Transcribing..." : "Transcribe Only"}
              </Button>
            </>
          )}
          {(call.status === "transcribing" || call.status === "analyzing") && (
            <Button disabled className="bg-blue-600">
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              {call.status === "transcribing" ? "Transcribing..." : "Analyzing..."}
            </Button>
          )}
          {(call.status === "transcribed" || call.status === "failed") && (
            <Button
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isPending}
            >
              <BarChart3 className="h-4 w-4 mr-2" />
              {analyzeMutation.isPending ? "Analyzing..." : "Analyze"}
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="transcript" disabled={!transcript}>
            Transcript
          </TabsTrigger>
          <TabsTrigger value="analysis" disabled={!analysis}>
            Analysis
          </TabsTrigger>
          <TabsTrigger value="actions" disabled={!actionItems?.length}>
            Actions ({actionItems?.length || 0})
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Performance Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${getScoreColor(analysis?.performance_score)}`}>
                  {analysis?.performance_score?.toFixed(0) || "N/A"}%
                </div>
                <Progress value={analysis?.performance_score || 0} className="mt-2" />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Conversion Likelihood</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${getScoreColor(analysis?.conversion_likelihood)}`}>
                  {analysis?.conversion_likelihood?.toFixed(0) || "N/A"}%
                </div>
                <Progress value={analysis?.conversion_likelihood || 0} className="mt-2" />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Call Reason</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-lg font-semibold">
                  {analysis?.call_reason?.replace(/_/g, " ") || "N/A"}
                </div>
                <p className="text-sm text-muted-foreground">
                  {analysis?.call_reason_confidence?.toFixed(0)}% confidence
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Outcome</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-lg font-semibold">
                  {analysis?.call_outcome?.replace(/_/g, " ") || "N/A"}
                </div>
                <p className="text-sm text-muted-foreground">
                  {analysis?.call_outcome_confidence?.toFixed(0)}% confidence
                </p>
              </CardContent>
            </Card>
          </div>

          {analysis?.performance_explanation && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle>Performance Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">{analysis.performance_explanation}</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Transcript Tab */}
        <TabsContent value="transcript">
          <Card>
            <CardHeader>
              <CardTitle>Call Transcript</CardTitle>
            </CardHeader>
            <CardContent>
              {transcript?.segments?.length ? (
                <div className="space-y-4">
                  {transcript.segments.map((segment, index) => (
                    <div key={index} className="flex gap-4">
                      <div className="text-sm text-muted-foreground w-16 flex-shrink-0">
                        {formatDuration(segment.start)}
                      </div>
                      <div className="flex-1">
                        {segment.speaker && (
                          <span className="font-medium text-primary mr-2">
                            {segment.speaker}:
                          </span>
                        )}
                        <span>{segment.text}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{transcript?.raw_text}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analysis Tab */}
        <TabsContent value="analysis">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Buying Signals */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Buying Signals
                </CardTitle>
              </CardHeader>
              <CardContent>
                {analysis?.buying_signals_detected?.length ? (
                  <ul className="space-y-2">
                    {analysis.buying_signals_detected.map((signal, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <TrendingUp className="h-4 w-4 text-green-500 mt-1 flex-shrink-0" />
                        <span className="text-sm">{signal}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">No buying signals detected</p>
                )}
              </CardContent>
            </Card>

            {/* Objections */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Objections Detected
                </CardTitle>
              </CardHeader>
              <CardContent>
                {analysis?.objections_detected?.length ? (
                  <div className="space-y-4">
                    {analysis.objections_detected.map((obj, i) => (
                      <div key={i} className="border-l-2 border-yellow-500 pl-3">
                        <p className="font-medium text-sm">{obj.type}</p>
                        <p className="text-sm text-muted-foreground italic">"{obj.quote}"</p>
                        <p className="text-sm mt-1">
                          <span className="font-medium">Response:</span> {obj.agent_response}
                        </p>
                        <Badge className="mt-1" variant="outline">
                          Score: {obj.handling_score}%
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No objections detected</p>
                )}
              </CardContent>
            </Card>

            {/* Missed Opportunities */}
            {analysis?.missed_opportunities?.length ? (
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-orange-600">
                    <AlertTriangle className="h-5 w-5" />
                    Missed Opportunities
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {analysis.missed_opportunities.map((opp, i) => (
                      <div key={i} className="p-3 bg-orange-50 rounded-lg">
                        <p className="text-sm">{opp.description}</p>
                        {opp.customer_signal && (
                          <p className="text-sm text-muted-foreground mt-1">
                            <span className="font-medium">Signal:</span> {opp.customer_signal}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : null}
          </div>
        </TabsContent>

        {/* Actions Tab */}
        <TabsContent value="actions">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckSquare className="h-5 w-5" />
                Action Items
              </CardTitle>
            </CardHeader>
            <CardContent>
              {actionItems?.length ? (
                <div className="space-y-3">
                  {actionItems.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-start gap-3 p-3 border rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{item.category}</Badge>
                          <Badge
                            className={
                              item.priority === "high"
                                ? "bg-red-100 text-red-800"
                                : item.priority === "medium"
                                ? "bg-yellow-100 text-yellow-800"
                                : "bg-green-100 text-green-800"
                            }
                          >
                            {item.priority}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm">{item.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No action items</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

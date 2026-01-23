import { useState, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Upload, Phone, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { callsApi, agentsApi, Call } from "@/lib/api"
import { formatDate, formatDuration, getStatusColor } from "@/lib/utils"

export default function Calls() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [agentFilter, setAgentFilter] = useState<string>("")
  const [selectedAgentForUpload, setSelectedAgentForUpload] = useState<string>("")

  const { data: calls, isLoading } = useQuery({
    queryKey: ["calls", statusFilter, agentFilter],
    queryFn: () =>
      callsApi.list({
        status: statusFilter || undefined,
        agent_id: agentFilter || undefined,
      }),
  })

  const { data: agents } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => callsApi.upload(file, selectedAgentForUpload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calls"] })
      setSelectedAgentForUpload("")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => callsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calls"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })

  const handleDelete = (call: Call) => {
    if (confirm(`Are you sure you want to delete "${call.filename}"? This action cannot be undone.`)) {
      deleteMutation.mutate(call.id)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && selectedAgentForUpload) {
      uploadMutation.mutate(file)
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleUploadClick = () => {
    if (!selectedAgentForUpload) {
      alert("Please select an agent before uploading a call.")
      return
    }
    fileInputRef.current?.click()
  }

  return (
    <div className="space-y-6">
      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between">
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="transcribing">Transcribing</option>
            <option value="transcribed">Transcribed</option>
            <option value="analyzing">Analyzing</option>
            <option value="analyzed">Analyzed</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm"
          >
            <option value="">All Agents</option>
            {agents?.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-2 items-center">
          <select
            value={selectedAgentForUpload}
            onChange={(e) => setSelectedAgentForUpload(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm"
          >
            <option value="">Select Agent for Upload</option>
            {agents?.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="audio/*"
            className="hidden"
          />
          <Button
            onClick={handleUploadClick}
            disabled={uploadMutation.isPending || !selectedAgentForUpload}
          >
            <Upload className="h-4 w-4 mr-2" />
            {uploadMutation.isPending ? "Uploading..." : "Upload Call"}
          </Button>
        </div>
      </div>

      {/* Calls List */}
      <Card>
        <CardHeader>
          <CardTitle>Call Recordings</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : calls?.length === 0 ? (
            <div className="text-center py-12">
              <Phone className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No calls found</h3>
              <p className="text-muted-foreground mt-1">
                Upload your first call recording to get started.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-medium">Filename</th>
                    <th className="text-left py-3 px-4 font-medium">Duration</th>
                    <th className="text-left py-3 px-4 font-medium">Status</th>
                    <th className="text-left py-3 px-4 font-medium">Quality</th>
                    <th className="text-left py-3 px-4 font-medium">Agent</th>
                    <th className="text-left py-3 px-4 font-medium">Date</th>
                    <th className="text-left py-3 px-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {calls?.map((call: Call) => (
                    <tr key={call.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <Link
                          to={`/calls/${call.id}`}
                          className="text-primary hover:underline font-medium"
                        >
                          {call.filename}
                        </Link>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatDuration(call.duration_seconds)}
                      </td>
                      <td className="py-3 px-4">
                        <Badge className={getStatusColor(call.status)}>
                          {call.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        {call.quality_flag && call.quality_flag !== "normal" ? (
                          <Badge
                            className={
                              call.quality_flag === "short"
                                ? "bg-yellow-100 text-yellow-800"
                                : call.quality_flag === "silent"
                                ? "bg-gray-100 text-gray-800"
                                : call.quality_flag === "poor_audio"
                                ? "bg-orange-100 text-orange-800"
                                : call.quality_flag === "non_english"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-purple-100 text-purple-800"
                            }
                            title={call.quality_notes || undefined}
                          >
                            {call.quality_flag.replace("_", " ")}
                          </Badge>
                        ) : (
                          <span className="text-green-600 text-sm">✓ Normal</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {call.agent?.name || "Unassigned"}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatDate(call.created_at)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex gap-2">
                          <Link to={`/calls/${call.id}`}>
                            <Button variant="outline" size="sm">
                              View
                            </Button>
                          </Link>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => handleDelete(call)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

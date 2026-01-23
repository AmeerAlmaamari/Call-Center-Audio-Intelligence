import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Users, Mail, ArrowRight, Plus, Pencil, Trash2, X } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { agentsApi, dashboardApi, Agent, AgentCreate, AgentUpdate } from "@/lib/api"
import { getScoreColor } from "@/lib/utils"

interface AgentFormData {
  name: string
  email: string
  department: string
}

export default function Agents() {
  const queryClient = useQueryClient()
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null)
  const [formData, setFormData] = useState<AgentFormData>({ name: "", email: "", department: "" })

  const { data: agents, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  })

  const { data: performance } = useQuery({
    queryKey: ["dashboard", "agents"],
    queryFn: dashboardApi.getAgentPerformance,
  })

  const createMutation = useMutation({
    mutationFn: (data: AgentCreate) => agentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard", "agents"] })
      setShowAddModal(false)
      setFormData({ name: "", email: "", department: "" })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentUpdate }) => agentsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard", "agents"] })
      setEditingAgent(null)
      setFormData({ name: "", email: "", department: "" })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => agentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard", "agents"] })
    },
  })

  const getAgentPerformance = (agentId: string) => {
    return performance?.find((p) => p.agent_id === agentId)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim()) return

    if (editingAgent) {
      updateMutation.mutate({ id: editingAgent.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent)
    setFormData({
      name: agent.name,
      email: agent.email || "",
      department: agent.department || "",
    })
  }

  const handleDelete = (agent: Agent) => {
    if (confirm(`Are you sure you want to delete agent "${agent.name}"? Their calls will be unassigned.`)) {
      deleteMutation.mutate(agent.id)
    }
  }

  const closeModal = () => {
    setShowAddModal(false)
    setEditingAgent(null)
    setFormData({ name: "", email: "", department: "" })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Add Agent Button */}
      <div className="flex justify-end">
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Agent
        </Button>
      </div>

      {/* Add/Edit Modal */}
      {(showAddModal || editingAgent) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md mx-4">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{editingAgent ? "Edit Agent" : "Add New Agent"}</CardTitle>
              <Button variant="ghost" size="icon" onClick={closeModal}>
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Agent name"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="agent@example.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="department">Department</Label>
                  <Input
                    id="department"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    placeholder="Sales, Support, etc."
                  />
                </div>
                <div className="flex gap-2 pt-4">
                  <Button type="button" variant="outline" onClick={closeModal} className="flex-1">
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    className="flex-1"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    {createMutation.isPending || updateMutation.isPending
                      ? "Saving..."
                      : editingAgent
                      ? "Update"
                      : "Create"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agents?.map((agent) => {
          const perf = getAgentPerformance(agent.id)
          return (
            <Card key={agent.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <CardTitle className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <Users className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold">{agent.name}</p>
                    <p className="text-sm text-muted-foreground font-normal">
                      {agent.department || "No department"}
                    </p>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Mail className="h-4 w-4" />
                    {agent.email}
                  </div>

                  {perf && (
                    <div className="grid grid-cols-2 gap-4 pt-3 border-t">
                      <div>
                        <p className="text-xs text-muted-foreground">Calls</p>
                        <p className="text-lg font-semibold">{perf.total_calls}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Avg Score</p>
                        <p className={`text-lg font-semibold ${getScoreColor(perf.avg_performance_score)}`}>
                          {perf.avg_performance_score?.toFixed(0) || "N/A"}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Conversion</p>
                        <p className={`text-lg font-semibold ${getScoreColor(perf.avg_conversion_likelihood)}`}>
                          {perf.avg_conversion_likelihood?.toFixed(0) || "N/A"}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Sales</p>
                        <p className="text-lg font-semibold text-green-600">
                          {perf.successful_sales}
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2 pt-3">
                    <Link to={`/agents/${agent.id}`} className="flex-1">
                      <Button variant="outline" className="w-full">
                        View Details
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </Button>
                    </Link>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handleEdit(agent)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => handleDelete(agent)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {agents?.length === 0 && (
        <div className="text-center py-12">
          <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium">No agents found</h3>
          <p className="text-muted-foreground mt-1">
            Agents will appear here once they are added to the system.
          </p>
        </div>
      )}
    </div>
  )
}

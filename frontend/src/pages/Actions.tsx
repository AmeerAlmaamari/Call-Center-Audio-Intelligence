import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import {
  CheckSquare,
  AlertCircle,
  Clock,
  ArrowRight,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { dashboardApi, ActionItem } from "@/lib/api"
import { formatDate } from "@/lib/utils"

export default function Actions() {
  const { data: actionCenter, isLoading } = useQuery({
    queryKey: ["dashboard", "action-center"],
    queryFn: dashboardApi.getActionCenter,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const allActionItems: ActionItem[] = [
    ...(actionCenter?.pending_followups || []),
    ...(actionCenter?.coaching_recommendations || []),
  ]

  const highPriority = allActionItems.filter((item) => item.priority === "high")
  const mediumPriority = allActionItems.filter((item) => item.priority === "medium")
  const lowPriority = allActionItems.filter((item) => item.priority === "low")

  const byCategory = allActionItems.reduce((acc, item) => {
    acc[item.category] = (acc[item.category] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Actions</CardTitle>
            <CheckSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{allActionItems.length}</div>
          </CardContent>
        </Card>

        <Card className="border-red-200">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-red-600">High Priority</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{highPriority.length}</div>
          </CardContent>
        </Card>

        <Card className="border-yellow-200">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-yellow-600">Medium Priority</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{mediumPriority.length}</div>
          </CardContent>
        </Card>

        <Card className="border-green-200">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-green-600">Low Priority</CardTitle>
            <CheckSquare className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{lowPriority.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Category Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>By Category</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {Object.entries(byCategory).map(([category, count]) => (
              <Badge key={category} variant="outline" className="text-sm py-1 px-3">
                {category}: {count}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Action Items List */}
      <Card>
        <CardHeader>
          <CardTitle>All Action Items</CardTitle>
        </CardHeader>
        <CardContent>
          {allActionItems.length === 0 ? (
            <div className="text-center py-12">
              <CheckSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No action items</h3>
              <p className="text-muted-foreground mt-1">
                Action items will appear here after call analysis.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {allActionItems.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div
                    className={`h-3 w-3 rounded-full mt-1.5 flex-shrink-0 ${
                      item.priority === "high"
                        ? "bg-red-500"
                        : item.priority === "medium"
                        ? "bg-yellow-500"
                        : "bg-green-500"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
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
                    <p className="text-sm">{item.description}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDate(item.created_at)}
                    </p>
                  </div>
                  <Link to={`/calls/${item.call_id}`}>
                    <Button variant="ghost" size="sm">
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

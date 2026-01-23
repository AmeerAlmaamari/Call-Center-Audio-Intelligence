import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Calls from './pages/Calls'
import CallDetail from './pages/CallDetail'
import Agents from './pages/Agents'
import AgentDetail from './pages/AgentDetail'
import Insights from './pages/Insights'
import Actions from './pages/Actions'
import VoiceAgent from './pages/VoiceAgent'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="calls" element={<Calls />} />
        <Route path="calls/:id" element={<CallDetail />} />
        <Route path="agents" element={<Agents />} />
        <Route path="agents/:id" element={<AgentDetail />} />
        <Route path="insights" element={<Insights />} />
        <Route path="actions" element={<Actions />} />
        <Route path="voice-agent" element={<VoiceAgent />} />
      </Route>
    </Routes>
  )
}

export default App

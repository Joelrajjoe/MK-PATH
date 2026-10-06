import { Routes, Route, Navigate } from 'react-router-dom'
import Shell from './components/layout/Shell'
import Dashboard from './pages/Dashboard'
import ProjectList from './pages/projects/ProjectList'
import ProjectNew from './pages/projects/ProjectNew'
import ProjectWorkspace from './pages/projects/ProjectWorkspace'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Shell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="projects" element={<ProjectList />} />
        <Route path="projects/new" element={<ProjectNew />} />
        <Route path="projects/:projectId/*" element={<ProjectWorkspace />} />
      </Route>
    </Routes>
  )
}

export default App

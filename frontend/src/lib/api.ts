export interface Project {
  id: string;
  name: string;
  description?: string;
  businessGoal?: string;
  status: string;
  lastRun?: string;
  datasetCount: number;
  modelCount: number;
}

export interface Dataset {
  id: string;
  projectId: string;
  name: string;
  format: string;
  sizeBytes: number;
  status: string;
  createdAt: string;
  rowCount?: number;
  columnCount?: number;
  qualityScore?: number;
}

export interface Profile {
  id: string;
  datasetId: string;
  score: number;
  grade: string;
  issues: any[];
}

export interface SemanticContext {
  id: string;
  datasetId: string;
  confidence: number;
  version: number;
  concepts: any[];
}

export interface AgentRun {
  id: string;
  projectId: string;
  status: string;
}

export interface VerificationResult {
  id: string;
  status: string;
}

export interface Model {
  id: string;
  name: string;
}

export interface Artifact {
  id: string;
  name: string;
}

export interface AuditEvent {
  id: string;
  action: string;
  timestamp: string;
}

// Real client where available, dummy for the rest
const API_BASE = 'http://localhost:8000/api';

export const api = {
  projects: {
    list: async (): Promise<Project[]> => [],
    create: async (data: any): Promise<Project> => ({ id: '1', ...data, status: 'active', datasetCount: 0, modelCount: 0 }),
    get: async (id: string): Promise<Project> => ({ id, name: 'Project', status: 'active', datasetCount: 0, modelCount: 0 }),
  },
  datasets: {
    list: async (_projectId: string): Promise<Dataset[]> => {
      try {
        const res = await fetch(`${API_BASE}/datasets`);
        if (!res.ok) throw new Error('Failed to fetch datasets');
        const data = await res.json();
        return data.items || [];
      } catch (e) {
        console.error(e);
        return [];
      }
    },
    upload: async (_projectId: string, file: File, onProgress?: (p: number) => void): Promise<any> => {
      const formData = new FormData();
      formData.append('file', file);
      
      const xhr = new XMLHttpRequest();
      
      return new Promise((resolve, reject) => {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable && onProgress) {
            const percentComplete = (event.loaded / event.total) * 100;
            onProgress(percentComplete);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            const result = JSON.parse(xhr.responseText);
            // Return full result to handle ZIPs with multiple datasets
            resolve(result);
          } else {
            reject(new Error(`Upload failed: ${xhr.statusText}`));
          }
        };

        xhr.onerror = () => reject(new Error('Network error during upload'));

        xhr.open('POST', `${API_BASE}/datasets/upload`, true);
        xhr.send(formData);
      });
    }
  }
};

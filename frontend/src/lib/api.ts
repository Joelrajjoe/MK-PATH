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
  dataset_id?: string;
  projectId?: string;
  name: string;
  original_filename?: string;
  table_name?: string;
  format: string;
  source_format?: string;
  sizeBytes?: number;
  status: string;
  ingestion_status?: string;
  createdAt?: string;
  created_at?: string;
  rowCount?: number;
  row_count?: number;
  columnCount?: number;
  column_count?: number;
  qualityScore?: number;
  profile?: any;
}

const API_BASE = 'http://localhost:8000/api';

export const api = {
  projects: {
    list: async (): Promise<Project[]> => {
      const res = await fetch(`${API_BASE}/projects`);
      if (!res.ok) throw new Error('Failed to fetch projects');
      const data = await res.json();
      return data.map((p: any) => ({
        id: p.project_id || p.id,
        name: p.name,
        description: p.description,
        businessGoal: p.business_goal || p.businessGoal,
        status: p.status,
        lastRun: p.last_run || p.lastRun,
        datasetCount: p.dataset_count ?? p.datasetCount ?? 0,
        modelCount: p.model_count ?? p.modelCount ?? 0,
      }));
    },
    create: async (data: any): Promise<Project> => {
      const res = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to create project');
      }
      const p = await res.json();
      return {
        id: p.project_id || p.id,
        name: p.name,
        description: p.description,
        businessGoal: p.business_goal || p.businessGoal,
        status: p.status,
        lastRun: p.last_run || p.lastRun,
        datasetCount: p.dataset_count ?? p.datasetCount ?? 0,
        modelCount: p.model_count ?? p.modelCount ?? 0,
      };
    },
    get: async (id: string): Promise<Project> => {
      const res = await fetch(`${API_BASE}/projects/${id}`);
      if (!res.ok) throw new Error('Project not found');
      const p = await res.json();
      return {
        id: p.project_id || p.id,
        name: p.name,
        description: p.description,
        businessGoal: p.business_goal || p.businessGoal,
        status: p.status,
        lastRun: p.last_run || p.lastRun,
        datasetCount: p.dataset_count ?? p.datasetCount ?? 0,
        modelCount: p.model_count ?? p.modelCount ?? 0,
      };
    },
  },
  datasets: {
    list: async (_projectId?: string): Promise<Dataset[]> => {
      try {
        const res = await fetch(`${API_BASE}/datasets`);
        if (!res.ok) throw new Error('Failed to fetch datasets');
        const data = await res.json();
        return (data.items || []).map((d: any) => ({
          ...d,
          id: d.dataset_id || d.id,
          name: d.original_filename || d.table_name || d.name || 'Dataset',
          format: d.source_format || d.format || 'csv',
          status: d.ingestion_status || d.status || 'completed',
          rowCount: d.row_count ?? d.rowCount,
          columnCount: d.column_count ?? d.columnCount,
          qualityScore: d.profile?.quality_score ?? d.qualityScore,
        }));
      } catch (e) {
        console.error(e);
        return [];
      }
    },
    get: async (datasetId: string): Promise<Dataset> => {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}`);
      if (!res.ok) throw new Error('Dataset not found');
      const d = await res.json();
      return {
        ...d,
        id: d.dataset_id || d.id,
        name: d.original_filename || d.table_name || d.name || 'Dataset',
        format: d.source_format || d.format || 'csv',
        status: d.ingestion_status || d.status || 'completed',
        rowCount: d.row_count ?? d.rowCount,
        columnCount: d.column_count ?? d.columnCount,
        qualityScore: d.profile?.quality_score ?? d.qualityScore,
      };
    },
    schema: async (datasetId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/schema`);
      if (!res.ok) throw new Error('Schema not found');
      return await res.json();
    },
    preview: async (datasetId: string, limit = 10): Promise<any> => {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/preview?limit=${limit}`);
      if (!res.ok) throw new Error('Preview unavailable');
      return await res.json();
    },
    quality: async (datasetId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/quality`);
      if (!res.ok) return null;
      return await res.json();
    },
    profile: async (datasetId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/profile`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.detail || 'Profiling failed');
      }
      return await res.json();
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
  },
  semantic: {
    get: async (datasetId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/semantic`);
      if (!res.ok) {
        if (res.status === 404) return null;
        throw new Error('Failed to fetch semantic context');
      }
      return await res.json();
    },
    build: async (datasetId: string, businessGoal?: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/semantic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_goal: businessGoal }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.detail || 'Failed to build semantic context');
      }
      return await res.json();
    },
    getAmbiguities: async (datasetId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/datasets/${datasetId}/semantic/ambiguities`);
      if (!res.ok) return { ambiguities: [], questions: [] };
      return await res.json();
    },
    resolve: async (questionId: string, choice: string, note?: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/clarifications/${questionId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ choice, note, answered_by: 'user' }),
      });
      if (!res.ok) throw new Error('Failed to resolve clarification');
      return await res.json();
    }
  },
  runs: {
    execute: async (projectId: string, datasetId: string, businessGoal?: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/runs/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, dataset_id: datasetId, business_goal: businessGoal }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to execute run');
      }
      return await res.json();
    },
    get: async (runId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/runs/${runId}`);
      if (!res.ok) throw new Error('Run not found');
      return await res.json();
    },
    getAudit: async (runId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/runs/${runId}/audit`);
      if (!res.ok) return { events: [] };
      return await res.json();
    },
    getVerification: async (runId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/runs/${runId}/verification`);
      if (!res.ok) return null;
      return await res.json();
    }
  },
  analysis: {
    plan: async (datasetId: string, businessGoal: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/analysis/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, business_goal: businessGoal }),
      });
      if (!res.ok) throw new Error('Failed to generate analysis plan');
      return await res.json();
    },
    execute: async (datasetId: string, plan: any): Promise<any> => {
      const res = await fetch(`${API_BASE}/analysis/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, plan }),
      });
      if (!res.ok) throw new Error('Failed to execute analysis plan');
      return await res.json();
    }
  },
  models: {
    tournament: async (datasetId: string, target: string, isTemporal = false): Promise<any> => {
      const res = await fetch(`${API_BASE}/models/tournament`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, target, is_temporal: isTemporal }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Model tournament failed');
      }
      return await res.json();
    }
  },
  healing: {
    plan: async (datasetId: string): Promise<any> => {
      const res = await fetch(`${API_BASE}/healing/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId }),
      });
      if (!res.ok) throw new Error('Failed to generate healing plan');
      return await res.json();
    },
    apply: async (datasetId: string, plan: any): Promise<any> => {
      const res = await fetch(`${API_BASE}/healing/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, plan }),
      });
      if (!res.ok) throw new Error('Failed to apply data healing');
      return await res.json();
    }
  },
  verification: {
    getGates: async (projectId = 'project_1', runId = 'run_1', qualityScore = 100.0): Promise<any> => {
      const res = await fetch(`${API_BASE}/verification/gates?project_id=${projectId}&run_id=${runId}&quality_score=${qualityScore}`);
      if (!res.ok) throw new Error('Failed to fetch verification gates');
      return await res.json();
    }
  },
  audit: {
    list: async (projectId?: string, datasetId?: string): Promise<any> => {
      let url = `${API_BASE}/audit?limit=50`;
      if (projectId) url += `&project_id=${projectId}`;
      if (datasetId) url += `&dataset_id=${datasetId}`;
      const res = await fetch(url);
      if (!res.ok) return { events: [] };
      return await res.json();
    }
  }
};

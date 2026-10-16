import React from 'react'
import { Badge } from '@/components/ui/badge'
import { ShieldCheck, ShieldAlert, Clock, AlertTriangle, Key } from 'lucide-react'

interface Props {
  status: string
  keyId?: string
  timestamp?: string
  className?: string
}

export const AttestationStatusBadge: React.FC<Props> = ({ status, keyId, timestamp, className }) => {
  const getBadgeConfig = (st: string) => {
    switch (st) {
      case 'SIGNED':
      case 'VERIFIED':
      case 'VALID':
        return {
          label: 'CRYPTO-VERIFIED',
          variant: 'default' as const,
          bg: 'bg-emerald-950 text-emerald-200 border-emerald-800',
          icon: <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 mr-1" />,
        }
      case 'BLOCKED':
      case 'REJECTED':
      case 'FAIL':
        return {
          label: 'DEPLOYMENT BLOCKED',
          variant: 'destructive' as const,
          bg: 'bg-red-950 text-red-200 border-red-800',
          icon: <ShieldAlert className="h-3.5 w-3.5 text-red-400 mr-1" />,
        }
      case 'INVALID_SIGNATURE':
      case 'HASH_MISMATCH':
      case 'TAMPERED_BLOCKED':
        return {
          label: 'TAMPER DETECTED',
          variant: 'destructive' as const,
          bg: 'bg-red-950 text-red-200 border-red-800 animate-pulse',
          icon: <ShieldAlert className="h-3.5 w-3.5 text-red-400 mr-1" />,
        }
      case 'REVOKED_KEY':
        return {
          label: 'REVOKED KEY',
          variant: 'destructive' as const,
          bg: 'bg-red-950 text-red-300 border-red-800',
          icon: <Key className="h-3.5 w-3.5 text-red-400 mr-1" />,
        }
      case 'UNTRUSTED_KEY':
      case 'UNKNOWN_KEY':
        return {
          label: 'UNTRUSTED KEY',
          variant: 'outline' as const,
          bg: 'bg-yellow-950 text-yellow-300 border-yellow-800',
          icon: <AlertTriangle className="h-3.5 w-3.5 text-yellow-400 mr-1" />,
        }
      case 'STALE':
        return {
          label: 'STALE ATTESTATION',
          variant: 'outline' as const,
          bg: 'bg-slate-900 text-slate-300 border-slate-700',
          icon: <Clock className="h-3.5 w-3.5 text-slate-400 mr-1" />,
        }
      default:
        return {
          label: st || 'UNKNOWN',
          variant: 'secondary' as const,
          bg: 'bg-slate-900 text-slate-300 border-slate-700',
          icon: <ShieldCheck className="h-3.5 w-3.5 text-slate-400 mr-1" />,
        }
    }
  }

  const conf = getBadgeConfig(status)

  return (
    <div className={`inline-flex items-center gap-2 ${className || ''}`}>
      <Badge className={`flex items-center px-2.5 py-1 text-xs font-mono font-medium border ${conf.bg}`}>
        {conf.icon}
        {conf.label}
      </Badge>
      {keyId && (
        <span className="text-[11px] font-mono text-muted-foreground flex items-center">
          <Key className="h-3 w-3 mr-0.5 inline opacity-70" />
          {keyId}
        </span>
      )}
      {timestamp && (
        <span className="text-[10px] font-mono text-muted-foreground opacity-80">
          {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      )}
    </div>
  )
}


export default AttestationStatusBadge

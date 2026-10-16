import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ShieldCheck, ShieldAlert, CheckCircle, RefreshCw, Key, Hash, FileCode, Check } from 'lucide-react'
import { api } from '@/lib/api'
import AttestationStatusBadge from './AttestationStatusBadge'


interface Props {
  envelope: any
  onReverified?: (report: any) => void
}

export const AttestationEvidencePanel: React.FC<Props> = ({ envelope, onReverified }) => {
  const [verifying, setVerifying] = useState(false)
  const [report, setReport] = useState<any>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)

  if (!envelope) {
    return (
      <Card className="border border-border/40 bg-card/40">
        <CardContent className="py-8 text-center text-muted-foreground text-sm font-mono">
          No Attested Result Envelope associated with this execution run yet.
        </CardContent>
      </Card>
    )
  }

  const handleVerify = async () => {
    setVerifying(true)
    try {
      const res = await api.attestations.verify(envelope.envelope_id)
      setReport(res)
      if (onReverified) onReverified(res)
    } catch (err: any) {
      setReport({
        overall_status: 'ERROR',
        signature_valid: false,
        payload_hash_valid: false,
        verification_errors: [err.message || 'Verification request failed'],
      })
    } finally {
      setVerifying(false)
    }
  }

  const copyToClipboard = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(fieldName)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const att = envelope.attestation || {}
  const src = envelope.source_identity || {}
  const tr = envelope.transformation_lineage || {}
  const res = envelope.analytical_result || {}
  const art = envelope.artifact_provenance || {}


  return (
    <Card className="border border-border/50 bg-card/70 backdrop-blur shadow-sm">
      <CardHeader className="pb-3 border-b border-border/40">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-400" />
              <CardTitle className="text-base font-semibold font-mono tracking-tight">
                Attested Result Envelope (ARE-HL)
              </CardTitle>
              <AttestationStatusBadge
                status={report ? report.overall_status : envelope.attestation_status}
                keyId={att.key_id}
              />
            </div>
            <CardDescription className="text-xs text-muted-foreground mt-0.5">
              Envelope ID: <span className="font-mono text-foreground/80">{envelope.envelope_id}</span> • Schema: <span className="font-mono text-foreground/80">{envelope.schema_version}</span>
            </CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleVerify}
            disabled={verifying}
            className="h-8 gap-1.5 text-xs font-mono font-medium"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${verifying ? 'animate-spin' : ''}`} />
            {verifying ? 'Verifying...' : 'Reverify Integrity'}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4 text-xs">
        {/* Verification Report Banner */}
        {report && (
          <div
            className={`p-3 rounded-md border font-mono text-xs ${
              report.overall_status === 'VALID'
                ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200'
                : 'bg-red-950/40 border-red-800 text-red-200'
            }`}
          >
            <div className="flex items-center gap-2 font-semibold">
              {report.overall_status === 'VALID' ? (
                <CheckCircle className="h-4 w-4 text-emerald-400" />
              ) : (
                <ShieldAlert className="h-4 w-4 text-red-400" />
              )}
              Authoritative Verification Status: {report.overall_status}
            </div>
            <div className="mt-1 text-[11px] opacity-90 space-y-0.5">
              <div>Signature Valid: {report.signature_valid ? 'YES' : 'NO'}</div>
              <div>Payload Hash Valid: {report.payload_hash_valid ? 'YES' : 'NO'}</div>
              <div>Content Files Intact: {report.content_hashes_valid ? 'YES' : 'NO'}</div>
              <div>Mandatory Gates Acceptable: {report.mandatory_gates_acceptable ? 'YES' : 'NO'}</div>
              {report.verification_errors?.length > 0 && (
                <div className="mt-2 text-red-300 font-sans">
                  <strong>Errors:</strong>
                  <ul className="list-disc pl-4 mt-0.5">
                    {report.verification_errors.map((e: string, i: number) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Cryptographic Content Hashes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono">
          {/* Source Dataset Hash */}
          <div className="p-2.5 rounded bg-muted/30 border border-border/40">
            <div className="flex items-center justify-between text-muted-foreground mb-1">
              <span className="flex items-center gap-1 font-semibold text-foreground text-[11px]">
                <Hash className="h-3 w-3 text-cyan-400" /> Source Dataset SHA-256
              </span>
              <button
                onClick={() => copyToClipboard(src.source_content_hash, 'src')}
                className="hover:text-foreground text-[10px]"
              >
                {copiedField === 'src' ? <Check className="h-3 w-3 text-emerald-400" /> : 'Copy'}
              </button>
            </div>
            <div className="text-[11px] truncate text-foreground/90 bg-background/50 p-1 rounded border border-border/20">
              {src.source_content_hash || 'N/A'}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1">
              ID: {src.source_dataset_id} • Size: {src.source_size_bytes ?? 0} bytes
            </div>
          </div>

          {/* Derived Dataset Hash */}
          <div className="p-2.5 rounded bg-muted/30 border border-border/40">
            <div className="flex items-center justify-between text-muted-foreground mb-1">
              <span className="flex items-center gap-1 font-semibold text-foreground text-[11px]">
                <Hash className="h-3 w-3 text-amber-400" /> Derived Dataset SHA-256
              </span>
              {tr.derived_content_hash && (
                <button
                  onClick={() => copyToClipboard(tr.derived_content_hash, 'derived')}
                  className="hover:text-foreground text-[10px]"
                >
                  {copiedField === 'derived' ? <Check className="h-3 w-3 text-emerald-400" /> : 'Copy'}
                </button>
              )}
            </div>
            <div className="text-[11px] truncate text-foreground/90 bg-background/50 p-1 rounded border border-border/20">
              {tr.derived_content_hash || 'No transformation applied'}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1">
              Derived ID: {tr.derived_dataset_id || 'None'}
            </div>
          </div>

          {/* Result Payload Hash */}
          <div className="p-2.5 rounded bg-muted/30 border border-border/40">
            <div className="flex items-center justify-between text-muted-foreground mb-1">
              <span className="flex items-center gap-1 font-semibold text-foreground text-[11px]">
                <FileCode className="h-3 w-3 text-purple-400" /> Result Payload Hash
              </span>
              <button
                onClick={() => copyToClipboard(res.result_payload_hash, 'res')}
                className="hover:text-foreground text-[10px]"
              >
                {copiedField === 'res' ? <Check className="h-3 w-3 text-emerald-400" /> : 'Copy'}
              </button>
            </div>
            <div className="text-[11px] truncate text-foreground/90 bg-background/50 p-1 rounded border border-border/20">
              {res.result_payload_hash || 'N/A'}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1">
              Plan ID: {res.analysis_plan_id}
            </div>
          </div>

          {/* Attestation Signature */}
          <div className="p-2.5 rounded bg-muted/30 border border-border/40">
            <div className="flex items-center justify-between text-muted-foreground mb-1">
              <span className="flex items-center gap-1 font-semibold text-foreground text-[11px]">
                <Key className="h-3 w-3 text-emerald-400" /> Digital Signature ({att.signature_algorithm || 'Ed25519'})
              </span>
              <button
                onClick={() => copyToClipboard(att.signature, 'sig')}
                className="hover:text-foreground text-[10px]"
              >
                {copiedField === 'sig' ? <Check className="h-3 w-3 text-emerald-400" /> : 'Copy'}
              </button>
            </div>
            <div className="text-[11px] truncate text-foreground/90 bg-background/50 p-1 rounded border border-border/20">
              {att.signature || 'Unsigned'}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1">
              Signed at: {att.signing_timestamp || 'N/A'}
            </div>
          </div>
        </div>

        {/* Bound Artifact Hashes */}
        {art.artifact_content_hashes && Object.keys(art.artifact_content_hashes).length > 0 && (
          <div className="p-2.5 rounded bg-muted/20 border border-border/30">
            <div className="font-semibold text-[11px] text-foreground mb-1.5 flex items-center gap-1">
              <FileCode className="h-3.5 w-3.5 text-blue-400" /> Bound Deployment Artifact Hashes
            </div>
            <div className="space-y-1 font-mono text-[11px]">
              {Object.entries(art.artifact_content_hashes).map(([fname, h]: [string, any]) => (
                <div key={fname} className="flex items-center justify-between py-0.5 border-b border-border/10">
                  <span className="text-muted-foreground">{fname}:</span>
                  <span className="text-foreground/80 truncate max-w-[280px]">{h}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default AttestationEvidencePanel

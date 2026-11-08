import { useState } from 'react'
import { ArrowLeft, ArrowRight, CheckCircle2 } from 'lucide-react'
import { motion } from 'motion/react'
import { useNavigate } from 'react-router-dom'
import { selectFile } from '../api/files'
import { setRole } from '../api/network'
import { ROUTES } from '../constants/routes'
import { FileDropzone } from '../components/files/FileDropzone'
import { FileList } from '../components/files/FileList'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { useAppStore } from '../stores/appStore'
import { useFileStore } from '../stores/fileStore'
import { formatBytes } from '../utils/format'
import { getErrorMessage } from '../utils/errors'

export function SendFilesPage() {
  const navigate = useNavigate()
  const files = useFileStore((s) => s.files)
  const addFiles = useFileStore((s) => s.addFiles)
  const removeFile = useFileStore((s) => s.removeFile)
  const setUploading = useFileStore((s) => s.setUploading)
  const setUploaded = useFileStore((s) => s.setUploaded)
  const totalSize = files.reduce((sum, f) => sum + f.file.size, 0)
  const setRoleStore = useAppStore((s) => s.setRole)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const handleContinue = async () => {
    if (files.length === 0) {
      setError('Select a file before continuing.')
      return
    }

    setBusy(true)
    setError(null)
    try {
      await setRole('SENDER')
      setRoleStore('SENDER')

      for (const item of files) {
        if (item.uploaded) continue
        setUploading(item.localId, true)
        try {
          const uploaded = await selectFile(item.file)
          setUploaded(item.localId, uploaded)
        } catch (err) {
          const message = getErrorMessage(err, 'Failed to register file with backend')
          setUploading(item.localId, false, message)
          throw err
        }
      }

      navigate(ROUTES.sendConnect)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not prepare send flow'))
    } finally {
      setBusy(false)
    }
  }

  const hasFiles = files.length > 0
  const primaryFile = hasFiles ? files[0] : null

  return (
    <div className="mx-auto max-w-3xl flex flex-col min-h-[calc(100vh-160px)] justify-between space-y-8 pb-8">
      <div className="space-y-6">
        {/* Back and Page Header matching mockup */}
        <div className="flex items-start gap-4">
          <button
            type="button"
            onClick={() => navigate(ROUTES.home)}
            className="mt-1 p-2 rounded-full text-[var(--text)] hover:bg-[var(--bg-light)] transition focus-visible:outline-none"
            aria-label="Go back to Home"
          >
            <ArrowLeft className="w-6 h-6 stroke-[2.25]" />
          </button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text)]">Send Files</h1>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Choose what you want to share.</p>
          </div>
        </div>

        {error ? <ErrorBanner message={error} onDismiss={() => setError(null)} /> : null}

        {/* Dropzone matching mockup */}
        <FileDropzone onFiles={addFiles} disabled={busy} />

        {/* Selected File Card */}
        {hasFiles && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="pt-2"
          >
            <FileList files={files} onRemove={removeFile} totalSize={totalSize} />
          </motion.div>
        )}
      </div>

      {/* Bottom Bar matching reference mockup */}
      <div className="pt-6 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-4">
        <div className="text-sm font-medium text-[var(--text-muted)]">
          {primaryFile ? (
            <span className="text-[var(--text)] flex items-center gap-1.5 font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>
                Sending 1 file · <strong className="font-mono">{formatBytes(primaryFile.file.size)}</strong>
              </span>
            </span>
          ) : (
            <span>No files selected</span>
          )}
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="button"
          onClick={() => void handleContinue()}
          disabled={busy || !hasFiles}
          className={`inline-flex items-center gap-2 rounded-full px-8 py-3.5 text-base font-semibold text-white shadow-sm transition ${
            !hasFiles || busy
              ? 'bg-[#d8a48c] cursor-not-allowed opacity-60'
              : 'bg-[var(--primary)] hover:bg-[var(--primary-hover)] cursor-pointer'
          }`}
        >
          <span>{busy ? 'Preparing…' : 'Continue'}</span>
          <ArrowRight className="w-5 h-5 stroke-[2.25]" />
        </motion.button>
      </div>
    </div>
  )
}

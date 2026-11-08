import { FileIcon, X } from 'lucide-react'
import type { LocalSelectedFile } from '../../stores/fileStore'
import { formatBytes } from '../../utils/format'
import { Spinner } from '../ui/Spinner'

interface FileListProps {
  files: LocalSelectedFile[]
  onRemove: (localId: string) => void
  totalSize: number
}

export function FileList({ files, onRemove, totalSize }: FileListProps) {
  if (files.length === 0) return null

  return (
    <div className="space-y-3">
      <ul className="divide-y divide-[var(--border-muted)] overflow-hidden rounded-2xl border border-[var(--border-muted)] bg-white">
        {files.map((item) => (
          <li key={item.localId} className="flex items-center gap-4 px-4 py-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--surface-muted)]">
              <FileIcon className="h-5 w-5 text-[var(--primary)]" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-[var(--text)]">{item.file.name}</p>
              <p className="mt-0.5 text-sm text-[var(--text-muted)]">
                {item.file.type || 'Unknown type'} · {formatBytes(item.file.size)}
                {item.uploaded ? ' · Ready' : null}
              </p>
              {item.error ? <p className="mt-1 text-sm text-[var(--danger)]">{item.error}</p> : null}
              {item.uploading ? <Spinner className="mt-2" label="Uploading to local backend…" /> : null}
            </div>
            <button
              type="button"
              onClick={() => onRemove(item.localId)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full text-[var(--text-muted)] transition hover:bg-[var(--surface-muted)] hover:text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]"
              aria-label={`Remove ${item.file.name}`}
            >
              <X className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
      <p className="text-sm text-[var(--text-muted)]">Total size: {formatBytes(totalSize)}</p>
    </div>
  )
}

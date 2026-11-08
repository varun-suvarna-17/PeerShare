import { Upload } from 'lucide-react'
import { useCallback, useRef, useState, type DragEvent, type ChangeEvent } from 'react'
import { MAX_FILE_SIZE_BYTES } from '../../constants/protocols'
import { formatBytes } from '../../utils/format'

interface FileDropzoneProps {
  onFiles: (files: File[]) => void
  disabled?: boolean
}

export function FileDropzone({ onFiles, disabled }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const handleFiles = useCallback(
    (list: FileList | File[]) => {
      const files = Array.from(list)
      if (files.length === 0) return

      const file = files[0]
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setLocalError(`“${file.name}” exceeds the 5 MB limit (${formatBytes(file.size)}).`)
        return
      }
      setLocalError(null)
      onFiles([file])
    },
    [onFiles],
  )

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    if (disabled) return
    handleFiles(event.dataTransfer.files)
  }

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) handleFiles(event.target.files)
    event.target.value = ''
  }

  return (
    <div className="space-y-4">
      <div
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        onKeyDown={(e) => {
          if (disabled) return
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
        onDragEnter={(e) => {
          e.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => {
          if (!disabled) inputRef.current?.click()
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-[28px] border-2 border-dashed px-8 py-20 transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] ${
          dragging
            ? 'border-[var(--primary)] bg-[#fbe7d5]'
            : 'border-[#e6b99d] bg-[var(--bg-light)] hover:border-[var(--primary)]'
        } ${disabled ? 'cursor-not-allowed opacity-60' : ''}`}
      >
        {/* Circular upload tray with up arrow from mockup */}
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--bg)] shadow-xs transition-transform duration-200 group-hover:scale-105">
          <Upload className="h-7 w-7 text-[var(--primary)] stroke-[2.25]" aria-hidden />
        </div>

        <p className="text-xl font-bold text-[var(--text)]">Drag and drop files here</p>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          Any file type · max {formatBytes(MAX_FILE_SIZE_BYTES)}
        </p>

        {/* Choose files pill button matching mockup */}
        <div className="mt-6">
          <span className="inline-block rounded-full bg-[var(--primary)] px-8 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--primary-hover)]">
            Choose files
          </span>
        </div>

        <input
          ref={inputRef}
          type="file"
          className="sr-only"
          onChange={onChange}
          disabled={disabled}
        />
      </div>

      {localError ? (
        <p className="text-center text-sm font-medium text-[var(--danger)]">{localError}</p>
      ) : null}
    </div>
  )
}

import { useAppApi, useNavigate } from '@kirocrew/app-sdk'
import { Btn, Input, PageHeader } from '@kirocrew/app-sdk/ui'
import { useState } from 'react'

function looksAbsolute(value: string): boolean {
  const trimmed = value.trim()
  return (
    trimmed.startsWith('/')
    || trimmed.startsWith('\\')
    || /^[A-Za-z]:[\\/]/.test(trimmed)
  )
}

function errorText(err: unknown): string {
  if (err instanceof Error) return err.message
  return String(err)
}

export default function RobloxMvp() {
  const api = useAppApi()
  const navigate = useNavigate()
  const [path, setPath] = useState('')
  const [error, setError] = useState('')

  async function onPickFolder() {
    try {
      const data = await api.post<{ path?: string | null; cancelled?: boolean }>(
        '/api/apps/roblox-mvp/pick-folder',
      )
      if (data.cancelled || !data.path) {
        setError('')
        return
      }
      setPath(data.path)
      setError('')
    } catch (err) {
      setError(errorText(err))
    }
  }

  async function onStart() {
    try {
      const data = await api.post<{ slot: string }>(
        '/api/apps/roblox-mvp/start',
        { project_dir: path.trim() },
      )
      navigate('/chat?slot=' + encodeURIComponent(data.slot))
    } catch (err) {
      setError(errorText(err))
    }
  }

  return (
    <>
      <PageHeader title="Roblox MVP" subtitle="选择项目文件夹，开始写玩法文档。" />
      <div className="px-6 pb-8 overflow-y-auto flex-1 min-h-0">
        <label className="block text-sm text-muted mb-1" htmlFor="project-dir">
          项目文件夹
        </label>
        <Input
          id="project-dir"
          value={path}
          onChange={(event) => setPath(event.target.value)}
          placeholder="输入绝对路径，或点选择文件夹"
        />
        <div className="flex gap-2 mt-3">
          <Btn type="button" onClick={() => void onPickFolder()}>
            选择文件夹
          </Btn>
          <Btn
            type="button"
            primary
            disabled={!looksAbsolute(path)}
            onClick={() => void onStart()}
          >
            开始
          </Btn>
        </div>
        {error ? <p className="text-sm text-danger mt-3">{error}</p> : null}
      </div>
    </>
  )
}

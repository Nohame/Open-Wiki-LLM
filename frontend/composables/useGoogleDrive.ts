import { useApi } from '~/composables/useApi'
import type { GoogleDriveListResponse, IngestResult } from '~/types/api'

export function useGoogleDrive() {
  const { get, post, del } = useApi()

  async function getAuthUrl(): Promise<string> {
    const data = await get<{ url: string }>('/api/connectors/google-drive/auth-url')
    return data.url
  }

  async function disconnect(): Promise<void> {
    await del('/api/connectors/google-drive')
  }

  async function listFiles(folderId = 'root'): Promise<GoogleDriveListResponse> {
    return get<GoogleDriveListResponse>(
      `/api/connectors/google-drive/files?folder_id=${encodeURIComponent(folderId)}`
    )
  }

  async function ingestFile(
    fileId: string,
    fileName: string,
    mimeType: string,
    title?: string,
    tags: string[] = [],
  ): Promise<IngestResult> {
    return post<IngestResult>('/api/connectors/google-drive/ingest', {
      file_id: fileId,
      file_name: fileName,
      mime_type: mimeType,
      title,
      tags,
    })
  }

  return { getAuthUrl, disconnect, listFiles, ingestFile }
}

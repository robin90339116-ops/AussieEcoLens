import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';
import { config } from '../config';
import {
  mockPollUploadStatus,
  mockRequestPresignedUrl,
  mockUploadFileToS3
} from './mock';

const awsClient = axios.create({ baseURL: config.awsApiBaseUrl });

const getToken = async () => {
  const session = await fetchAuthSession();
  return session.tokens?.accessToken?.toString() || session.tokens?.idToken?.toString() || '';
};

const attachAuth = async (request) => {
  const token = await getToken();
  if (token) {
    request.headers.Authorization = `Bearer ${token}`;
  }
  return request;
};

awsClient.interceptors.request.use(attachAuth);

const ensureBaseUrl = (baseUrl, provider) => {
  if (!baseUrl) {
    throw new Error(`${provider} API base URL is missing. Set it in frontend/.env.`);
  }
};

export const normalizeResults = (payload) => {
  const rawItems =
    payload?.items ||
    payload?.results ||
    payload?.files ||
    payload?.matches ||
    (Array.isArray(payload) ? payload : []);

  return rawItems.map((item, index) => {
    if (typeof item === 'string') {
      return {
        id: item,
        type: /\.(mp4|mov|webm)$/i.test(item) ? 'video' : 'image',
        url: item,
        thumbnail_url: item,
        original_url: item,
        tags: {}
      };
    }

    const thumbnailUrl =
      item.thumbnail_url || item.thumbnailUrl || item.thumbnail || item.previewUrl || item.url;
    const originalUrl =
      item.original_url || item.originalUrl || item.fullUrl || item.mediaUrl || item.url || thumbnailUrl;
    const type = item.type || (/\.(mp4|mov|webm)$/i.test(originalUrl || '') ? 'video' : 'image');

    return {
      ...item,
      id: item.id || item.file_id || item.fileId || originalUrl || `result-${index}`,
      type,
      thumbnail_url: thumbnailUrl,
      original_url: originalUrl,
      url: item.url || originalUrl,
      tags: item.tags || item.detectedTags || {}
    };
  });
};

export async function requestPresignedUrl(file) {
  if (config.useMocks) {
    return mockRequestPresignedUrl(file);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.get(config.paths.presigned, {
    params: {
      fileName: file.name,
      contentType: file.type,
      size: file.size
    }
  });
  return data;
}

export async function uploadFileToS3(uploadUrl, file, onProgress) {
  if (config.useMocks || uploadUrl?.startsWith('mock://')) {
    return mockUploadFileToS3(uploadUrl, file, onProgress);
  }
  await axios.put(uploadUrl, file, {
    headers: {
      'Content-Type': file.type || 'application/octet-stream'
    },
    onUploadProgress: (event) => {
      if (event.total) {
        onProgress?.(Math.round((event.loaded * 100) / event.total));
      }
    }
  });
}

export async function pollUploadStatus({ key, file }) {
  if (config.useMocks) {
    return mockPollUploadStatus(file);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.get(config.paths.uploadStatus, {
    params: {
      key,
      fileName: file.name
    }
  });
  return data?.item || data?.file || data;
}

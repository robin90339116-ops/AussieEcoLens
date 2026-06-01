const sampleFiles = [
  {
    id: 'mock-1',
    type: 'image',
    thumbnail_url:
      'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=520&q=80',
    original_url:
      'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80',
    tags: { 'common wombat': 2, 'australian magpie': 1 },
    upload_time: '2026-05-31T05:20:00Z'
  },
  {
    id: 'mock-2',
    type: 'image',
    thumbnail_url:
      'https://images.unsplash.com/photo-1485550409059-9afb054cada4?auto=format&fit=crop&w=520&q=80',
    original_url:
      'https://images.unsplash.com/photo-1485550409059-9afb054cada4?auto=format&fit=crop&w=1600&q=80',
    tags: { dingo: 1 },
    upload_time: '2026-05-31T06:15:00Z'
  },
  {
    id: 'mock-3',
    type: 'video',
    url: 'https://example.com/mock/wildlife-video.mp4',
    original_url: 'https://example.com/mock/wildlife-video.mp4',
    tags: { 'southern cassowary': 1, 'orange-footed scrubfowl': 2 },
    upload_time: '2026-05-31T07:30:00Z'
  }
];

let files = [...sampleFiles];

const wait = (ms = 360) => new Promise((resolve) => setTimeout(resolve, ms));

const matchesTags = (file, requestedTags) =>
  Object.entries(requestedTags).every(([species, count]) => {
    const current = file.tags?.[species] ?? 0;
    return current >= Number(count || 1);
  });

export async function mockRequestPresignedUrl(file) {
  await wait();
  return {
    uploadUrl: 'mock://s3-upload',
    key: `uploads/${Date.now()}-${file.name}`,
    fileName: file.name
  };
}

export async function mockUploadFileToS3(_uploadUrl, _file, onProgress) {
  for (const value of [18, 36, 58, 78, 100]) {
    await wait(120);
    onProgress?.(value);
  }
}

export async function mockPollUploadStatus(file) {
  await wait();
  const created = {
    id: `mock-${Date.now()}`,
    type: file.type?.startsWith('video') ? 'video' : 'image',
    thumbnail_url: URL.createObjectURL(file),
    original_url: URL.createObjectURL(file),
    tags: { 'common wombat': 1 },
    upload_time: new Date().toISOString()
  };
  files = [created, ...files];
  return created;
}

export async function mockQueryByTags(tags) {
  await wait();
  return files.filter((file) => matchesTags(file, tags));
}

export async function mockQueryBySpecies(species) {
  await wait();
  return files.filter((file) => Number(file.tags?.[species] || 0) > 0);
}

export async function mockResolveOriginalUrl(thumbnailUrl) {
  await wait();
  const match = files.find((file) => file.thumbnail_url === thumbnailUrl || file.url === thumbnailUrl);
  return match?.original_url || thumbnailUrl;
}

export async function mockQueryByUploadedFile() {
  await wait();
  return files.filter((file) => file.tags?.['common wombat'] || file.tags?.dingo);
}

export async function mockBulkUpdateTags({ urls, tags, operation }) {
  await wait();
  files = files.map((file) => {
    const fileUrl = file.thumbnail_url || file.original_url || file.url;
    if (!urls.includes(fileUrl)) {
      return file;
    }
    const nextTags = { ...(file.tags || {}) };
    Object.entries(tags).forEach(([species, count]) => {
      if (operation === 1) {
        nextTags[species] = Number(count || 1);
      } else {
        delete nextTags[species];
      }
    });
    return { ...file, tags: nextTags };
  });
  return { updated: urls.length };
}

export async function mockDeleteFiles(urls) {
  await wait();
  const before = files.length;
  files = files.filter((file) => !urls.includes(file.thumbnail_url || file.original_url || file.url));
  return { deleted: before - files.length };
}

export async function mockListFiles() {
  await wait();
  return files;
}

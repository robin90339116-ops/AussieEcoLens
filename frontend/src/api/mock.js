const wait = (ms = 360) => new Promise((resolve) => setTimeout(resolve, ms));

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
  return {
    id: `mock-${Date.now()}`,
    type: file.type?.startsWith('video') ? 'video' : 'image',
    thumbnail_url: URL.createObjectURL(file),
    original_url: URL.createObjectURL(file),
    tags: { 'common wombat': 1 },
    upload_time: new Date().toISOString()
  };
}

import { Button, Empty, Image, Modal, Space, Tag, Typography, message } from 'antd';
import { ExternalLink, Eye, PlayCircle } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { resolveOriginalUrl } from '../api/client';

const readStoredResults = () => {
  try {
    return JSON.parse(sessionStorage.getItem('aussie-ecolens-results') || 'null');
  } catch {
    return null;
  }
};

export default function Results() {
  const location = useLocation();
  const stored = readStoredResults();
  const title = location.state?.title || stored?.title || 'Results';
  const items = useMemo(() => location.state?.items || stored?.items || [], [location.state, stored]);
  const [modalUrl, setModalUrl] = useState('');
  const [loadingUrl, setLoadingUrl] = useState('');

  useEffect(() => {
    if (location.state?.items) {
      sessionStorage.setItem('aussie-ecolens-results', JSON.stringify(location.state));
    }
  }, [location.state]);

  const handleOpenImage = async (item) => {
    const thumbnailUrl = item.thumbnail_url || item.url || item.original_url;
    setLoadingUrl(thumbnailUrl);
    try {
      const originalUrl = await resolveOriginalUrl(thumbnailUrl);
      setModalUrl(originalUrl);
    } catch (error) {
      message.error(error.message || 'Could not resolve original URL');
    } finally {
      setLoadingUrl('');
    }
  };

  return (
    <section className="page-grid single-column">
      <div className="page-heading">
        <Typography.Title level={2}>{title}</Typography.Title>
        <Typography.Text type="secondary">{items.length} matching files</Typography.Text>
      </div>

      {items.length === 0 ? (
        <div className="tool-panel">
          <Empty description="No results" />
        </div>
      ) : (
        <div className="gallery-grid">
          {items.map((item) => {
            const isVideo = item.type === 'video';
            const previewUrl = item.thumbnail_url || item.url || item.original_url;
            const originalUrl = item.original_url || item.url;

            return (
              <article className="media-card" key={item.id || previewUrl}>
                <div className="media-frame">
                  {isVideo ? (
                    <div className="video-tile">
                      <PlayCircle size={42} />
                      <Typography.Text>Video file</Typography.Text>
                    </div>
                  ) : (
                    <Image src={previewUrl} alt="Wildlife thumbnail" preview={false} />
                  )}
                </div>
                <div className="media-card-body">
                  <Space wrap>
                    {Object.entries(item.tags || {}).map(([species, count]) => (
                      <Tag color="green" key={species}>
                        {species} x {count}
                      </Tag>
                    ))}
                  </Space>
                  <Space className="card-actions">
                    {isVideo ? (
                      <Button
                        href={originalUrl}
                        target="_blank"
                        rel="noreferrer"
                        icon={<ExternalLink size={16} />}
                      >
                        Open
                      </Button>
                    ) : (
                      <Button
                        loading={loadingUrl === previewUrl}
                        icon={<Eye size={16} />}
                        onClick={() => handleOpenImage(item)}
                      >
                        Full image
                      </Button>
                    )}
                    <Typography.Text copyable ellipsis className="copy-url">
                      {previewUrl}
                    </Typography.Text>
                  </Space>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <Modal
        title="Full-size image"
        open={Boolean(modalUrl)}
        footer={null}
        onCancel={() => setModalUrl('')}
        width={920}
      >
        {modalUrl && <img className="modal-image" src={modalUrl} alt="Full-size wildlife media" />}
      </Modal>
    </section>
  );
}


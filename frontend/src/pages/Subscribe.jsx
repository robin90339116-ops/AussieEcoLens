import { Button, Checkbox, Empty, Space, Tag, Typography, message } from 'antd';
import { Bell, Save, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getSubscriptions, saveSubscriptions, unsubscribeSpecies } from '../api/client';
import { speciesOptions } from '../data/species';
import { useAuth } from '../context/AuthContext';

export default function Subscribe() {
  const { user } = useAuth();
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadSubscriptions = async () => {
    setLoading(true);
    try {
      setSelected(await getSubscriptions());
    } catch (error) {
      message.error(error.message || 'Could not load subscriptions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSubscriptions();
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      const next = await saveSubscriptions(selected);
      if (Array.isArray(next)) {
        setSelected(next);
      }
      message.success('Subscriptions updated');
    } catch (error) {
      message.error(error.message || 'Subscription update failed');
    } finally {
      setLoading(false);
    }
  };

  const handleUnsubscribe = async (species) => {
    setLoading(true);
    try {
      const next = await unsubscribeSpecies(species);
      setSelected(Array.isArray(next) ? next : selected.filter((item) => item !== species));
      message.success('Subscription removed');
    } catch (error) {
      message.error(error.message || 'Unsubscribe failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="page-grid subscribe-grid">
      <div className="page-heading">
        <Typography.Title level={2}>Tag notifications</Typography.Title>
        <Typography.Text type="secondary">{user?.email}</Typography.Text>
      </div>

      <div className="tool-panel">
        <Checkbox.Group value={selected} onChange={setSelected} className="species-check-grid">
          {speciesOptions.map((species) => (
            <Checkbox key={species.value} value={species.value}>
              {species.label}
            </Checkbox>
          ))}
        </Checkbox.Group>
        <Space className="panel-actions">
          <Button type="primary" loading={loading} icon={<Save size={17} />} onClick={handleSave}>
            Save subscriptions
          </Button>
          <Button loading={loading} icon={<Bell size={17} />} onClick={loadSubscriptions}>
            Refresh
          </Button>
        </Space>
      </div>

      <div className="tool-panel">
        <Typography.Title level={4}>Subscribed species</Typography.Title>
        {selected.length ? (
          <Space wrap>
            {selected.map((species) => (
              <Tag
                key={species}
                color="green"
                closable
                closeIcon={<X size={12} />}
                onClose={(event) => {
                  event.preventDefault();
                  handleUnsubscribe(species);
                }}
              >
                {species}
              </Tag>
            ))}
          </Space>
        ) : (
          <Empty description="No subscriptions" />
        )}
      </div>
    </section>
  );
}

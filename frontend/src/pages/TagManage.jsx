import { Button, Form, Input, InputNumber, Radio, Select, Space, Typography, message } from 'antd';
import { Plus, Save, X } from 'lucide-react';
import { useState } from 'react';
import { bulkUpdateTags, tagsArrayToObject } from '../api/client';
import { speciesOptions } from '../data/species';

const parseLines = (value = '') =>
  value
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

export default function TagManage() {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async ({ urlsText, rows, operation }) => {
    const urls = parseLines(urlsText);
    const tags = tagsArrayToObject(rows || []);
    if (!urls.length || !Object.keys(tags).length) {
      message.error('URLs and tags are required');
      return;
    }

    setLoading(true);
    try {
      const response = await bulkUpdateTags({
        urls,
        tags,
        operation
      });
      message.success(`Tag update submitted${response?.updated ? `: ${response.updated}` : ''}`);
    } catch (error) {
      message.error(error.message || 'Tag update failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="page-grid single-column">
      <div className="page-heading">
        <Typography.Title level={2}>Bulk tag management</Typography.Title>
        <Typography.Text type="secondary">Add or remove species tags from selected media URLs.</Typography.Text>
      </div>

      <div className="tool-panel">
        <Form
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ operation: 1, rows: [{ count: 1 }] }}
        >
          <Form.Item
            name="urlsText"
            label="Media URLs"
            rules={[{ required: true, message: 'Enter at least one URL' }]}
          >
            <Input.TextArea rows={5} placeholder="One URL per line" />
          </Form.Item>

          <Form.Item name="operation" label="Operation">
            <Radio.Group optionType="button" buttonStyle="solid">
              <Radio.Button value={1}>Add</Radio.Button>
              <Radio.Button value={0}>Remove</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.List name="rows">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <div className="query-row" key={field.key}>
                    <Form.Item
                      {...field}
                      name={[field.name, 'species']}
                      rules={[{ required: true, message: 'Select species' }]}
                    >
                      <Select
                        showSearch
                        options={speciesOptions}
                        optionFilterProp="label"
                        placeholder="Species"
                      />
                    </Form.Item>
                    <Form.Item {...field} name={[field.name, 'count']}>
                      <InputNumber min={1} max={99} />
                    </Form.Item>
                    <Button
                      title="Remove row"
                      icon={<X size={16} />}
                      onClick={() => remove(field.name)}
                    />
                  </div>
                ))}
                <Button icon={<Plus size={16} />} onClick={() => add({ count: 1 })}>
                  Add tag
                </Button>
              </>
            )}
          </Form.List>

          <Space className="panel-actions">
            <Button type="primary" htmlType="submit" loading={loading} icon={<Save size={17} />}>
              Submit update
            </Button>
          </Space>
        </Form>
      </div>
    </section>
  );
}


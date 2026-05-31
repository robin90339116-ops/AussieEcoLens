import { Button, Form, Input, Typography, message } from 'antd';
import { ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function NewPassword() {
  const navigate = useNavigate();
  const { completeNewPassword } = useAuth();

  const handleSubmit = async ({ password }) => {
    try {
      await completeNewPassword(password);
      message.success('Password updated');
      navigate('/upload', { replace: true });
    } catch (error) {
      message.error(error.message || 'Password update failed');
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark">AE</span>
          <Typography.Title level={1}>New password</Typography.Title>
        </div>
        <Form layout="vertical" onFinish={handleSubmit} requiredMark={false}>
          <Form.Item
            name="password"
            label="Password"
            rules={[
              { required: true, message: 'Enter a password' },
              {
                pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/,
                message: 'Use 8+ chars with upper, lower, number, and symbol'
              }
            ]}
          >
            <Input.Password size="large" autoComplete="new-password" />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            icon={<ShieldCheck size={18} />}
          >
            Save password
          </Button>
        </Form>
      </section>
    </main>
  );
}


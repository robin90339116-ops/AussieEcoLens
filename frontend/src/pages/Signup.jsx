import { Button, Form, Input, Space, Typography, message } from 'antd';
import { ShieldCheck } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Signup() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const handleSubmit = async (values) => {
    try {
      await register(values);
      navigate('/verify', { state: { email: values.email } });
    } catch (error) {
      message.error(error.message || 'Sign-up failed');
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel auth-panel-wide">
        <div className="auth-brand">
          <span className="brand-mark">AE</span>
          <Typography.Title level={1}>Create account</Typography.Title>
        </div>
        <Form layout="vertical" onFinish={handleSubmit} requiredMark={false}>
          <div className="two-column-form">
            <Form.Item
              name="givenName"
              label="First name"
              rules={[{ required: true, message: 'Enter your first name' }]}
            >
              <Input size="large" autoComplete="given-name" />
            </Form.Item>
            <Form.Item
              name="familyName"
              label="Last name"
              rules={[{ required: true, message: 'Enter your last name' }]}
            >
              <Input size="large" autoComplete="family-name" />
            </Form.Item>
          </div>
          <Form.Item
            name="email"
            label="Email"
            rules={[{ required: true, type: 'email', message: 'Enter a valid email' }]}
          >
            <Input size="large" autoComplete="email" />
          </Form.Item>
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
            Continue
          </Button>
        </Form>
        <Space className="auth-footer">
          <Typography.Text type="secondary">Already registered?</Typography.Text>
          <Link to="/login">Sign in</Link>
        </Space>
      </section>
    </main>
  );
}


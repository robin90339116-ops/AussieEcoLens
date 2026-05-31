import { Alert, Button, Form, Input, Space, Typography, message } from 'antd';
import { LogIn, UserPlus } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, mockAuth } = useAuth();
  const [form] = Form.useForm();
  const redirectTo = location.state?.from?.pathname || '/upload';

  const handleSubmit = async (values) => {
    try {
      const result = await login(values);
      const step = result.nextStep?.signInStep;
      if (step === 'CONFIRM_SIGN_UP') {
        navigate('/verify', { state: { email: values.email } });
        return;
      }
      if (step === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        navigate('/new-password', { state: { email: values.email } });
        return;
      }
      navigate(redirectTo, { replace: true });
    } catch (error) {
      message.error(error.message || 'Sign-in failed');
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark">AE</span>
          <Typography.Title level={1}>Aussie EcoLens</Typography.Title>
        </div>
        {mockAuth && (
          <Alert
            type="warning"
            showIcon
            message="Local mock authentication is active"
            className="auth-alert"
          />
        )}
        <Form form={form} layout="vertical" onFinish={handleSubmit} requiredMark={false}>
          <Form.Item
            name="email"
            label="Email"
            rules={[{ required: true, type: 'email', message: 'Enter a valid email' }]}
          >
            <Input autoComplete="email" size="large" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Password"
            rules={[{ required: true, message: 'Enter your password' }]}
          >
            <Input.Password autoComplete="current-password" size="large" />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            icon={<LogIn size={18} />}
          >
            Sign in
          </Button>
        </Form>
        <Space className="auth-footer">
          <Typography.Text type="secondary">New account?</Typography.Text>
          <Link to="/signup">
            <Button type="link" icon={<UserPlus size={16} />}>
              Sign up
            </Button>
          </Link>
        </Space>
      </section>
    </main>
  );
}

